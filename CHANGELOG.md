# Changelog

This changelog records published source releases and verified local build artifacts. An entry under Unreleased is not a published release.

## v1.2.0 — Published (commit `ee1a255`, tag `v1.2.0`, 2026-10-08)

### Release preparation

- Prepared VehicleCheck v1.2.0 with a single `APP_VERSION` source, matching GUI title, and a maintained one-file Windows spec that derives executable naming and version metadata from that constant.
- Built `dist/VehicleCheck-1.2.0.exe`; the owner manually launched it and confirmed the GUI opened and the application ran successfully. **VehicleCheck v1.2.0 GUI SMOKE TEST: PASS.**
- The full test suite passed: 54 tests, 0 failures, 0 errors. The PyInstaller build succeeded and Windows version metadata was verified.
- Published source state: commit `ee1a255`, tag `v1.2.0`; `main` is synchronized with `origin/main`.
- Built the separate `dist/VehicleCheck-Notifications-1.2.0.exe` from `notifications.py` (9,160,901 bytes, PyInstaller 6.22.2). It is one-file, console-enabled, uses shared version metadata, and has no embedded SMTP password. `--help` exited 0 and showed all supported options.
- The authorized `--type DAY27 --dry-run` run exited 1 and produced no preview lines. It did not send email or update notification markers; SQL-read validation remains incomplete.
- Notification EXE status: **built / deployment pending**. No file was copied to `srv-sql`, and no scheduled task was created. The GUI binary design was not changed.

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

The previous released source version was `1.1.0` (version commit `63c4db8`, dated 2026-09-14). VehicleCheck v1.2.0 is published from commit `ee1a255` under tag `v1.2.0`. Central notification deployment remains pending.

## Technical debt / deferred risks

- **F-07 — ACCEPTED / DEFERRED RISK for v1.2.0:** Keep the current SMTP-send-then-marker sequence for this release and accept the rare duplicate window if the marker is not committed after SMTP acceptance. Do not mark before sending or rush a schema change before release.
- Future work: evaluate a durable notification outbox/audit mechanism with notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This is not implemented and does not imply exactly-once SMTP delivery.
