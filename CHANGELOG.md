# Changelog

## [12.8.18] - 2026-05-13

### Fixed

- ⚔️ **AFK Journey**: Prevented false positive victory evaluations during battle completion by ensuring that matching the statistics icon (`battle/result.png`) is strictly cross-validated against defeat overlays and retry indicators, restoring accurate tracking and automatic replay loops for failed stages.
- ⚔️ **AFK Journey**: Resolved automated navigation blocks in **AFK Stages** and **Season AFK Stages** where the sequence could fail to tap continuation triggers after dismissing post-battle popups; the bot now reliably awaits and triggers subsequent "Next" actions to maintain continuous stage pushing.
