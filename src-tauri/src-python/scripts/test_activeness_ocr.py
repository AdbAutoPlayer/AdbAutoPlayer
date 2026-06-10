# ruff: noqa: RUF001
"""Replay OCR on saved debug screenshots (activeness, DR, SA) without a device scan."""

import io
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

# Set stdout encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import cv2  # noqa: E402

# Add the extras directory (Qwen2-VL deps installed by the app at runtime)
_extras = Path(sys.executable).parent.parent / "extras" / "guild_scan"
if _extras.exists() and str(_extras) not in sys.path:
    sys.path.append(str(_extras))

sys.path.insert(0, str(Path(__file__).parent.parent))

from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend  # noqa: E402
from adb_auto_player.ocr.rapidocr_backend import RapidOCRBackend  # noqa: E402

SCREENSHOTS_DIR = Path(
    r"C:\Users\sacri\AppData\Roaming\com.AdbAutoPlayer.AdbAutoPlayer"
    r"\0\data\screenshots"
)

# ── Activeness constants ──────────────────────────────────────────────────────
_Y_ACTIVENESS_MIN = 320
_Y_ACTIVENESS_MAX = 1800
_X_ACTIVENESS_MIN = 500
_Y_ACTIVENESS_PAIR_RADIUS = 120
_MIN_ACTIVENESS_VALUE = 10
_MAX_ACTIVENESS_VALUE = 9999
_MIN_NAME_LENGTH = 2
_MAX_NUMERIC_NAME_DIGITS = 4

_RE_POWER_RATING = re.compile(r"^\d+[.,]?\d*\s*[KMBkmb]\b", re.IGNORECASE)
_RE_BASE_SUFFIX = re.compile(
    r"[(" + chr(0xFF08) + r"]\s*[Bb]ase\s*[)" + chr(0xFF09) + r"]"
)
_RE_GUILD_HEADER = re.compile(
    r"Guild Member|Warband|Activeness|Officer|Founder|Friends",
    re.IGNORECASE,
)

# ── Rankings constants ────────────────────────────────────────────────────────
_Y_MAX_RANKINGS = 1800
_X_RANK_BOUNDARY = 200
_X_SCORE_BOUNDARY = 700
_Y_ROW_ALIGNMENT_TOLERANCE = 80
_MIN_ROW_BLOCKS = 2
_MAX_RANK_NUMBER = 500
_MIN_NAME_ALNUM_RATIO = 0.5
_Y_GUILD_OFFSET = 45

# ── Guild member list (fresh from API 2026-06-10) ─────────────────────────────
GUILD_MEMBERS = [
    "Cos",
    "Eleanor Cassedy",
    "Peter",
    "Trailblazer",
    "BroGamer",
    "BlackFriday",
    "Forest Child",
    "ArinaKravz",
    "Sacrifar",
    "Aurion",
    "Xenos",
    "Manu",
    "Qee_Jordanius",
    "ОпасныйПоцык",
    "Victz",
    "devin",
    "Kirsty",
    "Fuq",
    "Brew",
    "Lazarius",
    "Mikki",
    "Jorvikingr",
    "Wildburgh",
    "Escanor",
    "旅人",
    "Evan",
    "Riley",
    "Jack",
    "Harima",
    "Lea_June | CR",
    "PeachyKeen | CR",
    "B0ldar",
    "67",
    "Lutarian",
    "Nyxilis",
    "BORKBORK",
    "Rain",
    "Lunalyn",
    "Strobrijam",
    "Arcanist",
    "Amethia|CR",
    "Melkor",
    "이른봄날",
    "Dazzah",
    "Boki",
    "Acharya",
    "Kotone",
    "Talal",
    "Ofidio",
    "Vanbluu",
    "de0s",
    "Killy",
    "Aroshard",
    "Mao | CR",
    "Complex Protein",
    "WhiteRabbit",
    "Night-",
    "Potato_Troy",
    "Saga- Bey",
    "Zucc",
    "Ghrokan",
    "Narixx",
    "Bøą",
    "Hazz",
    "IndominousLink",
    "典明",
    "CTL|Caresse",
    "Beebs | CR",
    "Carot",
    "Cale",
    "Morgan",
    "Sebv",
    "recluse",
    "Sch4rfi",
    "ArchJeepR",
    "Chippy's Sidekick",
    "Persephone",
    "Burglar",
    "Shin",
    "Pierre",
    "Jamie",
    "Arnz",
    "Frog | CR",
    "CTL | Maciejsonik",
    "Nemesis",
    "Grigori",
    "Waku",
    "enkeaa",
    "Vertex",
    "불꽃남자. 정대만",
]

SUFFIX_PAT = re.compile(r"\b[A-Za-z]?\d{3,4}\b")
THRESHOLD = 0.65
FUZZY_MATCH_THRESHOLD = 0.75
UNRANKED_MIN_COUNT = 2


# ── Helpers ───────────────────────────────────────────────────────────────────

# Cyrillic to Visual Latin character transliteration map (intentional ambiguous chars)
_CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "6",
    "в": "b",
    "г": "r",
    "д": "g",
    "е": "e",
    "ё": "e",
    "ж": "k",
    "з": "3",
    "и": "u",
    "й": "u",
    "к": "k",
    "л": "n",
    "м": "m",
    "н": "h",
    "о": "o",
    "п": "n",
    "р": "p",
    "с": "c",
    "т": "m",
    "у": "y",
    "ф": "o",
    "х": "x",
    "ц": "u",
    "ч": "u",
    "ш": "w",
    "щ": "w",
    "ъ": "b",
    "ы": "bi",
    "ь": "b",
    "э": "3",
    "ю": "io",
    "я": "r",
    "А": "A",
    "Б": "6",
    "В": "B",
    "Г": "R",
    "Д": "G",
    "Е": "E",
    "Ё": "E",
    "Ж": "K",
    "З": "3",
    "И": "U",
    "Й": "U",
    "К": "K",
    "Л": "N",
    "М": "M",
    "Н": "H",
    "О": "O",
    "П": "N",
    "Р": "P",
    "С": "C",
    "Т": "M",
    "У": "Y",
    "Х": "X",
    "Ц": "U",
    "Ч": "U",
    "Ш": "W",
    "Щ": "W",
    "Ы": "Bi",
    "Я": "R",
}


def to_visual_latin(text: str) -> str:
    """Map Cyrillic characters to visual-matching Latin characters."""
    return "".join(_CYRILLIC_TO_LATIN.get(c, c) for c in text)


_DIACRITIC_MAP = {
    "ø": "o",
    "Ø": "O",
    "ą": "a",
    "Ą": "A",
    "ę": "e",
    "Ę": "E",
    "ś": "s",
    "Ś": "S",
    "ź": "z",
    "Ź": "Z",
    "ż": "z",
    "Ż": "Z",
    "ł": "l",
    "Ł": "L",
    "æ": "ae",
    "Æ": "AE",
    "þ": "th",
    "Þ": "TH",
    "ß": "ss",
}


def strip_diacritics(text: str) -> str:
    """Normalize and strip diacritics from a string."""
    import unicodedata  # noqa: PLC0415

    result = []
    for c in text:
        mapped = _DIACRITIC_MAP.get(c)
        if mapped is not None:
            result.append(mapped)
            continue
        nfd = unicodedata.normalize("NFD", c)
        ascii_base = nfd.encode("ascii", "ignore").decode("ascii")
        result.append(ascii_base if ascii_base else c)
    return "".join(result)


def clean_name(name: str) -> str:
    """Clean name suffixes."""
    return SUFFIX_PAT.sub("", name).strip()


_KOREAN_MEMBERS = [
    m for m in GUILD_MEMBERS if re.search(r"[가-힣\u1100-\u11FF\u3130-\u318F]", m)
]
_CJK_PAT = re.compile(r"[\u4E00-\u9FFF\u3040-\u30FF\uF900-\uFAFF]")
_CLEANED_MEMBERS = [
    (m, re.sub(r"\b[A-Za-z]?\d{3,4}\b", "", m).strip()) for m in GUILD_MEMBERS
]


def best_match(ocr_name: str) -> tuple[str, float]:
    """Find the best matching guild member name using string similarity."""
    # CJK misread heuristic: RapidOCR garbles Korean into CJK characters.
    # Only fire when the text does not match a known CJK guild member name.
    if len(_KOREAN_MEMBERS) == 1:
        is_korean = bool(re.search(r"[가-힣\u1100-\u11FF\u3130-\u318F]", ocr_name))
        is_cjk_misread = bool(_CJK_PAT.search(ocr_name)) and not any(
            ocr_name == mc for _, mc in _CLEANED_MEMBERS if _CJK_PAT.search(mc)
        )
        if is_korean or is_cjk_misread:
            return _KOREAN_MEMBERS[0], 1.0

    cleaned_ocr = to_visual_latin(strip_diacritics(clean_name(ocr_name)))
    best_m, best_r = "", 0.0
    for m in GUILD_MEMBERS:
        member_vis = to_visual_latin(strip_diacritics(clean_name(m)))
        r = SequenceMatcher(None, cleaned_ocr.lower(), member_vis.lower()).ratio()
        if r > best_r:
            best_r, best_m = r, m
    return best_m, best_r


def report(label: str, all_names: list[str]) -> None:
    """Match a flat list of OCR names against guild members and print a report."""
    # Deduplicate keeping last occurrence (mirrors "best activeness" logic)
    seen: dict[str, int] = {}
    for name in all_names:
        seen[name] = seen.get(name, 0) + 1

    matched: dict[str, tuple[str, int]] = {}
    unmatched: list[tuple[str, int, str, float]] = []

    for ocr_name, count in seen.items():
        m, r = best_match(ocr_name)
        if r >= THRESHOLD:
            if m not in matched or count > matched[m][1]:
                matched[m] = (ocr_name, count)
        else:
            unmatched.append((ocr_name, count, m, r))

    missing = [m for m in GUILD_MEMBERS if m not in matched]

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  Matched {len(matched)}/{len(GUILD_MEMBERS)} guild members")
    print("=" * 60)

    if missing:
        print(f"\n  Missing ({len(missing)}):")
        for m in missing:
            print(f"    {m!r}")

    if unmatched:
        print(f"\n  Unmatched OCR reads (ratio < {THRESHOLD}):")
        for ocr, cnt, m, r in sorted(unmatched, key=lambda x: -x[1]):
            print(f"    {ocr!r:32s} x{cnt}  best={m!r} ({r:.2f})")

    print("\n  All matched:")
    for gm, (ocr, cnt) in sorted(matched.items(), key=lambda x: x[0].lower()):
        flag = " *" if ocr != gm else ""
        print(f"    {gm!r:30s} <- {ocr!r:30s} x{cnt}{flag}")


# ── Activeness parsing ────────────────────────────────────────────────────────


def is_valid_activeness_name(text: str) -> bool:
    """Validate if the text is a valid name block in activeness list."""
    t = text.strip()
    if len(t) < _MIN_NAME_LENGTH:
        return False
    if _RE_POWER_RATING.match(t) or _RE_BASE_SUFFIX.search(t):
        return False
    if _RE_GUILD_HEADER.search(t):
        return False
    digits_only = t.replace(",", "").replace(".", "")
    if digits_only.isdigit() and int(digits_only) >= _MIN_ACTIVENESS_VALUE:
        if len(digits_only) > _MAX_NUMERIC_NAME_DIGITS:
            return False
    return True


def parse_activeness_rows(screenshot, ocr_backend):
    """Parse activeness rows from screenshot."""
    ocr_results = ocr_backend.detect_text_blocks(screenshot)
    area_blocks = [
        r
        for r in ocr_results
        if _Y_ACTIVENESS_MIN <= r.box.center.y <= _Y_ACTIVENESS_MAX
    ]
    activeness_blocks, name_blocks = [], []
    for b in area_blocks:
        t = b.text.strip()
        if (
            t.isdigit()
            and b.box.center.x >= _X_ACTIVENESS_MIN
            and _MIN_ACTIVENESS_VALUE <= int(t) <= _MAX_ACTIVENESS_VALUE
        ):
            activeness_blocks.append(b)
        elif b.box.center.x < _X_ACTIVENESS_MIN and is_valid_activeness_name(t):
            name_blocks.append(b)

    name_blocks.sort(key=lambda b: b.box.center.y)
    pairs, used = [], set()
    for nb in name_blocks:
        name_y, best_act, best_dist, best_idx = nb.box.center.y, None, float("inf"), -1
        for idx, ab in enumerate(activeness_blocks):
            if idx in used:
                continue
            dist = abs(ab.box.center.y - name_y)
            if dist <= _Y_ACTIVENESS_PAIR_RADIUS and dist < best_dist:
                best_dist, best_act, best_idx = dist, ab.text.strip(), idx
        if best_act is not None:
            used.add(best_idx)
            pairs.append((nb.text.strip(), best_act))
        else:
            pairs.append((nb.text.strip(), "0"))
    return pairs


def test_activeness(backend) -> None:  # noqa: PLR0912
    """Test OCR text extraction on activeness screenshots."""
    screenshots = sorted(SCREENSHOTS_DIR.glob("activeness_*.png"))
    if not screenshots:
        print("No activeness screenshots found.")
        return

    all_seen: dict[str, int] = {}
    for path in screenshots:
        img = cv2.imread(str(path))
        if img is None:
            continue
        for raw_name, activeness in parse_activeness_rows(img, backend):
            name = re.sub(r"\s*[A-Za-z]?\d{3,4}\s*$", "", raw_name).strip()
            if not name or len(name) < _MIN_NAME_LENGTH:
                continue
            try:
                act_int = int(activeness)
            except ValueError:
                act_int = 0
            if name not in all_seen or act_int > all_seen[name]:
                all_seen[name] = act_int

    # For activeness report we show activeness values, not counts
    matched: dict[str, tuple[str, int]] = {}
    unmatched: list[tuple[str, int, str, float]] = []
    for ocr_name, act in all_seen.items():
        m, r = best_match(ocr_name)
        if r >= THRESHOLD:
            if m not in matched or act > matched[m][1]:
                matched[m] = (ocr_name, act)
        else:
            unmatched.append((ocr_name, act, m, r))

    missing = [m for m in GUILD_MEMBERS if m not in matched]

    print("\n" + "=" * 60)
    print(f"  ACTIVENESS  ({len(screenshots)} frames)")
    print(f"  Matched {len(matched)}/{len(GUILD_MEMBERS)} guild members")
    print("=" * 60)

    if missing:
        print(f"\n  Missing ({len(missing)}):")
        for m in missing:
            print(f"    {m!r}")

    if unmatched:
        print(f"\n  Unmatched OCR reads (ratio < {THRESHOLD}):")
        for ocr, act, m, r in sorted(unmatched, key=lambda x: -x[1]):
            print(f"    {ocr!r:32s} act={act:4d}  best={m!r} ({r:.2f})")

    print("\n  All matched (sorted by activeness desc):")
    for gm, (ocr, act) in sorted(matched.items(), key=lambda x: -x[1][1]):
        flag = " *" if ocr != gm else ""
        print(f"    {gm!r:30s} <- {ocr!r:30s} act={act}{flag}")


# ── Chest contribution parsing ────────────────────────────────────────────────

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


def parse_chest_contribution_rows(screenshot, ocr_backend) -> list[tuple[str, int]]:  # noqa: PLR0912
    """Return (raw_name, chest_count) pairs from one Contribution Ranking frame."""
    ocr_results = ocr_backend.detect_text_blocks(screenshot)
    area = [
        r
        for r in ocr_results
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
        if not t or len(t) < _MIN_NAME_LENGTH:
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
        name_y = nb.box.center.y
        best_val, best_dist, best_idx = None, float("inf"), -1
        for idx, vb in enumerate(value_blocks):
            if idx in used:
                continue
            dist = abs(vb.box.center.y - name_y)
            if dist <= _Y_CHEST_PAIR_RADIUS and dist < best_dist:
                mv = _RE_CHEST_VALUE.match(vb.text.strip())
                if mv is not None:
                    best_dist, best_val, best_idx = dist, int(mv.group(1)), idx
        if best_val is not None:
            used.add(best_idx)
            pairs.append((nb.text.strip(), best_val))
    return pairs


def test_chest_contributions(backend) -> None:  # noqa: PLR0912
    """Test OCR text extraction on chest contribution screenshots."""
    screenshots = sorted(SCREENSHOTS_DIR.glob("chest_*.png"))
    if not screenshots:
        print("\nNo chest screenshots found.")
        return

    all_seen: dict[str, int] = {}
    for path in screenshots:
        img = cv2.imread(str(path))
        if img is None:
            continue
        for raw_name, chest_count in parse_chest_contribution_rows(img, backend):
            name = re.sub(r"\s*[A-Za-z]?\d{3,4}\s*$", "", raw_name).strip()
            if not name or len(name) < _MIN_NAME_LENGTH:
                continue
            if name not in all_seen or chest_count > all_seen[name]:
                all_seen[name] = chest_count

    matched: dict[str, tuple[str, int]] = {}
    unmatched: list[tuple[str, int, str, float]] = []
    for ocr_name, count in all_seen.items():
        m, r = best_match(ocr_name)
        if r >= THRESHOLD:
            if m not in matched or count > matched[m][1]:
                matched[m] = (ocr_name, count)
        else:
            unmatched.append((ocr_name, count, m, r))

    missing = [m for m in GUILD_MEMBERS if m not in matched]

    print("\n" + "=" * 60)
    print(f"  CHEST CONTRIBUTIONS  ({len(screenshots)} frames)")
    print(f"  Matched {len(matched)}/{len(GUILD_MEMBERS)} guild members")
    print("=" * 60)

    if missing:
        print(f"\n  Missing ({len(missing)}):")
        for m in missing:
            print(f"    {m!r}")

    if unmatched:
        print(f"\n  Unmatched OCR reads (ratio < {THRESHOLD}):")
        for ocr, cnt, m, r in sorted(unmatched, key=lambda x: -x[1]):
            print(f"    {ocr!r:32s} cnt={cnt:4d}  best={m!r} ({r:.2f})")

    print("\n  All matched (sorted by contribution desc):")
    for gm, (ocr, cnt) in sorted(matched.items(), key=lambda x: -x[1][1]):
        flag = " *" if ocr != gm else ""
        print(f"    {gm!r:30s} <- {ocr!r:30s} cnt={cnt}{flag}")


# ── Rankings parsing ──────────────────────────────────────────────────────────


def parse_rankings_frame(  # noqa: PLR0912
    screenshot, ocr_backend, y_min: int, is_supreme_arena: bool
) -> list[tuple[str | None, str]]:
    """Return list of (rank, name) pairs from one rankings screenshot."""
    ocr_results = ocr_backend.detect_text_blocks(screenshot)
    row_blocks = [r for r in ocr_results if y_min <= r.box.center.y <= _Y_MAX_RANKINGS]
    row_blocks.sort(key=lambda r: r.box.center.y)

    # Group into rows by Y proximity
    rows_grouped: list[list] = []
    for res in row_blocks:
        for group in rows_grouped:
            y_dist = abs(group[0].box.center.y - res.box.center.y)
            if y_dist < _Y_ROW_ALIGNMENT_TOLERANCE:
                group.append(res)
                break
        else:
            rows_grouped.append([res])

    pairs = []
    for row in rows_grouped:
        row_sorted = sorted(row, key=lambda r: r.box.center.x)
        if len(row_sorted) < _MIN_ROW_BLOCKS:
            continue

        rank_blocks = [b for b in row_sorted if b.box.center.x < _X_RANK_BOUNDARY]
        name_guild_blocks = [
            b
            for b in row_sorted
            if _X_RANK_BOUNDARY <= b.box.center.x < _X_SCORE_BOUNDARY
        ]
        score_blocks = [b for b in row_sorted if b.box.center.x >= _X_SCORE_BOUNDARY]
        valid_score = [b for b in score_blocks if b.text.strip().lower() != "season"]

        # Skip rows with no score column in DR mode
        if not is_supreme_arena and not valid_score:
            continue

        # Extract rank
        rank = None
        if rank_blocks:
            leftmost = min(rank_blocks, key=lambda b: b.box.center.x)
            spillover = [b for b in rank_blocks if b is not leftmost]
            name_guild_blocks = spillover + name_guild_blocks
            digits = "".join(re.findall(r"\d", leftmost.text))
            if digits and int(digits) <= _MAX_RANK_NUMBER:
                rank = digits

        # Extract name
        name = None
        if name_guild_blocks:
            score_y = valid_score[0].box.center.y if valid_score else None
            name_y_min = min(b.box.center.y for b in name_guild_blocks)
            valid = [
                b
                for b in name_guild_blocks
                if (
                    b.box.center.y < score_y - 20
                    if score_y is not None
                    else b.box.center.y - name_y_min < _Y_GUILD_OFFSET
                )
            ]
            if valid:
                raw = min(valid, key=lambda b: b.box.center.y).text.strip()
                raw = re.sub(r"\s*[A-Za-z]\d{3,4}\s*$", "", raw).strip()
                if (
                    raw
                    and len(raw) >= _MIN_NAME_LENGTH
                    and (
                        sum(1 for c in raw if c.isalnum()) / len(raw)
                        >= _MIN_NAME_ALNUM_RATIO
                    )
                ):
                    name = raw

        if name:
            pairs.append((rank, name))

    return pairs


def test_rankings(  # noqa: PLR0912, PLR0915
    rapid_backend,
    qwen_backend,
    prefix: str,
    label: str,
    is_supreme_arena: bool,
) -> None:
    """Test OCR extraction on Dream Realm and Supreme Arena ranking frames."""
    screenshots = sorted(SCREENSHOTS_DIR.glob(f"{prefix}_*.png"))
    if not screenshots:
        print(f"\nNo screenshots found for prefix '{prefix}'.")
        return

    use_qwen = qwen_backend is not None
    print(f"\n  [rankings backend: {'Qwen2-VL' if use_qwen else 'RapidOCR'}]")

    # rank -> list[name] observations
    rank_groups: dict[str, list[str]] = {}
    unranked: list[str] = []

    for idx, path in enumerate(screenshots):
        img = cv2.imread(str(path))
        if img is None:
            continue

        if use_qwen:
            h = img.shape[0]
            llm_y_min = (
                450
                if idx == 0 and not is_supreme_arena
                else (350 if is_supreme_arena else 780)
            )
            bbox_y_min = (
                820
                if idx == 0 and not is_supreme_arena
                else (350 if is_supreme_arena else 780)
            )
            scan_region = img[llm_y_min : min(h, _Y_MAX_RANKINGS), :]
            rows = qwen_backend.extract_rankings_from_screenshot(scan_region)
            if rows is not None:
                # Mirror production supplement: add RapidOCR bbox hits for guild
                # members that Qwen missed (x3 weight in canonicalization vote)
                guild_set = {
                    re.sub(r"\s*[A-Za-z]\d{3,4}\s*$", "", m).strip()
                    for m in GUILD_MEMBERS
                }
                llm_rank_names = {(rk, n) for rk, n, _ in rows if n}
                bbox_pairs = parse_rankings_frame(
                    img, rapid_backend, bbox_y_min, is_supreme_arena
                )
                supplement = [
                    (rk, n)
                    for rk, n in bbox_pairs
                    if n and (rk, n) not in llm_rank_names and n in guild_set
                ]
                for rank, row_name, _score in rows:
                    if not row_name:
                        continue
                    cleaned_row_name = re.sub(
                        r"\s*[A-Za-z]\d{3,4}\s*$", "", row_name
                    ).strip()
                    if rank:
                        rank_groups.setdefault(rank, []).append(cleaned_row_name)
                    else:
                        unranked.append(cleaned_row_name)
                # Add supplement x3 so it outweighs Qwen hallucinations
                for rank, supp_name in supplement * 3:
                    if rank:
                        rank_groups.setdefault(rank, []).append(supp_name)
                    else:
                        unranked.append(supp_name)
                continue
            # Qwen failed for this frame, fall back to bbox
            print(f"    [frame {idx}: Qwen2-VL failed, falling back to RapidOCR]")

        # RapidOCR bbox path
        if is_supreme_arena:
            y_min = 350
        elif idx == 0:
            y_min = 820
        else:
            y_min = 780
        pairs = parse_rankings_frame(img, rapid_backend, y_min, is_supreme_arena)
        for rank, name in pairs:
            if rank:
                rank_groups.setdefault(rank, []).append(name)
            else:
                unranked.append(name)

    # Canonicalize: mirrors production _canonicalize_observations
    # Sort by agreement ratio DESC (most self-consistent rank first), then obs count
    def _agreement(r: str) -> float:
        ns = rank_groups[r]
        top = Counter(n.lower() for n in ns).most_common(1)[0][1]
        return top / len(ns)

    def _rank_key(r: str) -> tuple:
        num = int(r) if r and r != "__" and r.isdigit() else 9999
        return (-_agreement(r), -len(rank_groups[r]), num)

    def _pick_best(names: list[str]) -> str | None:
        if not names:
            return None
        counts = Counter(n.lower() for n in names)
        top_lower, _ = counts.most_common(1)[0]
        return next(n for n in names if n.lower() == top_lower)

    def _fuzzy_seen(name: str, seen: set[str]) -> bool:
        nl = name.lower()
        return any(
            SequenceMatcher(None, nl, s.lower()).ratio() >= FUZZY_MATCH_THRESHOLD
            for s in seen
        )

    canonical_names: list[str] = []
    seen_canonical: set[str] = set()

    for rank in sorted(rank_groups, key=_rank_key):
        names = rank_groups[rank]
        canonical = _pick_best(names)
        if not canonical:
            continue
        if _fuzzy_seen(canonical, seen_canonical):
            # Top pick already assigned — try alternates not seen elsewhere
            alts = [n for n in names if not _fuzzy_seen(n, seen_canonical)]
            canonical = _pick_best(alts)
            if not canonical:
                continue
        seen_canonical.add(canonical)
        canonical_names.append(canonical)

    # Unranked names seen at least twice
    for name, cnt in Counter(unranked).items():
        if cnt >= UNRANKED_MIN_COUNT and not _fuzzy_seen(name, seen_canonical):
            seen_canonical.add(name)
            canonical_names.append(name)

    print("\n" + "=" * 60)
    print(
        f"  {label}  ({len(screenshots)} frames, "
        f"{len(canonical_names)} canonical entries)"
    )
    print("=" * 60)

    matched: dict[str, tuple[str, float]] = {}
    unmatched: list[tuple[str, str, float]] = []
    for name in canonical_names:
        m, r = best_match(name)
        if r >= THRESHOLD:
            if m not in matched or r > matched[m][1]:
                matched[m] = (name, r)
        else:
            unmatched.append((name, m, r))

    missing = [m for m in GUILD_MEMBERS if m not in matched]

    print(f"\n  Matched {len(matched)}/{len(GUILD_MEMBERS)} guild members")

    if missing:
        print(f"\n  Missing ({len(missing)}):")
        for m in missing:
            print(f"    {m!r}")

    if unmatched:
        print(f"\n  Unmatched OCR reads (ratio < {THRESHOLD}):")
        for ocr, m, r in sorted(unmatched, key=lambda x: x[0].lower()):
            print(f"    {ocr!r:32s} best={m!r} ({r:.2f})")

    print("\n  All matched (alphabetical):")
    for gm, (ocr, r) in sorted(matched.items(), key=lambda x: x[0].lower()):
        flag = f" * ({r:.2f})" if ocr != gm else ""
        print(f"    {gm!r:30s} <- {ocr!r}{flag}")


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    """Execute main script logic to test OCR performance on debug frames."""
    rapid = RapidOCRBackend.pp_ocr_v5_rec()

    # Try to load Qwen2-VL for rankings (mirrors production _select_ocr_backend)
    qwen = None
    if QwenVLOCRBackend.has_sufficient_vram():
        print("[rankings] GPU detected — using Qwen2-VL-2B for DR/SA rankings.")
        qwen = QwenVLOCRBackend()
    else:
        print(
            "[rankings] No GPU / insufficient VRAM — using RapidOCR for DR/SA rankings."
        )

    test_activeness(rapid)
    test_chest_contributions(rapid)

    # Find all ranking prefixes dynamically (dr_*, sa_*)
    dr_prefixes = sorted(
        {"_".join(p.name.split("_")[:2]) for p in SCREENSHOTS_DIR.glob("dr_*.png")}
    )
    sa_prefixes = sorted(
        {"_".join(p.name.split("_")[:2]) for p in SCREENSHOTS_DIR.glob("sa_*.png")}
    )

    for prefix in dr_prefixes:
        test_rankings(
            rapid, qwen, prefix, f"DREAM REALM — {prefix}", is_supreme_arena=False
        )

    for prefix in sa_prefixes:
        test_rankings(
            rapid, qwen, prefix, f"SUPREME ARENA — {prefix}", is_supreme_arena=True
        )


if __name__ == "__main__":
    main()
