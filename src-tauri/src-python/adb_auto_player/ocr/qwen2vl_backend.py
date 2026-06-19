"""Qwen2-VL-2B OCR backend for high-precision name extraction on GPU."""

import importlib.util
import json
import logging
import re
import threading
from typing import Any

import numpy as np
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.ocr import OCRResult

from ._backend import OCRBackend

logger = logging.getLogger(__name__)


class QwenVLOCRBackend(OCRBackend):
    """Qwen2-VL-2B-Instruct backend for high-precision text extraction.

    Uses GPU (CUDA) when available. Falls back to RapidOCR if torch/transformers
    are not installed. All imports are lazy so the backend works even when packages
    are installed at runtime during the same session.

    ``extract_text`` runs the VL model on an image crop and returns raw text.
    ``detect_text_blocks`` always delegates to RapidOCR (no bounding boxes).
    """

    MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
    MAX_IMAGE_WIDTH_CAP = 540

    def __init__(self) -> None:
        self._model: Any = None
        self._processor: Any = None
        self._fallback: OCRBackend | None = None
        self._device: str | None = None
        self._model_load_failed = False

    @property
    def _is_available(self) -> bool:
        return (
            importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("transformers") is not None
        )

    def _get_fallback(self) -> OCRBackend:
        if self._fallback is None:
            from adb_auto_player.ocr import RapidOCRBackend  # noqa: PLC0415

            self._fallback = RapidOCRBackend()
        return self._fallback

    def _get_device(self) -> str:
        if self._device is None:
            import torch  # type: ignore  # noqa: PLC0415

            if torch.cuda.is_available():
                self._device = "cuda"
            elif torch.backends.mps.is_available():
                self._device = "mps"
                logger.info("Qwen2-VL-2B: using Apple Silicon MPS backend.")
            else:
                self._device = "cpu"
                logger.warning(
                    "Qwen2-VL-2B: no GPU available — running on CPU, "
                    "expect slow inference."
                )
        return self._device

    def _download_model_if_needed(self) -> None:
        """Download model weights from HuggingFace with heartbeat progress logging.

        Checks the local HuggingFace cache first; if the weights are already
        present the method returns immediately. Otherwise ``snapshot_download``
        is called in the foreground while a background thread emits a log line
        every 30 s so the UI does not appear frozen.
        """
        try:
            from huggingface_hub import (  # type: ignore  # noqa: PLC0415
                try_to_load_from_cache,
            )

            cached = try_to_load_from_cache(self.MODEL_ID, "config.json")
            if cached is not None:
                return
        except Exception:
            pass

        logger.info(
            "Qwen2-VL-2B: model weights not found in local cache — "
            "downloading (~2.2 GB). This may take several minutes "
            "depending on your connection speed. Please do not close the app."
        )

        _stop = threading.Event()

        def _heartbeat() -> None:
            elapsed = 0
            while not _stop.wait(30):
                elapsed += 30
                logger.info(
                    f"[download] Qwen2-VL-2B still downloading… ({elapsed}s elapsed)"
                )

        hb = threading.Thread(target=_heartbeat, daemon=True)
        hb.start()
        try:
            from huggingface_hub import (  # type: ignore  # noqa: PLC0415
                snapshot_download,
            )

            snapshot_download(self.MODEL_ID)
            logger.info("Qwen2-VL-2B: model weights downloaded successfully.")
        except Exception as e:
            logger.warning(
                f"Qwen2-VL-2B: snapshot_download failed ({e}). "
                "Will retry via from_pretrained."
            )
        finally:
            _stop.set()

    def _init_model(self) -> bool:
        if self._model is not None:
            return True
        if self._model_load_failed or not self._is_available:
            return False
        try:
            import logging as _logging  # noqa: PLC0415

            # Silence HTTP and auth noise using each library's own verbosity API.
            for _noisy in ("httpx", "filelock"):
                _logging.getLogger(_noisy).setLevel(_logging.ERROR)
            try:
                import huggingface_hub.utils.logging as _hf_log  # type: ignore  # noqa: PLC0415

                _hf_log.set_verbosity_error()
            except Exception:
                pass
            try:
                import transformers.utils.logging as _tr_log  # type: ignore  # noqa: PLC0415

                _tr_log.set_verbosity(50)  # CRITICAL — suppress docstring [ERROR] noise
            except Exception:
                pass

            # Use direct imports to bypass AutoClass requirements checking,
            # which can fail when packages are installed in a non-standard path.
            import torch  # type: ignore  # noqa: PLC0415
            from transformers import (  # type: ignore  # noqa: PLC0415
                Qwen2VLForConditionalGeneration,
                Qwen2VLProcessor,
            )

            device = self._get_device()
            logger.info(
                f"Initializing Qwen2-VL-2B on {device} (model: {self.MODEL_ID})..."
            )
            self._download_model_if_needed()
            self._processor = Qwen2VLProcessor.from_pretrained(
                self.MODEL_ID, trust_remote_code=True, local_files_only=True
            )
            dtype = torch.float16 if device == "cuda" else torch.float32
            # low_cpu_mem_usage=True loads each layer directly to the target
            # device (GPU) without staging the full model in CPU RAM first,
            # avoiding Windows "paging file too small" errors (OS error 1455).
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.MODEL_ID,
                torch_dtype=dtype,
                device_map="auto" if device == "cuda" else device,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                local_files_only=True,
            )
            self._model.eval()
            logger.info("Qwen2-VL-2B initialized successfully.")
            return True
        except Exception as e:
            import traceback  # noqa: PLC0415

            logger.error(
                f"Failed to load Qwen2-VL-2B: {type(e).__name__}: {e}.\n"
                f"Root cause:\n{traceback.format_exc()}"
            )
            self._model_load_failed = True
            return False

    @staticmethod
    def has_sufficient_vram(min_gb: float = 6.0) -> bool:
        """Return True if a supported GPU backend is available.

        Accepts:
        - NVIDIA CUDA with ≥ min_gb VRAM
        - Apple Silicon MPS (unified memory, no fixed VRAM limit)
        """
        if importlib.util.find_spec("torch") is None:
            logger.warning("Qwen2-VL: torch not found in sys.path.")
            return False
        try:
            import torch  # type: ignore  # noqa: PLC0415

            logger.info(
                f"torch {torch.__version__} | "
                f"CUDA built: {torch.version.cuda} | "
                f"cuda.is_available: {torch.cuda.is_available()}"
            )

            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                vram_gb = props.total_memory / (1024**3)
                logger.info(f"GPU: {props.name} | VRAM: {vram_gb:.1f} GB")
                if vram_gb >= min_gb:
                    return True
                logger.warning(
                    f"VRAM {vram_gb:.1f} GB is below the {min_gb} GB minimum."
                )
                return False

            if torch.backends.mps.is_available():
                logger.info("Apple Silicon MPS available.")
                return True

            logger.warning(
                "torch.cuda.is_available() = False. "
                "Check that your NVIDIA drivers support CUDA "
                f"{torch.version.cuda}."
            )
            return False
        except Exception as e:
            logger.warning(f"has_sufficient_vram error: {e}")
            return False

    def _run_qwen_inference(
        self, messages: list, max_new_tokens: int = 256
    ) -> str | None:
        """Run Qwen2-VL inference on the given messages and return raw text output."""
        try:
            import torch  # type: ignore  # noqa: PLC0415

            device = self._get_device()
            text_prompt = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            has_qwen_utils = importlib.util.find_spec("qwen_vl_utils") is not None
            if has_qwen_utils:
                from qwen_vl_utils import (  # type: ignore  # noqa: PLC0415
                    process_vision_info,
                )

                image_inputs, video_inputs = process_vision_info(messages)
                inputs = self._processor(
                    text=[text_prompt],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                ).to(device)
            else:
                pil_images = [
                    c["image"]
                    for m in messages
                    for c in m.get("content", [])
                    if isinstance(c, dict) and c.get("type") == "image"
                ]
                inputs = self._processor(
                    text=[text_prompt],
                    images=pil_images or None,
                    padding=True,
                    return_tensors="pt",
                ).to(device)
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs, max_new_tokens=max_new_tokens
                )
            trimmed = [
                out[len(inp) :] for inp, out in zip(inputs.input_ids, generated_ids)
            ]
            return self._processor.batch_decode(
                trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()
        except Exception as e:
            logger.warning(f"Qwen2-VL inference failed: {e}")
            return None

    def _prepare_image(self, screenshot, y_min: int = 0, y_max: int | None = None):
        """Crop and resize screenshot to MAX_IMAGE_WIDTH_CAP; return PIL Image."""
        import cv2  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415

        crop = screenshot[y_min:y_max] if y_max else screenshot[y_min:]
        h, w = crop.shape[:2]
        if w > self.MAX_IMAGE_WIDTH_CAP:
            new_w = self.MAX_IMAGE_WIDTH_CAP
            new_h = int(h * new_w / w)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

    def extract_activeness_from_screenshot(
        self, screenshot
    ) -> list[tuple[str | None, str | None]] | None:
        """Extract (name, activeness) pairs from a guild members activeness screen.

        Supplements RapidOCR for multilingual names (Korean, etc.).
        Returns None on failure.
        """
        if not self._is_available or not self._init_model():
            return None
        try:
            pil_image = self._prepare_image(screenshot, y_min=300, y_max=1850)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {
                            "type": "text",
                            "text": (
                                "This is a guild member list showing player names "
                                "and activeness scores.\n"
                                "Return ONLY a JSON array, nothing else:\n"
                                '[{"name":"불꽃남자. 정대만","activeness":"450"},'
                                '{"name":"Sacrifar","activeness":"820"},...]\n'
                                "Rules:\n"
                                "- name: exact text as visible — including Korean, "
                                "Chinese, Cyrillic, special characters\n"
                                "- activeness: the number shown on the right of "
                                "each row ('0' if none visible)\n"
                                "- Skip UI labels: Guild Member, Warband, More, "
                                "Paladin, Sentinel, Founder, Officer, (Base)\n"
                                "- Include EVERY member row visible"
                            ),
                        },
                    ],
                }
            ]
            raw = self._run_qwen_inference(messages, max_new_tokens=384)
            if not raw:
                return None
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                return None
            data = json.loads(match.group())
            if not isinstance(data, list):
                return None
            pairs: list[tuple[str | None, str | None]] = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                name = str(entry["name"]).strip() if entry.get("name") else None
                act = (
                    str(entry["activeness"]).strip()
                    if entry.get("activeness") is not None
                    else "0"
                )
                pairs.append((name, act))
            return pairs if pairs else None
        except Exception as e:
            logger.warning(f"Qwen2-VL activeness extraction failed: {e}")
            return None

    def extract_chest_from_screenshot(
        self, screenshot
    ) -> list[tuple[str | None, str | None]] | None:
        """Extract (name, chest_count) pairs from a guild chest contribution screen.

        Supplements RapidOCR for multilingual names (Korean, etc.).
        Returns None on failure.
        """
        if not self._is_available or not self._init_model():
            return None
        try:
            pil_image = self._prepare_image(screenshot, y_min=850, y_max=1850)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {
                            "type": "text",
                            "text": (
                                "This is a guild chest contribution ranking screen. "
                                "Each row shows a member name and their chest count.\n"
                                "Return ONLY a JSON array, nothing else:\n"
                                '[{"name":"불꽃남자. 정대만","chest":"67"},'
                                '{"name":"Sacrifar","chest":"22"},...]\n'
                                "Rules:\n"
                                "- name: exact player name — including Korean, "
                                "Chinese, Cyrillic, special characters\n"
                                "- chest: the contribution number on the right\n"
                                "- Skip labels: Chest Contribution Ranking, "
                                "Paladin, Sentinel, Officer, Founder, rank numbers\n"
                                "- Include EVERY member row visible"
                            ),
                        },
                    ],
                }
            ]
            raw = self._run_qwen_inference(messages, max_new_tokens=384)
            if not raw:
                return None
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                return None
            data = json.loads(match.group())
            if not isinstance(data, list):
                return None
            pairs: list[tuple[str | None, str | None]] = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                name = str(entry["name"]).strip() if entry.get("name") else None
                chest = (
                    str(entry["chest"]).strip()
                    if entry.get("chest") is not None
                    else None
                )
                pairs.append((name, chest))
            return pairs if pairs else None
        except Exception as e:
            logger.warning(f"Qwen2-VL chest extraction failed: {e}")
            return None

    def extract_rankings_from_screenshot(
        self, screenshot
    ) -> list[tuple[str | None, str | None, str | None]] | None:
        """Extract structured (rank, name, score) rows from a full rankings screenshot.

        Sends the whole screen to Qwen2-VL with a structured JSON prompt.
        Returns None on any failure so the caller can fall back to RapidOCR.
        """
        if not self._is_available or not self._init_model():
            return None
        try:
            pil_image = self._prepare_image(screenshot)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {
                            "type": "text",
                            "text": (
                                "Extract all player ranking rows from the "
                                "scrollable list in this image. "
                                "Ignore any decorative podium at the top.\n"
                                "Return ONLY a JSON array, nothing else:\n"
                                '[{"rank":"24","name":"ОпасныйПоцык",'
                                '"score":"7634M"},...]\n'
                                "Rules:\n"
                                "- rank: number on the left "
                                "(null if a trophy/medal icon)\n"
                                "- name: transcribe EXACTLY what you see, "
                                "character by character — including Cyrillic, "
                                "Korean, Chinese, Japanese. "
                                "Do NOT substitute with a different name.\n"
                                "- score: value on the right "
                                "(e.g. '7634M'), null if absent\n"
                                "- Include ALL rows. Do NOT skip any entry.\n"
                                "- Each rank number must appear at most once."
                            ),
                        },
                    ],
                }
            ]
            raw = self._run_qwen_inference(messages, max_new_tokens=256)
            if not raw:
                return None
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                logger.debug(f"Qwen2-VL: no JSON array in response: {raw[:300]!r}")
                return None
            data = json.loads(match.group())
            if not isinstance(data, list):
                return None
            rows: list[tuple[str | None, str | None, str | None]] = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                rank = (
                    str(entry["rank"]).strip()
                    if entry.get("rank") is not None
                    else None
                )
                name = str(entry["name"]).strip() if entry.get("name") else None
                score = (
                    str(entry["score"]).strip()
                    if entry.get("score") is not None
                    else None
                )
                rows.append((rank, name, score))
            return rows if rows else None
        except Exception as e:
            logger.debug(f"Qwen2-VL rankings extraction failed: {e}")
            return None

    def extract_player_name(self, image: np.ndarray) -> str:
        """Extract the player name from a single member-card row crop.

        Used to read names that RapidOCR cannot detect (e.g. Korean Hangul).
        Returns an empty string on failure.
        """
        if not self._is_available or not self._init_model():
            return ""
        try:
            pil_image = self._prepare_image(image)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {
                            "type": "text",
                            "text": (
                                "This is a cropped row from a guild member list. "
                                "Extract ONLY the player name — not the power "
                                "rating, not the time stamp, not any other text.\n"
                                "Return just the name, nothing else.\n"
                                "Examples of player names: 불꽃남자.정대만, "
                                "Sacrifar, ОпасныйПоцык, 이른봄날"
                            ),
                        },
                    ],
                }
            ]
            raw = self._run_qwen_inference(messages, max_new_tokens=32)
            return raw.strip() if raw else ""
        except Exception as e:
            logger.warning(f"Qwen2-VL extract_player_name failed: {e}")
            return ""

    def extract_text(self, image: np.ndarray) -> str:
        """Extract text from the given image crop using Qwen2-VL.

        If the model or dependencies are not available, falls back to the
        RapidOCR backend.
        """
        if not self._is_available or not self._init_model():
            return self._get_fallback().extract_text(image)
        try:
            pil_image = self._prepare_image(image)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {
                            "type": "text",
                            "text": (
                                "Extract all text from this image. "
                                "Output only the exact text as it appears, "
                                "no explanations."
                            ),
                        },
                    ],
                }
            ]
            raw = self._run_qwen_inference(messages, max_new_tokens=128)
            return raw if raw else ""
        except Exception as e:
            logger.error(f"Qwen2-VL extract_text failed: {e}")
            return ""

    def detect_text_blocks(
        self,
        image: np.ndarray,
        min_confidence: ConfidenceValue = ConfidenceValue(0.0),
    ) -> list[OCRResult]:
        """Delegate to RapidOCR: Qwen2-VL does not produce bounding boxes."""
        return self._get_fallback().detect_text_blocks(image, min_confidence)
