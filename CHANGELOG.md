# Changelog

Changes recorded here are based on local committed source history. An entry under Unreleased is not a published release.

## Unreleased (local commits dated 2026-10-07 to 2026-10-08)

### Added

- Added a notification type filter for CRP, DAY27, DAY30, and OVERDUE processing (`9068e80`).
- Highlighted main vehicle-list rows red when the displayed Countdown is `<= 3` (`7dcc824`). This is a separate UI enhancement, not F-06.

### Changed

- Updated the README to describe CARSM and vehicle filtering (`eded1fe`).
- Aligned runtime tests with the current production connection behavior (`34ceb48`).

### Fixed

- Fixed F-01, the notifications CLI entry point, including safe dry-run behavior (`e30c2b7`).
- Fixed F-06 missed-run behavior with DAY27 catch-up on cycle days 27–29 (`925a8b4`). The marker is scoped to the current cycle.

## Release history

The source declares version `1.1.0` in `version.py` (version commit `63c4db8`, dated 2026-09-14). No corresponding Git tag or published release was verified during this documentation update, so this changelog does not assert a release date or deployed artifact for that version.

The next planned release is v1.2.0; it has not been versioned or released in the inspected repository.
