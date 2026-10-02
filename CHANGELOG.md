# Changelog

## [12.13.2] - 2026-10-02

### Added

- **Guild Manager Scan – Members with the same name**: When two or more guild members share a name, the scan opens the player's profile panel and reads the "User ID" / "Server" line to tell them apart. On the rankings it taps the row; on the guild member list it taps the avatar. Each one is exported as a separate entry with an "Id" field (the Guild Manager id). If they are on the same server and have no `userId` set in the Guild Manager, a warning asks to enter it and only one of them is exported. Chest contributions of shared names are left empty to be entered by hand, because the chest ranking has no profile panel.
- **Guild Manager Scan – Korean and Cyrillic names**: The default OCR model can't read Hangul or Cyrillic, so these names came out as noise (e.g. "丘号" for "도로롱", "CKnTaJe" for "Скиталец") or weren't read at all. When the guild has such members, the name line is read again with the PP-OCRv5 Korean / Cyrillic models, on both the rankings and the activeness list.

### Bug Fixes

- **Guild Manager Scan**: Two members whose short names differ by one letter (e.g. "Toki" and "Loki") were merged as OCR variants of the same player. They are now kept separate when both are in the Guild Manager.
- **Guild Manager Scan**: The player's own row, pinned at the top or bottom of the rankings, was merged into the row next to it and took its rank. It is now ignored.
- **Guild Manager Scan**: A misread Korean name that couldn't be recovered was matched to a Korean member anyway, so several rows could end up assigned to the same person. It is now dropped instead. A one-letter OCR mistake in a Korean name (e.g. "또강" for "또깅") is still matched to the right member.
- **Guild Manager Scan**: The Dream Realm and Supreme Arena rankings stopped after 25 scrolls, so long lists weren't read to the end. The limit is now 60.
