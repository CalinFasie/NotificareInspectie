# Project status

**Status date:** 2026-10-08

**Application:** VehicleCheck

**Production database:** CARSM

**SQL Server:** `srv-sql`

**Business timezone:** Europe/Bucharest

The published v1.2.0 source release is commit `ee1a255`, tagged `v1.2.0`, with `main` synchronized to `origin/main`. Owner-confirmed production history is identified separately from checks performed during this task.

## Current version

The previous released source version is `1.1.0`, introduced by commit `63c4db8` (2026-09-14). **VehicleCheck v1.2.0 is published** at commit `ee1a255`, tag `v1.2.0`; `main`, `origin/main`, and the local tag resolve to that commit. The shared `APP_VERSION` is `1.2.0`, and the GUI title is `VehicleCheck v1.2.0`. The GUI executable was built and smoke-tested successfully. This does not establish workstation rollout status.

## Packaging analysis

- `VehicleCheck.spec` remains the GUI build specification: one-file, `console=False`, `main.py` entry point, `collect_all('tzdata')`, and version metadata from `version.py`.
- `VehicleCheck-Notifications.spec` is the separate notification build specification: one-file, `console=True`, `notifications.py` entry point, shared version metadata, and `collect_all('tzdata')`. PyInstaller's normal analysis includes `pyodbc`; Tkinter is excluded and the dependency report contains no GUI modules.
- `VehicleCheck v1.1.0.spec` has a later filesystem timestamp and a matching `build/VehicleCheck v1.1.0` work folder, but the prior `dist/` contained no `VehicleCheck v1.1.0.exe`. The timestamp of the old `VehicleCheck.exe` does not establish which spec created it. Neither old spec can be confirmed as the latest working build.
- The old `VehicleCheck v1.1.0.spec` and existing GUI build/dist artifacts are preserved. The notification build does not use `main.py` or GUI resources, and it does not embed SMTP credentials.
- Both maintained specs derive Windows version information from the same `APP_VERSION` in `version.py`; the notification executable identifies itself as `VehicleCheck Notifications`.

## Current production state

- The application connects to SQL Server host `srv-sql` and production database CARSM (`carsm` in configuration), using application tables `dbo._CONFIG`, `dbo._VEHICLES`, and `dbo._INSPECTIONS`.
- The project owner confirms that colleague PCs already run the GUI and connect successfully to `srv-sql` / CARSM.
- A live production-data dry-run completed with exit code 0. A controlled real SMTP test message was received. Subsequently, the owner ran `notifications.py --type DAY27` and confirmed the notification emails were delivered. See the separate validation statuses below.
- The approved architecture is `VehicleCheck-1.2.0.exe` on colleague PCs, without an SMTP secret, and one centralized `VehicleCheck-Notifications-1.2.0.exe` scheduled task on `srv-sql`. The notification executable is built; deployment and Task Scheduler setup remain pending.
- **F-07 — ACCEPTED / DEFERRED RISK for v1.2.0:** Preserve SMTP-send-then-marker behavior and accept the rare duplicate window. The existing application lock prevents concurrent runs but not a crash/restart between SMTP acceptance and SQL marker persistence.

## Findings and completed work

| Finding / change | Status | Evidence and scope |
|---|---|---|
| F-01 — notification CLI entry point and safe dry-run behavior | **FIXED** | Fixed and committed in `e30c2b7`. The notification CLI supports safe execution and dry-run behavior. A live production-data dry-run succeeded with exit code 0. |
| F-02 — Windows username / `getpass.getuser()` identity and role behavior | **ACCEPTED / DEFERRED RISK** | The owner explicitly chose to leave the production behavior unchanged because it works in production. It is not marked fixed. |
| F-03 — ODBC driver compatibility, encryption, and certificate behavior | **ACCEPTED / DEFERRED RISK** | The owner explicitly chose not to change the current production behavior at this time. It is not marked fixed. |
| F-06 — missed DAY27 scheduled run / failed SMTP retry window | **FIXED** | Implemented in `925a8b4`: day 26 no send; days 27–29 send/catch up once per current inspection cycle; day 30+ no DAY27 catch-up. The marker is checked relative to cycle start, so an older-cycle marker does not block the new cycle. SMTP failure does not write the marker and can be retried on day 28/29. The full test suite passed after the change; a live production-data DAY27 dry-run later exited 0. |
| Countdown row highlighting (separate UI enhancement) | **IMPLEMENTED / TESTED** | In `7dcc824`, the entire Treeview row text is red for displayed Countdown `<= 3`, including overdue/negative values; values `> 3` stay normal; `None`/empty stays normal. Tests passed. This is not F-06. |
| Notification `--type` filter | **IMPLEMENTED / PRODUCTION-USED** | `9068e80` supports CRP, DAY27, DAY30, and OVERDUE. Without `--type`, existing all-types behavior remains. The DAY27-only path has been used successfully. |
| Separate notification executable | **BUILT / DEPLOYMENT PENDING** | `dist/VehicleCheck-Notifications-1.2.0.exe`; one-file console build from `notifications.py`. `--help` exited 0. The requested DAY27 dry-run exited 1 with no previews, so SQL-read validation did not pass. No email or marker update was attempted. |

### DAY27 production validation

```yaml
DAY27 SMTP DELIVERY: VERIFIED
DAY27 REAL SEND: VERIFIED
```

The project owner confirms a controlled SMTP message was received and a later real `notifications.py --type DAY27` run delivered the emails. No passwords, app passwords, or secret values are recorded here. These are historical owner-confirmed results and were not repeated during this task.

## Release status

| State | Status |
|---|---|
| Previous released source version | `1.1.0`. |
| Published source version | `1.2.0`, commit `ee1a255`, tag `v1.2.0`; `main` synchronized with `origin/main`. |
| GUI release | Built and smoke-tested successfully; this task did not change its binary design. |
| v1.2.0 preparation | Version source, GUI title, maintained spec, and Windows version metadata prepared. |
| Tests | Current full unittest suite passed: 54 tests, 0 failures, 0 errors. |
| GUI built | `dist/VehicleCheck-1.2.0.exe`, 11,842,006 bytes; GUI version metadata verified. |
| Notifications built | `dist/VehicleCheck-Notifications-1.2.0.exe`, 9,160,901 bytes, PyInstaller 6.22.2. ProductName/FileDescription `VehicleCheck Notifications`, FileVersion `1.2.0.0`, ProductVersion `1.2.0` verified. CLI help passed. DAY27 dry-run returned 1 with no preview rows. |
| GUI startup smoke | **PASS** — owner manually launched `dist/VehicleCheck-1.2.0.exe`; the GUI opened and the application ran successfully. |
| Source publication | Published on `origin/main` at `ee1a255`, tag `v1.2.0`; local refs agree. |
| Central notification deployment | **PENDING** — no executable was copied to `srv-sql`, and no scheduled task was created. |

## Centralized notifications

The approved model is:

```text
Colleague PCs:
    VehicleCheck-1.2.0.exe
    no SMTP secret required

srv-sql:
    VehicleCheck-Notifications-1.2.0.exe
    one scheduled task
    CARSM access
    VEHICLECHECK_SMTP_PASSWORD available only to the task identity
```

The notification executable is **built / deployment pending**. The DAY27 dry-run returned exit code 1 without previews, so SQL-read validation remains incomplete. No task has been installed on `srv-sql`.

## F-07 — ACCEPTED / DEFERRED RISK for v1.2.0

For v1.2.0, preserve the current sequence: SMTP send succeeds, notification marker `UPDATE`, SQL commit. Accept that a process termination in the small interval after SMTP acceptance but before marker persistence may lead to a duplicate on a later run. The SQL application lock prevents concurrent notification runs but does not close this crash/restart window.

Do not change to mark-before-send: that could permanently lose legitimate notifications when SMTP subsequently fails. Do not introduce a rushed schema change immediately before the release. F-07 is accepted/deferred for v1.2.0, not fixed.

Future technical work: evaluate a durable notification outbox/audit mechanism containing a notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This design is not implemented. It must not be described as providing exactly-once SMTP delivery.

## Current worktree

At the start of the notification packaging task, tracked files were clean and the repository had unrelated untracked files/artifacts: `Explorare 2.md`, `VehicleCheck v1.1.0.spec`, `analyze.ps1`, compatibility ZIPs, a dropdown export/patch, `codex-analysis-prompt.txt`, and `users.txt`. They were preserved. `VehicleCheck-Notifications.spec` is new and untracked; the generated notification EXE and PyInstaller work folder are ignored build outputs. The existing GUI spec and GUI binary were not changed.

## Next steps

1. Diagnose the failed DAY27 dry-run using the approved task identity and host connectivity before considering deployment; do not retry sends blindly.
2. Configure and validate the single scheduled task on `srv-sql` as a separate deployment step.
3. Revisit F-07 outbox/audit design and retry/recovery policy as future technical work; it remains deferred for v1.2.0.

## Remaining uncertainties

- Whether the selected task identity, local SQL instance configuration, and ODBC installation on `srv-sql` will support the executable; the DAY27 dry-run returned exit code 1 without preview output.
- Whether any recurring Task Scheduler job already exists on `srv-sql`; no deployment inspection was performed.
- Why the earlier automated GUI startup smoke did not expose the expected main-window title within its 40-second timeout; the later owner-confirmed manual launch passed.
