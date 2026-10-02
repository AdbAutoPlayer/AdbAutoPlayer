"""Guild scan: telling apart guild members who share the same name.

The rankings list only shows avatar, name, server badge and score, so two
members both called e.g. "모험가" are indistinguishable there and used to
collapse into a single entry. For rows of such names the scan opens the
player's profile panel (tap on the row) and reads the footer
"User ID: 44942604  Server: G439", then matches it against the roster's
`userId` (or `server`, when the namesakes are on different servers).

An identified row carries an internal label "<name>#<roster id>" through
canonicalization so the namesakes don't dedupe into one; the exported entry
gets back the plain name plus an "Id" field with the roster id.
"""

import logging
import re
from time import sleep

import cv2
import numpy as np
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.ocr import OCRBackend

from ._guild_scan_names import _GuildScanNamesMixin

_PROFILE_USER_ID_RE = re.compile(r"User\s*ID\s*[:\uff1a]?\s*(\d{5,})", re.IGNORECASE)
_PROFILE_SERVER_RE = re.compile(
    r"Server\s*[:\uff1a]?\s*([A-Za-z]\d{3,4})", re.IGNORECASE
)
_IDENTITY_LABEL_RE = re.compile(r"^(.*)#(\d+)$")


class _GuildScanIdentityMixin(_GuildScanNamesMixin):
    """Identify same-named guild members through their profile panel."""

    _X_ROW_TAP = 600
    _PROFILE_CLOSE = (540, 1815)
    _PROFILE_ROW_EDGE_MARGIN = 60
    _PROFILE_OPEN_WAIT = 2.0
    _PROFILE_CLOSE_WAIT = 1.5
    _PROFILE_READ_ATTEMPTS = 2
    _ROW_STABLE_HALF_HEIGHT = 60
    _ROW_STABLE_MAX_DIFF = 5.0
    # Guild members list: the avatar sits left of the name, ~55 px lower.
    _X_AVATAR_TAP = 130
    _AVATAR_BELOW_NAME_OFFSET = 55
    _Y_AVATAR_TAP_MIN = 660
    _Y_AVATAR_TAP_MAX = 1560

    def _analyze_duplicate_names(self, players: list[dict]) -> None:
        """Group roster records sharing a name and warn when they can't be told apart.

        Args:
            players: Roster player records from the Guild Manager API.
        """
        groups: dict[str, list[dict]] = {}
        for p in players:
            groups.setdefault(self._normalize_name_key(p["name"]), []).append(p)
        self._duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}

        for records in self._duplicate_groups.values():
            name = records[0]["name"]
            servers = [str(r.get("server") or "").upper() for r in records]
            if all(str(r.get("userId") or "").strip() for r in records):
                how = "their User ID"
            elif all(servers) and len(set(servers)) == len(servers):
                how = "their server"
            else:
                logging.warning(
                    f"{len(records)} guild members are named {name!r} on the same "
                    "server. Enter each one's in-game User ID (Profile panel, "
                    "bottom line) in the userId field of the Guild Manager to "
                    "tell them apart; until then only one of them is exported."
                )
                continue
            logging.info(
                f"{len(records)} guild members are named {name!r}: their rows "
                f"will be identified by opening the profile panel ({how})."
            )

    def _duplicate_group(self, name: str | None) -> list[dict] | None:
        if not name:
            return None
        groups = getattr(self, "_duplicate_groups", None) or {}
        return groups.get(self._normalize_name_key(name))

    def _identity_labels(self) -> list[str]:
        """Return the internal "<name>#<id>" label of every same-named member."""
        groups = getattr(self, "_duplicate_groups", None) or {}
        return [self._identity_label(r) for records in groups.values() for r in records]

    @staticmethod
    def _identity_label(record: dict) -> str:
        return f"{record['name']}#{record['id']}"

    def _split_identity_label(self, name: str) -> tuple[str, int | str] | None:
        """Return (name, roster id) for an identity label, else None."""
        match = _IDENTITY_LABEL_RE.match(name)
        if not match:
            return None
        for record in self._duplicate_group(match.group(1)) or []:
            if str(record["id"]) == match.group(2):
                return record["name"], record["id"]
        return None

    def _identify_duplicate_row(
        self,
        result: tuple[str | None, str | None, str | None],
        row_sorted: list[OCRResult],
        y_min: int,
        ocr_backend: OCRBackend,
        screenshot,
    ) -> tuple[str | None, str | None, str | None]:
        """Replace a shared name with its member's identity label, if possible.

        Rows cut off at the list edges are skipped (a tap there could hit the
        pinned own-player row); they show up whole in a neighbouring frame.
        The result is cached per (rank, score), so each row is opened once
        per date even though it appears in several frames.
        """
        rank, name, score = result
        group = self._duplicate_group(name)
        if not group or not rank:
            return result

        cache = self.__dict__.setdefault("_identity_cache", {})
        key = (rank, score)
        if key not in cache:
            row_y = int(sum(b.box.center.y for b in row_sorted) / len(row_sorted))
            margin = self._PROFILE_ROW_EDGE_MARGIN
            if not (y_min + margin <= row_y <= self._Y_MAX_RANKINGS - margin):
                return result
            attempted, record = self._open_profile_and_match(
                Point(self._X_ROW_TAP, row_y), row_y, screenshot, group, ocr_backend
            )
            if not attempted:
                return result
            cache[key] = self._identity_label(record) if record else None
            if record:
                logging.info(
                    f"Rank {rank}: {name!a} identified as roster id {record['id']}."
                )
        label = cache[key]
        return (rank, label, score) if label else result

    def _identify_member_by_avatar(
        self, name: str, name_y: int, screenshot, ocr_backend: OCRBackend
    ) -> str:
        """Guild members list: identify a shared name by tapping its avatar.

        On this screen only the avatar opens the profile panel (a tap on the
        row does nothing). Returns the identity label, or `name` unchanged.
        """
        group = self._duplicate_group(name)
        avatar_y = name_y + self._AVATAR_BELOW_NAME_OFFSET
        if not group or not (
            self._Y_AVATAR_TAP_MIN <= avatar_y <= self._Y_AVATAR_TAP_MAX
        ):
            return name
        _, record = self._open_profile_and_match(
            Point(self._X_AVATAR_TAP, avatar_y), name_y, screenshot, group, ocr_backend
        )
        if not record:
            return name
        logging.info(f"Guild member {name!a} identified as roster id {record['id']}.")
        return self._identity_label(record)

    def _row_unchanged(self, screenshot, fresh, row_y: int) -> bool:
        """Return True if the row strip is pixel-identical-ish in both frames.

        A list still settling from the swipe's inertia shifts every row by a
        few pixels, enough to tap a neighbouring player: a 3 px shift already
        gives a mean difference of ~11, a still list stays below ~1.
        """
        half = self._ROW_STABLE_HALF_HEIGHT
        top, bottom = max(0, row_y - half), row_y + half
        before = cv2.cvtColor(screenshot[top:bottom], cv2.COLOR_BGR2GRAY)
        after = cv2.cvtColor(fresh[top:bottom], cv2.COLOR_BGR2GRAY)
        if before.shape != after.shape or before.size == 0:
            return False
        diff = np.abs(before.astype(np.int16) - after.astype(np.int16)).mean()
        return float(diff) <= self._ROW_STABLE_MAX_DIFF

    def _open_profile_and_match(
        self,
        tap_point: Point,
        row_y: int,
        screenshot,
        group: list[dict],
        ocr_backend: OCRBackend,
    ) -> tuple[bool, dict | None]:
        """Tap, read User ID / Server from the profile panel, close it.

        Returns (attempted, record). `attempted` is False when the row moved
        since `screenshot` was analysed: nothing was tapped, and the row is
        retried from a later frame.
        """
        if not self._row_unchanged(screenshot, self.get_screenshot(), row_y):
            logging.debug(f"Row at y={row_y} moved since the frame; not tapping.")
            return False, None

        self.tap(tap_point, log=False)
        sleep(self._PROFILE_OPEN_WAIT)
        user_id = server = None
        for _ in range(self._PROFILE_READ_ATTEMPTS):
            user_id, server = self._read_profile_identity(
                ocr_backend.detect_text_blocks(self.get_screenshot())
            )
            if user_id:
                break
            sleep(1)
        if not user_id:
            # The panel didn't open (or isn't readable): don't tap "close",
            # on the list that spot is the bottom navigation bar.
            logging.warning("Could not read the User ID from the profile panel.")
            return True, None

        self.tap(Point(*self._PROFILE_CLOSE), log=False)
        sleep(self._PROFILE_CLOSE_WAIT)
        return True, self._match_duplicate_record(group, user_id, server)

    @staticmethod
    def _read_profile_identity(
        blocks: list[OCRResult],
    ) -> tuple[str | None, str | None]:
        """Return (user id, server) from the profile panel's footer line."""
        for block in blocks:
            id_match = _PROFILE_USER_ID_RE.search(block.text)
            if id_match:
                server_match = _PROFILE_SERVER_RE.search(block.text)
                server = server_match.group(1).upper() if server_match else None
                return id_match.group(1), server
        return None, None

    @staticmethod
    def _match_duplicate_record(
        group: list[dict], user_id: str, server: str | None
    ) -> dict | None:
        """Pick the namesake whose userId (or, failing that, server) matches."""
        for record in group:
            if str(record.get("userId") or "").strip() == user_id:
                return record
        if server:
            same_server = [
                r for r in group if str(r.get("server") or "").upper() == server
            ]
            if len(same_server) == 1:
                return same_server[0]
        logging.warning(
            f"Profile User ID {user_id} (server {server}) matches none of the "
            f"members named {group[0]['name']!r}; check their userId in the "
            "Guild Manager."
        )
        return None

    def _roster_name_keys(self) -> set[str]:
        """Roster keys plus identity labels, so namesakes never dedupe together."""
        return super()._roster_name_keys() | {
            self._normalize_name_key(label) for label in self._identity_labels()
        }

    def _correct_names_with_guild_members(
        self, rankings: list[dict], guild_members: list[str]
    ) -> list[dict]:
        """Export identified namesakes as their plain name plus the roster "Id"."""
        identified: list[dict] = []
        others: list[dict] = []
        for entry in rankings:
            ident = self._split_identity_label(entry["Name"])
            if ident:
                name, roster_id = ident
                identified.append({**entry, "Name": name, "Id": roster_id})
            else:
                others.append(entry)
        identified_names = {e["Name"] for e in identified}
        corrected = [
            e
            for e in super()._correct_names_with_guild_members(others, guild_members)
            # A leftover unidentified sighting of a namesake would otherwise
            # be imported as "the" member with that name.
            if e["Name"] not in identified_names
        ]

        def _rank_key(e: dict) -> float:
            r = e.get("Rank", "")
            return int(r) if r.isdigit() else float("inf")

        return sorted(identified + corrected, key=_rank_key)

    def _is_sighting_of(self, name: str | None, label: str | None) -> bool:
        """Return True if `name` is the plain name behind identity `label`."""
        match = _IDENTITY_LABEL_RE.match(label) if label else None
        return bool(match and name) and self._normalize_name_key(
            name
        ) == self._normalize_name_key(match.group(1))

    def _carry_identity_labels(self, rows: list[tuple], bbox_rows: list[tuple]) -> list:
        """Copy identity labels from the bbox rows onto Qwen rows at the same rank."""
        label_by_rank = {
            rk: nm
            for rk, nm, _ in bbox_rows
            if rk and nm and self._split_identity_label(nm)
        }
        return [
            (
                rk,
                label_by_rank[rk]
                if self._is_sighting_of(nm, label_by_rank.get(rk))
                else nm,
                sc,
            )
            for rk, nm, sc in rows
        ]

    def _apply_identity_labels(
        self, observations: list[tuple[str | None, str | None]]
    ) -> list[tuple[str | None, str | None]]:
        """Relabel plain sightings of a shared name at a rank already identified.

        A row is opened only once, and only when fully visible; its other
        sightings (cut-off frames) still carry the plain name and would
        otherwise outvote or split the identified one.
        """
        label_by_rank: dict[str, str] = {}
        for rank, name in observations:
            if rank and name and self._split_identity_label(name):
                label_by_rank[rank] = name
        relabeled: list[tuple[str | None, str | None]] = []
        for rank, name in observations:
            label = label_by_rank.get(rank) if rank else None
            if label and self._is_sighting_of(name, label):
                relabeled.append((rank, label))
            else:
                relabeled.append((rank, name))
        return relabeled
