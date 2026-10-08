# Project status

**Status date:** 2026-10-08

**Application:** VehicleCheck

**Production database:** CARSM

**SQL Server:** `srv-sql`

**Business timezone:** Europe/Bucharest

Owner-confirmed production history in this document is recorded as supplied by the project owner; it was not repeated during this documentation-only change.

## Current version

The source version in `version.py` is `1.1.0`, introduced by commit `63c4db8` (2026-09-14). The next planned release is v1.2.0, but the repository does not show a v1.2.0 version bump or confirmed release.

At inspection, local `main` was six commits ahead of the local `origin/main` tracking reference and zero commits behind it. No fetch or GitHub check was performed. Do not infer that local commits have been pushed from this tracking-reference count.

The six local commits after that tracking ref are `e30c2b7`, `34ceb48`, `eded1fe`, `9068e80`, `925a8b4`, and `7dcc824` (2026-10-07 to 2026-10-08). They are committed locally; their GitHub status is unknown.

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
| Current source/application version | `1.1.0` in `version.py`. |
| Next planned release | v1.2.0. |
| v1.2.0 versioned/prepared | No v1.2.0 version bump or release preparation is present in the inspected repository. |
| Built | Local untracked PyInstaller specs and build/dist artifacts exist, but are not verified as a v1.2.0 build or as matching current source. |
| Committed locally | Six commits are ahead of the local tracking ref. |
| Pushed to GitHub | Unknown; no fetch or GitHub check was performed. |
| Tagged | No Git tags were present at inspection. |
| Deployed | No v1.2.0 deployment is established. Owner-confirmed GUI and DAY27 production use are described above. |

## Centralized notifications

The planned model is one controlled Windows machine/server for scheduled sends, rather than sending independently from every colleague workstation. `srv-sql` is a Windows Server and is being considered as that host. Centralized scheduling and deployment are not yet confirmed.

## F-07 — ACCEPTED / DEFERRED RISK for v1.2.0

For v1.2.0, preserve the current sequence: SMTP send succeeds, notification marker `UPDATE`, SQL commit. Accept that a process termination in the small interval after SMTP acceptance but before marker persistence may lead to a duplicate on a later run. The SQL application lock prevents concurrent notification runs but does not close this crash/restart window.

Do not change to mark-before-send: that could permanently lose legitimate notifications when SMTP subsequently fails. Do not introduce a rushed schema change immediately before the release. F-07 is accepted/deferred for v1.2.0, not fixed.

Future technical work: evaluate a durable notification outbox/audit mechanism containing a notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. This design is not implemented. It must not be described as providing exactly-once SMTP delivery.

## Current worktree

Before the documentation task, tracked files were clean. Existing unrelated untracked files/artifacts were preserved: `Explorare 2.md`, two PyInstaller `.spec` files, `build/`, `dist/`, `analyze.ps1`, compatibility ZIPs, a dropdown export/patch, `codex-analysis-prompt.txt`, and `users.txt`. Current documentation work is limited to documentation files and the README documentation links.

## Next steps

1. Revisit F-07 outbox/audit design and retry/recovery policy as future technical work after v1.2.0.
2. Decide whether `srv-sql` or another controlled Windows host will run centralized notifications; configure and validate scheduling before deployment.
3. Prepare and version the planned v1.2.0 release, then track build, commit, push, tag, and deployment separately.
4. Preserve the owner-approved F-02/F-03 behavior unless a future production decision explicitly changes it.

## Remaining uncertainties

- Whether the six local commits have been pushed to GitHub; local `origin/main` may be stale.
- Which Windows Server will host the centralized scheduled task and whether any recurring task is already configured.
- Whether local untracked build artifacts correspond to current source; no v1.2.0 build or deployment has been verified.
