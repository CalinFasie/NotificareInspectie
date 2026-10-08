# Changelog

This changelog records published source releases and verified local build artifacts. **READY FOR RELEASE** means the local release checks passed; it has not been published until separate Git release steps are completed.

## v1.2.1 — READY FOR RELEASE

This release is prepared from the source after the published `v1.2.0` tag. The existing `v1.2.0` tag remains at commit `ee1a255`.

### Packaging

- Set the shared `APP_VERSION` to `1.2.1`; both maintained PyInstaller specs derive executable names and Windows version metadata from it.
- Build `VehicleCheck-1.2.1.exe` as the existing one-file, windowed GUI and `VehicleCheck-Notifications-1.2.1.exe` as a one-file console build from `notifications.py`.
- Both builds succeeded with PyInstaller 6.22.2. GUI size: 11,842,112 bytes. Notification size: 9,159,999 bytes. Requested Windows metadata was verified for both artifacts.
- The full unit suite passed: 54 tests, 0 failures, 0 errors. Notification `--help` exited 0 and displayed `CRP`, `DAY27`, `DAY30`, `OVERDUE`, and `--dry-run`.
- The DAY27 `--dry-run` exited 0 with successful processing and zero previews (no eligible DAY27 vehicles). It sent no email and updated no notification markers. Two sandboxed attempts exited 1 with a generic failure; the network-enabled run succeeded.
- The GUI smoke check opened a responsive window titled `VehicleCheck v1.2.1`.
- Preserve notification rules, F-07's accepted/deferred-risk status, SQL behavior, and runtime-only SMTP password configuration.
- Centralized notification deployment to `srv-sql` remains pending.
- v1.2.1 is **READY FOR RELEASE**. It has not been committed, tagged, pushed, or deployed.

## v1.2.0 — Published (commit `ee1a255`, tag `v1.2.0`, 2026-10-08)

### Release preparation

- Prepared VehicleCheck v1.2.0 with a single `APP_VERSION` source, matching GUI title, and a maintained one-file Windows spec that derives executable naming and version metadata from that constant.
- Built `dist/VehicleCheck-1.2.0.exe`; the owner manually launched it and confirmed the GUI opened and the application ran successfully. **VehicleCheck v1.2.0 GUI SMOKE TEST: PASS.**
- The full test suite passed: 54 tests, 0 failures, 0 errors. The PyInstaller build succeeded and Windows version metadata was verified.
- Published source state: commit `ee1a255`, tag `v1.2.0`. The current `main` and `origin/main` are synchronized at the later packaging commit `4953d72`.
- Built the separate `dist/VehicleCheck-Notifications-1.2.0.exe` from `notifications.py` (9,160,901 bytes, PyInstaller 6.22.2). It is one-file, console-enabled, uses shared version metadata, and has no embedded SMTP password. `--help` exited 0 and showed all supported options.
- The initial packaging-task `--type DAY27 --dry-run` attempt exited 1 without preview lines. The owner later reported a rerun with SQL access and successful processing, exit code 0, no email sent, and no marker update. The v1.2.1 executable received a separate successful dry-run; see its entry above.
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

The previous released source version was `1.1.0` (version commit `63c4db8`, dated 2026-09-14). VehicleCheck v1.2.0 remains published from commit `ee1a255` under tag `v1.2.0`; v1.2.1 is ready for Git publication. Central notification deployment remains pending.

## Technical debt / deferred risks

- **F-07 — ACCEPTED / DEFERRED RISK for v1.2.0:** Keep the current SMTP-send-then-marker sequence for this release and accept the rare duplicate window if the marker is not committed after SMTP acceptance. Do not mark before sending or rush a schema change before release.
- Future work: evaluate a durable notification outbox/audit mechanism with notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This is not implemented and does not imply exactly-once SMTP delivery.
