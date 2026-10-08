# Changelog

Changes recorded here are based on local committed source history. An entry under Unreleased is not a published release.

## v1.2.0 — Ready for release (local commit `0704f87`, 2026-10-08)

### Release preparation

- Prepared VehicleCheck v1.2.0 with a single `APP_VERSION` source, matching GUI title, and a maintained one-file Windows spec that derives executable naming and version metadata from that constant.
- Built `dist/VehicleCheck-1.2.0.exe`; the owner manually launched it and confirmed the GUI opened and the application ran successfully. **VehicleCheck v1.2.0 GUI SMOKE TEST: PASS.**
- The full test suite passed: 54 tests, 0 failures, 0 errors. The PyInstaller build succeeded and Windows version metadata was verified.
- Release commit `0704f87` exists locally. It has not been pushed or tagged; v1.2.0 has not been deployed.

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

The previous released source version was `1.1.0` (version commit `63c4db8`, dated 2026-09-14). The current local release commit is `0704f87` and sets `APP_VERSION` to `1.2.0`. v1.2.0 is READY FOR RELEASE; it has not been pushed, tagged, or deployed.

## Technical debt / deferred risks

- **F-07 — ACCEPTED / DEFERRED RISK for v1.2.0:** Keep the current SMTP-send-then-marker sequence for this release and accept the rare duplicate window if the marker is not committed after SMTP acceptance. Do not mark before sending or rush a schema change before release.
- Future work: evaluate a durable notification outbox/audit mechanism with notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This is not implemented and does not imply exactly-once SMTP delivery.
