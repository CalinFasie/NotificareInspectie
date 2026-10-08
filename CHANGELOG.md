# Changelog

This changelog records published source releases and verified local build artifacts. Release candidates are not published until separate Git release steps are completed.

## v1.2.2 — Patch release candidate

This patch adds a controlled SMTP connectivity test to the centralized notification CLI. It is prepared from the published v1.2.1 source state at commit `32ce2fb` (tag `v1.2.1`). The existing `v1.2.0` and `v1.2.1` tags are unchanged.

### SMTP test mode

- Added `--smtp-test-recipient EMAIL`. When used alone, it calls the existing `send_email()` once with the requested recipient and a fixed test subject/body, then exits without running notification processing or accessing SQL.
- The option rejects missing or whitespace-only recipients and is incompatible with `--type` and `--dry-run`. Existing notification CLI behavior is unchanged when the option is omitted.
- SMTP/configuration failures return exit code 1; logs include the exception class but omit exception details to prevent credential disclosure. SMTP passwords remain runtime configuration in `VEHICLECHECK_SMTP_PASSWORD`.
- The SMTP test command is documented for controlled operator use. It was not invoked and no email was sent during this task.

### Packaging and verification

- Set the shared `APP_VERSION` to `1.2.2`. Both maintained specs derive executable names and Windows version metadata from it. Build targets are `VehicleCheck-1.2.2.exe` and `VehicleCheck-Notifications-1.2.2.exe`.
- The full test suite passed: 58 tests, 0 failures, 0 errors. `git diff --check` passed.
- Both specs built with `--clean` using PyInstaller 6.22.2. GUI size: 11,841,577 bytes. Notification size: 9,159,730 bytes. Product names, descriptions, and version metadata were verified.
- Notification `--help` exited 0 and displayed `--type`, all four notification types, `--dry-run`, and `--smtp-test-recipient`.
- Centralized notification deployment to `srv-sql` remains pending.

## v1.2.1 — Published (commit `32ce2fb`, tag `v1.2.1`, 2026-10-08)

- The published v1.2.1 source is at commit `32ce2fb`; local `main` and `origin/main` are synchronized there. Both v1.2.0 and v1.2.1 tags remain unchanged.
- The v1.2.1 GUI and notification executables were built and validated before publication. The GUI smoke check opened a responsive window; notification `--help` passed, and its DAY27 dry-run exited 0 with successful processing and zero previews. The owner reported the separate v1.2.0 DAY27 rerun succeeded with SQL access, sent no email, and updated no marker.
- Centralized notification deployment to `srv-sql` remains pending.

## v1.2.0 — Published (commit `ee1a255`, tag `v1.2.0`, 2026-10-08)

### Release preparation

- Prepared VehicleCheck v1.2.0 with a single `APP_VERSION` source, matching GUI title, and a maintained one-file Windows spec that derives executable naming and version metadata from that constant.
- Built `dist/VehicleCheck-1.2.0.exe`; the owner manually launched it and confirmed the GUI opened and the application ran successfully. **VehicleCheck v1.2.0 GUI SMOKE TEST: PASS.**
- The full test suite passed: 54 tests, 0 failures, 0 errors. The PyInstaller build succeeded and Windows version metadata was verified.
- Published source state: commit `ee1a255`, tag `v1.2.0`. `main` and `origin/main` were subsequently synchronized and now point to the published v1.2.1 commit `32ce2fb`.
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

The previous released source version was `1.1.0` (version commit `63c4db8`, dated 2026-09-14). VehicleCheck v1.2.0 remains published from commit `ee1a255` under tag `v1.2.0`, and v1.2.1 is published from commit `32ce2fb` under tag `v1.2.1`. v1.2.2 is a patch release candidate. Central notification deployment remains pending.

## Technical debt / deferred risks

- **F-07 — ACCEPTED / DEFERRED RISK for v1.2.0:** Keep the current SMTP-send-then-marker sequence for this release and accept the rare duplicate window if the marker is not committed after SMTP acceptance. Do not mark before sending or rush a schema change before release.
- Future work: evaluate a durable notification outbox/audit mechanism with notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This is not implemented and does not imply exactly-once SMTP delivery.
