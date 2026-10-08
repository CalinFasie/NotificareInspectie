# Project status

**Status date:** 2026-10-08

**Application:** VehicleCheck

**Production database:** CARSM

**SQL Server:** `srv-sql`

**Business timezone:** Europe/Bucharest

Owner-confirmed production history in this document is recorded as supplied by the project owner; it was not repeated during this documentation-only change.

## Current version

The previous released source version is `1.1.0`, introduced by commit `63c4db8` (2026-09-14). The current local release commit is `0704f87` (`Prepare VehicleCheck v1.2.0 release`) and sets the single source constant to `1.2.0`, with GUI title `VehicleCheck v1.2.0`. **v1.2.0 — READY FOR RELEASE**; it has not been pushed or tagged and is not deployed.

At the start of release preparation, local `main` and the local `origin/main` tracking ref both pointed to `fef33bd`. No fetch or GitHub check was performed. This local ref equality does not independently establish live GitHub state.

## Packaging analysis

- Both existing `.spec` files were untracked and have no Git history. Their recipes are materially the same: one-file executable, `console=False`, `main.py` entry point, and `collect_all('tzdata')` for timezone data and hidden imports.
- `VehicleCheck v1.1.0.spec` has a later filesystem timestamp and a matching `build/VehicleCheck v1.1.0` work folder, but the prior `dist/` contained no `VehicleCheck v1.1.0.exe`. The timestamp of the old `VehicleCheck.exe` does not establish which spec created it. Neither old spec can be confirmed as the latest working build.
- `VehicleCheck.spec` is selected as the single maintained, version-neutral spec because it avoids the stale v1.1.0 output name and matches the preferred name. The old `VehicleCheck v1.1.0.spec` and existing build/dist artifacts were preserved.
- The maintained spec keeps one-file/windowed mode, collects `tzdata`, and relies on Analysis/PyInstaller hooks for imports used by `main.py` and `pyodbc`. No custom icon or other application data asset was found. Windows version information is built as a standard PyInstaller `VSVersionInfo` from `APP_VERSION`, avoiding a second manually maintained version string.

## Current production state

- The application connects to SQL Server host `srv-sql` and production database CARSM (`carsm` in configuration), using application tables `dbo._CONFIG`, `dbo._VEHICLES`, and `dbo._INSPECTIONS`.
- The project owner confirms that colleague PCs already run the GUI and connect successfully to `srv-sql` / CARSM.
- A live production-data dry-run completed with exit code 0. A controlled real SMTP test message was received. Subsequently, the owner ran `notifications.py --type DAY27` and confirmed the notification emails were delivered. See the separate validation statuses below.
- Centralized scheduled execution from one controlled Windows machine/server remains planned. `srv-sql` is a Windows Server being considered as the notification host; it is not documented as a deployed notification host.
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

### DAY27 production validation

```yaml
DAY27 SMTP DELIVERY: VERIFIED
DAY27 REAL SEND: VERIFIED
```

The project owner confirms a controlled SMTP message was received and a later real `notifications.py --type DAY27` run delivered the emails. No passwords, app passwords, or secret values are recorded here. These are owner-confirmed production results, not a new send performed during this documentation task.

## Release status

| State | Status |
|---|---|
| Previous released source version | `1.1.0`. |
| Latest local source version | `1.2.0`, release commit `0704f87`; GUI title is `VehicleCheck v1.2.0`. |
| Release status | **READY FOR RELEASE**; not pushed or tagged, and not deployed. |
| v1.2.0 preparation | Version source, GUI title, maintained spec, and Windows version metadata prepared. |
| Tests | Full unittest suite passed: 54 tests, 0 failures, 0 errors. |
| Built | `dist/VehicleCheck-1.2.0.exe`, 11,842,006 bytes, PyInstaller 6.22.2. Embedded ProductName/FileDescription, FileVersion, and ProductVersion verified. |
| GUI startup smoke | **PASS** — owner manually launched `dist/VehicleCheck-1.2.0.exe`; the GUI opened and the application ran successfully. |
| Committed locally | Yes — `0704f87 Prepare VehicleCheck v1.2.0 release`. |
| Pushed to GitHub | No — the release commit has not been pushed. |
| Tagged | No — v1.2.0 has not been tagged. |
| Deployed | No — v1.2.0 has not been deployed. |

## Centralized notifications

The planned model is one controlled Windows machine/server for scheduled sends, rather than sending independently from every colleague workstation. `srv-sql` is a Windows Server and is being considered as that host. Centralized scheduling and deployment are not yet confirmed.

## F-07 — ACCEPTED / DEFERRED RISK for v1.2.0

For v1.2.0, preserve the current sequence: SMTP send succeeds, notification marker `UPDATE`, SQL commit. Accept that a process termination in the small interval after SMTP acceptance but before marker persistence may lead to a duplicate on a later run. The SQL application lock prevents concurrent notification runs but does not close this crash/restart window.

Do not change to mark-before-send: that could permanently lose legitimate notifications when SMTP subsequently fails. Do not introduce a rushed schema change immediately before the release. F-07 is accepted/deferred for v1.2.0, not fixed.

Future technical work: evaluate a durable notification outbox/audit mechanism containing a notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This design is not implemented. It must not be described as providing exactly-once SMTP delivery.

## Current worktree

Before release preparation, tracked files were clean and the repository had unrelated untracked files/artifacts: `Explorare 2.md`, two PyInstaller `.spec` files, `build/`, `dist/`, `analyze.ps1`, compatibility ZIPs, a dropdown export/patch, `codex-analysis-prompt.txt`, and `users.txt`. The old `VehicleCheck v1.1.0.spec` and prior build/dist contents remain preserved. The new EXE and isolated clean work directory are generated, ignored build outputs. Release-preparation changes are limited to version/title, `.gitignore`, the maintained spec, and release documentation.

## Next steps

1. After release approval, push the local release commit and create the v1.2.0 tag; handle deployment as a separate step.
2. Revisit F-07 outbox/audit design and retry/recovery policy as future technical work after v1.2.0.
3. Decide whether `srv-sql` or another controlled Windows host will run centralized notifications; configure and validate scheduling before deployment.

## Remaining uncertainties

- Current live GitHub state; local `origin/main` was not refreshed or independently checked.
- Which Windows Server will host the centralized scheduled task and whether any recurring task is already configured.
- Whether the previous untracked build artifacts correspond to current source. The v1.2.0 executable was built and manually smoke-tested, while the release commit remains local and the executable has not been deployed.
- Why the earlier automated GUI startup smoke did not expose the expected main-window title within its 40-second timeout; the later owner-confirmed manual launch passed.
