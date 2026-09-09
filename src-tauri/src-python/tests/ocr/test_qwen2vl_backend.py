"""Unit tests for QwenVLOCRBackend partial-download fix.

Covers:
- _download_model_if_needed: partial-download detection via cache + shard check
- _weight_shards_cached: verifies every shard in the safetensors index is cached
- _init_model: OSError from from_pretrained triggers force re-download and retry
- _init_model: KMP_DUPLICATE_LIB_OK is set before torch is imported
"""

import json
import os
from unittest.mock import MagicMock, PropertyMock, call, patch

from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend

_SHARD_A = "model-00001-of-00002.safetensors"
_SHARD_B = "model-00002-of-00002.safetensors"


def _write_index(tmp_path, shards=(_SHARD_A, _SHARD_B)):
    """Write a minimal model.safetensors.index.json to tmp_path and return its path.

    Args:
        tmp_path: pytest tmp_path fixture directory to write into.
        shards: shard filenames to reference from the index's weight_map.
    """
    index_path = tmp_path / "model.safetensors.index.json"
    weight_map = {f"layer.{i}.weight": shard for i, shard in enumerate(shards)}
    index_path.write_text(json.dumps({"weight_map": weight_map}), encoding="utf-8")
    return str(index_path)


def _hf_mock(config_result, index_result, shard_results=None):
    """Return a minimal huggingface_hub module mock.

    Args:
        config_result: value returned for the config.json cache check.
        index_result: value returned for the weight-index cache check.
        shard_results: dict mapping shard filename to its cache-check result,
            used for calls made while verifying individual weight shards.
    """
    mock = MagicMock()

    def side_effect(_model_id, filename):
        if filename == "config.json":
            return config_result
        if filename == "model.safetensors.index.json":
            return index_result
        return (shard_results or {}).get(filename)

    mock.try_to_load_from_cache.side_effect = side_effect
    return mock


class TestWeightShardsCached:
    def _backend(self):
        return QwenVLOCRBackend()

    def test_all_shards_cached_returns_true(self, tmp_path):
        backend = self._backend()
        index_path = _write_index(tmp_path)
        mock_hf = _hf_mock(
            "/cache/config.json",
            index_path,
            shard_results={
                _SHARD_A: "/cache/" + _SHARD_A,
                _SHARD_B: "/cache/" + _SHARD_B,
            },
        )

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            assert backend._weight_shards_cached(index_path) is True

    def test_missing_shard_returns_false(self, tmp_path):
        backend = self._backend()
        index_path = _write_index(tmp_path)
        mock_hf = _hf_mock(
            "/cache/config.json",
            index_path,
            shard_results={_SHARD_A: "/cache/" + _SHARD_A, _SHARD_B: None},
        )

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            assert backend._weight_shards_cached(index_path) is False

    def test_unreadable_index_returns_false(self, tmp_path):
        backend = self._backend()
        missing_path = str(tmp_path / "does-not-exist.json")
        mock_hf = _hf_mock("/cache/config.json", missing_path)

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            assert backend._weight_shards_cached(missing_path) is False


class TestDownloadModelIfNeeded:
    def _backend(self):
        return QwenVLOCRBackend()

    def test_both_files_and_shards_cached_skips_download(self, tmp_path):
        """config.json, weight index, and every shard cached → no download."""
        backend = self._backend()
        index_path = _write_index(tmp_path)
        mock_hf = _hf_mock(
            "/cache/config.json",
            index_path,
            shard_results={
                _SHARD_A: "/cache/" + _SHARD_A,
                _SHARD_B: "/cache/" + _SHARD_B,
            },
        )

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            backend._download_model_if_needed()

        mock_hf.snapshot_download.assert_not_called()

    def test_missing_shard_triggers_redownload(self, tmp_path):
        """Index present but a referenced shard is missing → download triggered.

        Regression test: STATUS_ACCESS_VIOLATION crashes were traced to
        from_pretrained loading a corrupt/incomplete shard because the old
        cache check only looked at config.json + the index file, never the
        shards the index references.
        """
        backend = self._backend()
        index_path = _write_index(tmp_path)
        mock_hf = _hf_mock(
            "/cache/config.json",
            index_path,
            shard_results={_SHARD_A: "/cache/" + _SHARD_A, _SHARD_B: None},
        )

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            backend._download_model_if_needed()

        mock_hf.snapshot_download.assert_called_once_with(QwenVLOCRBackend.MODEL_ID)

    def test_only_config_cached_triggers_download(self):
        """config.json cached but weight index missing → download triggered."""
        backend = self._backend()
        mock_hf = _hf_mock("/cache/config.json", None)

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            backend._download_model_if_needed()

        mock_hf.snapshot_download.assert_called_once_with(QwenVLOCRBackend.MODEL_ID)

    def test_neither_file_cached_triggers_download(self):
        """Neither file cached → download triggered."""
        backend = self._backend()
        mock_hf = _hf_mock(None, None)

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            backend._download_model_if_needed()

        mock_hf.snapshot_download.assert_called_once()

    def test_force_redownload_skips_cache_check(self):
        """force_redownload=True always downloads, even when both files are cached."""
        backend = self._backend()
        mock_hf = MagicMock()
        mock_hf.try_to_load_from_cache.return_value = "/cache/path"

        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            backend._download_model_if_needed(force_redownload=True)

        mock_hf.snapshot_download.assert_called_once()
        mock_hf.try_to_load_from_cache.assert_not_called()


class TestInitModel:
    def _make_sys_mocks(self, proc_cls, model_cls):
        """Return sys.modules patches for torch and transformers.

        Args:
            proc_cls: mock to use as Qwen2VLProcessor.
            model_cls: mock to use as Qwen2VLForConditionalGeneration.
        """
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        mock_transformers = MagicMock()
        mock_transformers.Qwen2VLProcessor = proc_cls
        mock_transformers.Qwen2VLForConditionalGeneration = model_cls

        return {
            "torch": mock_torch,
            "transformers": mock_transformers,
        }

    def test_oserror_triggers_retry_with_force_redownload(self):
        """OSError from from_pretrained triggers force re-download."""
        backend = QwenVLOCRBackend()

        mock_proc_cls = MagicMock()
        mock_proc_cls.from_pretrained.side_effect = [
            OSError("Partial download: file not found"),
            MagicMock(),
        ]
        mock_model_inst = MagicMock()
        mock_model_cls = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model_inst

        sys_mocks = self._make_sys_mocks(mock_proc_cls, mock_model_cls)

        with (
            patch.dict("sys.modules", sys_mocks),
            patch.object(
                type(backend),
                "_is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(backend, "_download_model_if_needed") as mock_dl,
        ):
            result = backend._init_model()

        assert result is True
        assert mock_dl.call_count == 2
        assert mock_dl.call_args_list[0] == call()
        assert mock_dl.call_args_list[1] == call(force_redownload=True)
        mock_model_inst.eval.assert_called_once()

    def test_persistent_oserror_sets_model_load_failed(self):
        """If the retry also raises OSError, model_load_failed is set to True."""
        backend = QwenVLOCRBackend()

        mock_proc_cls = MagicMock()
        mock_proc_cls.from_pretrained.side_effect = OSError("persistent error")
        mock_model_cls = MagicMock()

        sys_mocks = self._make_sys_mocks(mock_proc_cls, mock_model_cls)

        with (
            patch.dict("sys.modules", sys_mocks),
            patch.object(
                type(backend),
                "_is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(backend, "_download_model_if_needed"),
        ):
            result = backend._init_model()

        assert result is False
        assert backend._model_load_failed is True


class TestKmpDuplicateLibWorkaround:
    """Regression test for the torch_cpu.dll access-violation crash.

    The bundled extras env ships both torch's and paddle's copies of
    libiomp5md.dll; transformers' optional-backend probing can load paddle's
    after torch's is already resident, and Intel's OpenMP runtime doesn't
    tolerate two copies in one process. `KMP_DUPLICATE_LIB_OK=TRUE` must be
    set before the first `import torch`.
    """

    def test_init_model_sets_kmp_duplicate_lib_ok(self, monkeypatch):
        monkeypatch.delenv("KMP_DUPLICATE_LIB_OK", raising=False)
        backend = QwenVLOCRBackend()

        mock_proc_cls = MagicMock()
        mock_model_cls = MagicMock()
        mock_model_cls.from_pretrained.return_value = MagicMock()
        sys_mocks = {
            "torch": MagicMock(
                cuda=MagicMock(is_available=MagicMock(return_value=False)),
                backends=MagicMock(
                    mps=MagicMock(is_available=MagicMock(return_value=False))
                ),
            ),
            "transformers": MagicMock(
                Qwen2VLProcessor=mock_proc_cls,
                Qwen2VLForConditionalGeneration=mock_model_cls,
            ),
        }

        with (
            patch.dict("sys.modules", sys_mocks),
            patch.object(
                type(backend),
                "_is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(backend, "_download_model_if_needed"),
        ):
            backend._init_model()

        assert os.environ.get("KMP_DUPLICATE_LIB_OK") == "TRUE"

    def test_does_not_override_an_existing_value(self, monkeypatch):
        """A user-set value (e.g. "FALSE" to keep the safety check) is respected."""
        monkeypatch.setenv("KMP_DUPLICATE_LIB_OK", "FALSE")
        backend = QwenVLOCRBackend()

        mock_proc_cls = MagicMock()
        mock_proc_cls.from_pretrained.side_effect = OSError("boom")
        sys_mocks = {
            "torch": MagicMock(
                cuda=MagicMock(is_available=MagicMock(return_value=False)),
                backends=MagicMock(
                    mps=MagicMock(is_available=MagicMock(return_value=False))
                ),
            ),
            "transformers": MagicMock(
                Qwen2VLProcessor=mock_proc_cls,
                Qwen2VLForConditionalGeneration=MagicMock(),
            ),
        }

        with (
            patch.dict("sys.modules", sys_mocks),
            patch.object(
                type(backend),
                "_is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(backend, "_download_model_if_needed"),
        ):
            backend._init_model()

        assert os.environ.get("KMP_DUPLICATE_LIB_OK") == "FALSE"
