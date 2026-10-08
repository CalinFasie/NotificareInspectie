# Project status

**Status date:** 2026-10-08

**Application:** VehicleCheck

**Production database:** CARSM

**SQL Server:** `srv-sql`

**Business timezone:** Europe/Bucharest

The published v1.2.0 release remains at commit `ee1a255`, tag `v1.2.0`. Release v1.2.1 is **READY FOR RELEASE** from the current source. `main` and `origin/main` are synchronized at the later packaging commit `4953d72`. Owner-confirmed production history is identified separately from checks performed during this task.

## Current version

The previous released source version is `1.1.0`, introduced by commit `63c4db8` (2026-09-14). **VehicleCheck v1.2.0 is published** at commit `ee1a255`, tag `v1.2.0`. The current `main` and `origin/main` contain the later packaging commit `4953d72`; the v1.2.0 tag remains unchanged. Release v1.2.1 has shared `APP_VERSION = "1.2.1"` and GUI title `VehicleCheck v1.2.1`. Its builds, tests, help, DAY27 dry-run, and GUI smoke check passed; v1.2.1 is **READY FOR RELEASE**. Git publication and deployment are still pending.

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
- The v1.2.1 architecture is `VehicleCheck-1.2.1.exe` on colleague PCs, without an SMTP secret, and one centralized `VehicleCheck-Notifications-1.2.1.exe` scheduled task on `srv-sql`. The release is ready; deployment and Task Scheduler setup remain pending.
- **F-07 — ACCEPTED / DEFERRED RISK for v1.2.0 and v1.2.1:** Preserve SMTP-send-then-marker behavior and accept the rare duplicate window. The existing application lock prevents concurrent runs but not a crash/restart between SMTP acceptance and SQL marker persistence. v1.2.1 does not change this behavior.

## Findings and completed work

| Finding / change | Status | Evidence and scope |
|---|---|---|
| F-01 — notification CLI entry point and safe dry-run behavior | **FIXED** | Fixed and committed in `e30c2b7`. The notification CLI supports safe execution and dry-run behavior. A live production-data dry-run succeeded with exit code 0. |
| F-02 — Windows username / `getpass.getuser()` identity and role behavior | **ACCEPTED / DEFERRED RISK** | The owner explicitly chose to leave the production behavior unchanged because it works in production. It is not marked fixed. |
| F-03 — ODBC driver compatibility, encryption, and certificate behavior | **ACCEPTED / DEFERRED RISK** | The owner explicitly chose not to change the current production behavior at this time. It is not marked fixed. |
| F-06 — missed DAY27 scheduled run / failed SMTP retry window | **FIXED** | Implemented in `925a8b4`: day 26 no send; days 27–29 send/catch up once per current inspection cycle; day 30+ no DAY27 catch-up. The marker is checked relative to cycle start, so an older-cycle marker does not block the new cycle. SMTP failure does not write the marker and can be retried on day 28/29. The full test suite passed after the change; a live production-data DAY27 dry-run later exited 0. |
| Countdown row highlighting (separate UI enhancement) | **IMPLEMENTED / TESTED** | In `7dcc824`, the entire Treeview row text is red for displayed Countdown `<= 3`, including overdue/negative values; values `> 3` stay normal; `None`/empty stays normal. Tests passed. This is not F-06. |
| Notification `--type` filter | **IMPLEMENTED / PRODUCTION-USED** | `9068e80` supports CRP, DAY27, DAY30, and OVERDUE. Without `--type`, existing all-types behavior remains. The DAY27-only path has been used successfully. |
| Separate notification executable | **BUILT / DEPLOYMENT PENDING** | The v1.2.0 artifact is `dist/VehicleCheck-Notifications-1.2.0.exe`; its initial task run failed, and the owner later reported a successful DAY27 dry-run rerun. The v1.2.1 artifact built and its network-enabled DAY27 dry-run succeeded with exit 0 and zero previews. No deployment has occurred. |

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
| Published source version | `1.2.0`, commit `ee1a255`, tag `v1.2.0`; tag unchanged. Current `main` and `origin/main` are synchronized at `4953d72`. |
| v1.2.1 release status | Shared source is `version.py`; **READY FOR RELEASE**. Not committed, tagged, or pushed. |
| GUI release | Built and smoke-tested successfully; this task did not change its binary design. |
| v1.2.0 preparation | Version source, GUI title, maintained spec, and Windows version metadata prepared. |
| v1.2.1 tests | Full unittest suite passed: 54 tests, 0 failures, 0 errors. |
| GUI built | `dist/VehicleCheck-1.2.0.exe`, 11,842,006 bytes; GUI version metadata verified. |
| v1.2.0 notifications built | `dist/VehicleCheck-Notifications-1.2.0.exe`, 9,160,901 bytes, PyInstaller 6.22.2. ProductName/FileDescription `VehicleCheck Notifications`, FileVersion `1.2.0.0`, ProductVersion `1.2.0` verified. CLI help passed; successful later DAY27 dry-run is owner-reported. |
| v1.2.1 GUI build | `dist/VehicleCheck-1.2.1.exe`, 11,842,112 bytes; PyInstaller 6.22.2. ProductName/FileDescription `VehicleCheck`, FileVersion `1.2.1.0`, ProductVersion `1.2.1` verified. |
| v1.2.1 notification build | `dist/VehicleCheck-Notifications-1.2.1.exe`, 9,159,999 bytes; PyInstaller 6.22.2. ProductName/FileDescription `VehicleCheck Notifications`, FileVersion `1.2.1.0`, ProductVersion `1.2.1` verified. `pyodbc` and `tzdata` were included; Tkinter was excluded. |
| v1.2.1 notification CLI | `--help` exited 0 and displayed all required options. |
| v1.2.1 DAY27 dry-run | **PASS** — the network-enabled run exited 0 and processing succeeded with zero previews (no eligible DAY27 vehicles). No email or marker update occurred. Two sandboxed attempts had exited 1 with a generic failure. |
| v1.2.1 secret check | No literal SMTP password assignment found in tracked source, specs, scripts, or documentation. The build shell did not have `VEHICLECHECK_SMTP_PASSWORD` set; no password is in executable metadata. |
| v1.2.1 GUI startup smoke | **PASS** — responsive window opened with title `VehicleCheck v1.2.1`. The owner-confirmed v1.2.0 GUI smoke remains historical evidence only. |
| Source publication | v1.2.0 remains published at tag commit `ee1a255`. Current `main` and `origin/main` agree at `4953d72`. v1.2.1 has not been committed, tagged, or pushed. |
| Central notification deployment | **PENDING** — no executable was copied to `srv-sql`, and no scheduled task was created. |

## Centralized notifications

The approved model for v1.2.1 is:

```text
Colleague PCs:
    VehicleCheck-1.2.1.exe
    no SMTP secret required

srv-sql:
    VehicleCheck-Notifications-1.2.1.exe
    one scheduled task
    CARSM access
    VEHICLECHECK_SMTP_PASSWORD available only to the task identity
```

The v1.2.1 notification executable is built; deployment is pending. The v1.2.0 packaging task's initial DAY27 run failed, but the owner later reported a rerun with SQL access and successful processing, exit code 0, no email, and no marker update. The v1.2.1 network-enabled DAY27 dry-run exited 0 with successful processing and zero previews, indicating no eligible vehicles. It sent no email and updated no markers. No task has been installed on `srv-sql`.

## F-07 — ACCEPTED / DEFERRED RISK for v1.2.0 and v1.2.1

For v1.2.0 and v1.2.1, preserve the current sequence: SMTP send succeeds, notification marker `UPDATE`, SQL commit. Accept that a process termination in the small interval after SMTP acceptance but before marker persistence may lead to a duplicate on a later run. The SQL application lock prevents concurrent notification runs but does not close this crash/restart window.

Do not change to mark-before-send: that could permanently lose legitimate notifications when SMTP subsequently fails. Do not introduce a rushed schema change immediately before the release. F-07 is accepted/deferred, not fixed; v1.2.1 preserves the behavior.

Future technical work: evaluate a durable notification outbox/audit mechanism containing a notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This design is not implemented. It must not be described as providing exactly-once SMTP delivery.

## Current worktree

The v1.2.1 preparation changes `version.py` and release documentation. Existing untracked files and exports were present before editing and have been preserved. No files have been staged. Build outputs are ignored; the maintained GUI and notification specs are tracked and both derive the release version from `version.py`.

## Next steps

1. Review and stage only the v1.2.1 source and documentation paths; commit/tag/push remain separate release actions.
2. Configure and validate one scheduled task on `srv-sql` as a separate deployment step.
3. Revisit F-07 outbox/audit design and retry/recovery policy as future technical work; it remains accepted/deferred.

## Remaining uncertainties

- Whether the selected task identity, local SQL instance configuration, and ODBC installation on `srv-sql` will support the executable after deployment; no deployment inspection has been performed.
- Whether any recurring Task Scheduler job already exists on `srv-sql`; no deployment inspection was performed.
