"""Debug script: count pairs per chest frame."""

import re
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

from adb_auto_player.ocr.rapidocr_backend import RapidOCRBackend  # noqa: E402

rapid = RapidOCRBackend.pp_ocr_v5_rec()

SCREENSHOTS_DIR = Path(
    r"C:\Users\sacri\AppData\Roaming\com.AdbAutoPlayer.AdbAutoPlayer"
    r"\0\data\screenshots"
)

_Y_CHEST_CONTRIB_MIN = 850
_Y_CHEST_CONTRIB_MAX = 1800
_X_CHEST_NAME_MAX = 480
_Y_CHEST_PAIR_RADIUS = 150
_MAX_CHEST_VALUE = 99999
_MAX_CHEST_RANK_NUMBER = 200
_X_CHEST_RANK_BADGE_MAX = 200
_RE_CHEST_VALUE = re.compile(r"^\D{0,3}(\d+)$")
_RE_CHEST_LABEL = re.compile(
    r"chest\s*contribution|contribution\s*ranking|guild\s*chest"
    r"|distribution|activeness\s*required"
    r"|officer|founder|paladin|knight|squire|member",
    re.IGNORECASE,
)

MIN_NAME_LENGTH = 2

all_names: list[str] = []
for path in sorted(SCREENSHOTS_DIR.glob("chest_*.png")):
    img = cv2.imread(str(path))
    if img is None:
        continue
    results = rapid.detect_text_blocks(img)
    area = [
        r
        for r in results
        if _Y_CHEST_CONTRIB_MIN <= r.box.center.y <= _Y_CHEST_CONTRIB_MAX
    ]
    value_blocks = []
    for b in area:
        t = b.text.strip()
        m = _RE_CHEST_VALUE.match(t)
        if (
            b.box.center.x > _X_CHEST_NAME_MAX
            and m is not None
            and 0 <= int(m.group(1)) <= _MAX_CHEST_VALUE
            and not _RE_CHEST_LABEL.search(t)
        ):
            value_blocks.append(b)
    name_blocks = []
    for b in area:
        t = b.text.strip()
        if b.box.center.x >= _X_CHEST_NAME_MAX:
            continue
        if not t or len(t) < MIN_NAME_LENGTH:
            continue
        if _RE_CHEST_LABEL.search(t):
            continue
        if (
            t.isdigit()
            and int(t) <= _MAX_CHEST_RANK_NUMBER
            and b.box.center.x < _X_CHEST_RANK_BADGE_MAX
        ):
            continue
        name_blocks.append(b)
    name_blocks.sort(key=lambda b: b.box.center.y)
    pairs: list[tuple[str, int]] = []
    used: set[int] = set()
    for nb in name_blocks:
        best_val, best_dist, best_idx = None, float("inf"), -1
        for idx, vb in enumerate(value_blocks):
            if idx in used:
                continue
            dist = abs(vb.box.center.y - nb.box.center.y)
            if dist <= _Y_CHEST_PAIR_RADIUS and dist < best_dist:
                mv = _RE_CHEST_VALUE.match(vb.text.strip())
                if mv is not None:
                    best_dist, best_val, best_idx = dist, int(mv.group(1)), idx
        if best_val is not None:
            used.add(best_idx)
            pairs.append((nb.text.strip(), best_val))
    names_this = [p[0] for p in pairs]
    all_names.extend(names_this)
    print(f"{path.name}: {len(pairs)} pairs | {names_this}")

print(f"\nTotal reads: {len(all_names)}, Unique: {len(set(all_names))}")
