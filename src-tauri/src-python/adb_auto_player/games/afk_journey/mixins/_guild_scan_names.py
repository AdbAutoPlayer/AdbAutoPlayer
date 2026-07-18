"""Guild scan: name canonicalization and guild member matching."""

import json
import logging
import re
import urllib.request
from collections import Counter
from difflib import SequenceMatcher
from urllib.parse import parse_qs, urlparse

from ._guild_scan_setup import _GuildScanSetupMixin


class _GuildScanNamesMixin(_GuildScanSetupMixin):
    """Name canonicalization, fuzzy matching, and guild member correction."""

    def _canonicalize_observations(
        self,
        observations: list[tuple[str | None, str | None]],
        date_name: str,
    ) -> list[dict]:
        """Group by rank, pick best name per player via frequency consensus."""
        rank_groups: dict[str, list[str]] = {}
        unranked: list[str] = []

        for rank, name in observations:
            if not name:
                continue
            if rank:
                rank_groups.setdefault(rank, []).append(name)
            else:
                unranked.append(name)

        self._merge_truncated_rank_duplicates(rank_groups)

        results: list[dict] = []
        canonical_names: set[str] = set()

        def _agreement(r: str) -> float:
            names = rank_groups[r]
            if not names:
                return 0.0
            top = Counter(n.lower() for n in names).most_common(1)[0][1]
            return top / len(names)

        def _rank_sort_key(r: str) -> tuple:
            num = int(r) if r.isdigit() else 9999
            return (-_agreement(r), -len(rank_groups[r]), num)

        for rank in sorted(rank_groups, key=_rank_sort_key):
            names = rank_groups[rank]
            canonical = self._pick_canonical_name(names)
            if not canonical:
                continue
            if self._find_fuzzy_match(canonical, canonical_names) is not None:
                alt_names = [
                    n
                    for n in names
                    if self._find_fuzzy_match(n, canonical_names) is None
                    and not self._name_appears_more_elsewhere(n, rank, rank_groups)
                ]
                canonical = self._pick_canonical_name(alt_names)
                if not canonical:
                    logging.debug(
                        f"Rank {rank}: top candidate already covered, "
                        "no valid alternative found, skipping."
                    )
                    continue
                logging.debug(
                    f"Rank {rank}: top candidate already covered, "
                    f"using alternative {canonical!a}."
                )
            canonical_names.add(canonical)
            results.append({"Date": date_name, "Rank": rank, "Name": canonical})

        for group in self._group_by_similarity(unranked):
            if len(group) < self._MIN_UNRANKED_OBSERVATIONS:
                continue
            canonical = self._pick_canonical_name(group)
            if not canonical:
                continue
            if self._find_fuzzy_match(canonical, canonical_names) is not None:
                continue
            canonical_names.add(canonical)
            results.append({"Date": date_name, "Rank": "", "Name": canonical})

        results.sort(
            key=lambda e: int(e["Rank"]) if e["Rank"].isdigit() else float("inf")
        )
        logging.info(f"Canonicalized {len(results)} entries for {date_name}.")
        return results

    def _merge_truncated_rank_duplicates(
        self, rank_groups: dict[str, list[str]]
    ) -> None:
        """Merge a rank whose observations are a truncated misread of a longer rank.

        OCR badge noise (e.g. garbled characters merging into the digits)
        drops a trailing digit far more often than it invents one — "288"
        misread as "28" rather than the other way round. When the same name
        dominates both a rank and a longer rank sharing the same leading
        digits, an exact tie between them would otherwise be broken by
        preferring the smaller (wrong, truncated) rank number, and the
        longer (correct) rank would be silently dropped entirely as an
        already-claimed duplicate. Fold the short group into the long one
        instead of letting them compete as separate ranks.
        """
        for short_rank in list(rank_groups):
            short_names = rank_groups.get(short_rank)
            if not short_names or not short_rank.isdigit():
                continue
            short_top = Counter(n.lower() for n in short_names).most_common(1)[0][0]
            for long_rank in list(rank_groups):
                if (
                    long_rank == short_rank
                    or not long_rank.isdigit()
                    or len(long_rank) <= len(short_rank)
                    or not long_rank.startswith(short_rank)
                ):
                    continue
                long_names = rank_groups.get(long_rank)
                if not long_names:
                    continue
                long_top = Counter(n.lower() for n in long_names).most_common(1)[0][0]
                if long_top == short_top:
                    rank_groups[long_rank] = long_names + short_names
                    del rank_groups[short_rank]
                    break

    def _group_by_similarity(self, names: list[str]) -> list[list[str]]:
        """Cluster names into groups where each pair is fuzzy-similar."""
        groups: list[list[str]] = []
        for name in names:
            placed = False
            for group in groups:
                if (
                    SequenceMatcher(None, name.lower(), group[0].lower()).ratio()
                    >= self._FUZZY_DEDUP_THRESHOLD
                ):
                    group.append(name)
                    placed = True
                    break
            if not placed:
                groups.append([name])
        return groups

    def _pick_canonical_name(self, names: list[str]) -> str | None:
        """Return best name from OCR observations: most frequent fuzzy cluster wins."""
        quality = [
            n
            for n in names
            if n
            and len(n) >= self._MIN_NAME_LENGTH
            and sum(1 for c in n if c.isalnum()) / len(n) >= self._MIN_NAME_ALNUM_RATIO
        ]
        if not quality:
            return None

        best_group = max(self._group_by_similarity(quality), key=len)

        counts = Counter(n.lower() for n in best_group)
        max_count = counts.most_common(1)[0][1]
        top = [n for n in best_group if counts[n.lower()] == max_count]

        return min(
            top,
            key=lambda n: (
                -sum(1 for c in n if c.isalnum()) / len(n),
                len(n),
            ),
        )

    def _name_appears_more_elsewhere(
        self,
        name: str,
        rank: str,
        rank_groups: dict[str, list[str]],
    ) -> bool:
        """Return True if `name` has more observations at any rank other than `rank`.

        Used to exclude alt candidates that truly belong at a different rank —
        e.g. a player seen once at rank 15 (hallucination) but five times at
        rank 25 (correct) should NOT be used as the alt at rank 15.
        """
        name_lower = name.lower()
        count_here = sum(
            1 for n in rank_groups.get(rank, []) if n.lower() == name_lower
        )
        return any(
            sum(1 for n in v if n.lower() == name_lower) > count_here
            for r, v in rank_groups.items()
            if r != rank
        )

    def _find_fuzzy_match(self, name: str, seen_names: set[str]) -> str | None:
        """Return the matched seen name if similar to `name`, else None."""
        name_lower = name.lower()
        for seen in seen_names:
            ratio = SequenceMatcher(None, name_lower, seen.lower()).ratio()
            if ratio >= self._FUZZY_DEDUP_THRESHOLD:
                return seen
        return None

    def _fetch_guild_members(self) -> list[str]:
        """Fetch guild member names from the configured API URL for name correction."""
        url = self.settings.guild_manager_scan.guild_members_api_url
        if not url:
            return []
        try:
            req = urllib.request.Request(url)
            parsed = urlparse(url)
            apikey = parse_qs(parsed.query).get("apikey", [""])[0]
            if apikey:
                req.add_header("apikey", apikey)
            req.add_header("Cache-Control", "no-cache")
            req.add_header("Pragma", "no-cache")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and "state" in data[0]:
                names = [
                    p["name"]
                    for p in data[0]["state"].get("players", [])
                    if p.get("name")
                ]
                logging.info(f"Fetched {len(names)} guild members for name correction.")
                return names
        except Exception as e:
            logging.warning(f"Could not fetch guild members: {e}")
        return []

    def _clean_member_name(self, name: str, suffix_pat: re.Pattern) -> str:
        """Clean a name by removing suffix codes and noise words."""
        cleaned = suffix_pat.sub("", name.lower())
        name_clean = "".join(c for c in cleaned if c.isalnum() or c.isspace())
        words = []
        for w in name_clean.split():
            if (
                len(w) > 1
                or not w.isalpha()
                or any(ord(c) > self._MAX_ASCII_VAL for c in w)
            ):
                words.append(w)
        return "".join(words)

    def _to_visual_latin(self, text: str) -> str:
        """Map Cyrillic characters to visually similar Latin homoglyphs."""
        mapping = {
            "\u0430": "a",
            "\u0431": "6",
            "\u0432": "b",
            "\u0433": "r",
            "\u0434": "g",
            "\u0435": "e",
            "\u0451": "e",
            "\u0436": "k",
            "\u0437": "3",
            "\u0438": "u",
            "\u0439": "u",
            "\u043a": "k",
            "\u043b": "n",
            "\u043c": "m",
            "\u043d": "h",
            "\u043e": "o",
            "\u043f": "n",
            "\u0440": "p",
            "\u0441": "c",
            "\u0442": "m",
            "\u0443": "y",
            "\u0444": "o",
            "\u0445": "x",
            "\u0446": "u",
            "\u0447": "u",
            "\u0448": "w",
            "\u0449": "w",
            "\u044a": "b",
            "\u044b": "bi",
            "\u044c": "b",
            "\u044d": "3",
            "\u044e": "io",
            "\u044f": "r",
            "\u0410": "A",
            "\u0411": "6",
            "\u0412": "B",
            "\u0413": "R",
            "\u0414": "G",
            "\u0415": "E",
            "\u0401": "E",
            "\u0416": "K",
            "\u0417": "3",
            "\u0418": "U",
            "\u0419": "U",
            "\u041a": "K",
            "\u041b": "N",
            "\u041c": "M",
            "\u041d": "H",
            "\u041e": "O",
            "\u041f": "N",
            "\u0420": "P",
            "\u0421": "C",
            "\u0422": "M",
            "\u0423": "Y",
            "\u0425": "X",
            "\u0426": "U",
            "\u0427": "U",
            "\u0428": "W",
            "\u0429": "W",
            "\u042b": "Bi",
            "\u042f": "R",
        }
        return "".join(mapping.get(c, c) for c in text)

    def _strip_diacritics(self, text: str) -> str:
        """Replace non-ASCII diacritics with their base ASCII equivalents."""
        import unicodedata  # noqa: PLC0415

        _map = {
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
        result = []
        for c in text:
            mapped = _map.get(c)
            if mapped is not None:
                result.append(mapped)
                continue
            nfd = unicodedata.normalize("NFD", c)
            ascii_base = nfd.encode("ascii", "ignore").decode("ascii")
            result.append(ascii_base if ascii_base else c)
        return "".join(result)

    def _find_best_member_match(
        self,
        name: str,
        cleaned_members: list[tuple[str, str]],
        suffix_pat: re.Pattern,
    ) -> tuple[str, float]:
        """Find the closest guild member match and returns (best_match, ratio)."""
        name_clean = self._clean_member_name(name, suffix_pat)
        _hangul_pat = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
        korean_members = [m for m, _ in cleaned_members if _hangul_pat.search(m)]
        if korean_members:
            is_korean = bool(_hangul_pat.search(name))
            is_misread = name_clean in ("号1o", "号10", "号10g", "号1og", "号lo")
            _cjk_pat = re.compile(r"[一-鿿぀-ヿ豈-﫿]")
            is_cjk_misread = bool(_cjk_pat.search(name_clean)) and not any(
                name_clean == mc for _, mc in cleaned_members if _cjk_pat.search(mc)
            )
            if is_korean or is_cjk_misread or is_misread:
                if len(korean_members) == 1:
                    return korean_members[0], 1.0
                best_k, best_k_ratio = korean_members[0], 0.0
                for km in korean_members:
                    kmc = self._clean_member_name(km, suffix_pat)
                    r = SequenceMatcher(None, name_clean, kmc).ratio()
                    if r > best_k_ratio:
                        best_k_ratio, best_k = r, km
                return best_k, max(best_k_ratio, 0.7)

        if not name_clean:
            return name, 0.0

        name_clean = self._strip_diacritics(name_clean)
        name_visual = self._to_visual_latin(name_clean)

        best_ratio = 0.0
        best_match = name

        for member, member_clean in cleaned_members:
            member_visual = self._to_visual_latin(self._strip_diacritics(member_clean))
            if name_visual == member_visual:
                return member, 1.0

            ratio = SequenceMatcher(None, name_visual, member_visual).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = member

        return best_match, best_ratio

    def _correct_names_with_guild_members(
        self, rankings: list[dict], guild_members: list[str]
    ) -> list[dict]:
        """Replace OCR-misread names with the closest matching guild member name."""
        if not guild_members:
            return rankings

        suffix_pat = re.compile(r"\b[A-Za-z]?\d{3,4}\b")

        cleaned_members = [
            (m, self._clean_member_name(m, suffix_pat)) for m in guild_members
        ]

        corrected_entries: list[dict] = []

        for entry in rankings:
            name = entry["Name"]
            best_match, best_ratio = self._find_best_member_match(
                name, cleaned_members, suffix_pat
            )

            if best_ratio >= self._GUILD_NAME_CORRECTION_THRESHOLD:
                if best_match != name:
                    logging.debug(
                        f"Name corrected: {name!a} -> {best_match!a} ({best_ratio:.2f})"
                    )
                new_entry = entry.copy()
                new_entry["Name"] = best_match
                new_entry["_match_ratio"] = best_ratio
                corrected_entries.append(new_entry)
            else:
                logging.debug(
                    f"Name discarded as non-guild member noise: {name!a} "
                    f"(best: {best_match!a}, ratio: {best_ratio:.2f})"
                )

        dedup_dict: dict[tuple[str, str], dict] = {}
        for entry in corrected_entries:
            key = (entry.get("Date", ""), entry["Name"])
            existing = dedup_dict.get(key)
            if not existing:
                dedup_dict[key] = entry
                continue

            curr_ratio = entry["_match_ratio"]
            ex_ratio = existing["_match_ratio"]
            if curr_ratio > ex_ratio:
                dedup_dict[key] = entry
            elif (
                curr_ratio == ex_ratio
                and entry.get("Rank")
                and not existing.get("Rank")
            ):
                dedup_dict[key] = entry

        final_rankings = []
        for entry in dedup_dict.values():
            entry.pop("_match_ratio", None)
            final_rankings.append(entry)

        def _get_rank_key(e: dict) -> float:
            r = e.get("Rank", "")
            return int(r) if r.isdigit() else float("inf")

        final_rankings.sort(key=_get_rank_key)

        return final_rankings

    def _correct_single_name(self, name: str, guild_members: list[str]) -> str:
        """Return the closest guild member name to `name`."""
        suffix_pat = re.compile(r"\b[A-Za-z]?\d{3,4}\b")
        cleaned_members = [
            (m, self._clean_member_name(m, suffix_pat)) for m in guild_members
        ]
        best_match, best_ratio = self._find_best_member_match(
            name, cleaned_members, suffix_pat
        )
        return (
            best_match if best_ratio >= self._GUILD_NAME_CORRECTION_THRESHOLD else name
        )
