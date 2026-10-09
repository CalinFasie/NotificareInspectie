# Operations guide

This guide describes VehicleCheck v1.2.2 production operations. The notification runner is deployed on `srv-sql` and configured as a SQL Server Agent job. A controlled SMTP test, a manual Agent run, and the first automatic scheduled run have each been confirmed separately. The first automatic run is **PRODUCTION VERIFIED — 2026-10-09** from the exported SQL Server Agent Job History.

## Workstation GUI

The GUI is a Windows Tkinter application. The production SQL Server host is `srv-sql` and the database is CARSM. The owner confirms colleagues already use the GUI and connect successfully to this host/database. The current documented setup requires Python 3.10+, SQL Server access, and an installed supported ODBC driver. Install Python dependencies in the project virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The database connection uses Windows integrated authentication. The Windows username must map to an active application account in `dbo._CONFIG`; permissions are enforced by the application. Colleague workstations using only the GUI do not need the SMTP password. Notification sending is a separate operation.

The v1.2.2 GUI build is `VehicleCheck-1.2.2.exe`. Existing GUI connections from colleague PCs to SQL Server `srv-sql` and database `CARSM` are confirmed working; installation of the v1.2.2 GUI on every colleague PC has not been verified. Colleague PCs do not receive `VEHICLECHECK_SMTP_PASSWORD`.

The vehicle selector supports Active, Inactive, and Toate. The main list colors the entire row text red when its displayed Countdown value is 3 or lower; missing Countdown values remain in the normal style.

## Database

The source targets SQL Server database `carsm` (CARSM) with tables `dbo._CONFIG`, `dbo._VEHICLES`, and `dbo._INSPECTIONS`.

- `schema.sql` is intended to create a new database schema. Do not execute it over existing tables.
- `notification_columns.sql` is a separate script mentioned by the README for notification marker columns; inspect the target schema and the migration file before applying it.
- Database credentials are not stored in the connection string; Windows integrated authentication is used.
- Source currently prefers ODBC 18, then 17, then the legacy `SQL Server` driver. The connection string has `TrustServerCertificate=yes`; explicit `Encrypt=yes` is commented out. Do not describe transport encryption as verified without checking the deployed SQL Server/client configuration.

## Notifications

The notification runner uses Europe/Bucharest application dates. Its current business rules include CRP alerts beginning on cycle day 6 when CRP is missing, DAY27 inspection alerts, DAY30 alerts, and OVERDUE alerts after day 30. See `notifications.py` for authoritative behavior.

Preview a selected notification type without sending email or updating markers:

```powershell
.\.venv\Scripts\python.exe notifications.py --type DAY27 --dry-run
```

`--dry-run` still requires a working SQL connection to read the data and is not evidence of SMTP delivery. The no-argument notification command and any notification-type command without `--dry-run` may send real email and update SQL markers. Use them only from the approved operating host/account and within the approved schedule/runbook.

`--type` accepts `CRP`, `DAY27`, `DAY30`, or `OVERDUE`. The DAY27-only path has been used successfully. Omitting `--type` retains the existing all-types behavior.

The deployed production runner is `C:\VehicleCheck\VehicleCheck-Notifications-1.2.2.exe`. SQL Server Agent invokes it without arguments, so each run processes all applicable notification types. `--dry-run` still reads production vehicle data but does not send email or update notification markers.

### Controlled SMTP connectivity test

When an operator needs to verify the configured SMTP connection, run the dedicated test mode with an approved test inbox:

```powershell
C:\VehicleCheck\VehicleCheck-Notifications-1.2.2.exe --smtp-test-recipient "your-test-inbox@example.com"
```

This mode sends exactly one harmless email with subject `[VehicleCheck TEST] SMTP verification` and a body identifying it as a connectivity test. It uses the existing SMTP configuration and `VEHICLECHECK_SMTP_PASSWORD` available to the process identity. It does not run notification processing, read vehicle data, acquire the SQL notification lock, update SQL, or change notification markers. The option requires a non-empty recipient and cannot be combined with `--type` or `--dry-run`. SMTP/configuration failure returns exit code 1; success returns 0. This command sends a real email when an operator runs it, so use only an approved test inbox.

### Owner-confirmed production validation

- A production-data dry-run completed with exit code 0.
- The DAY27-only production-data dry-run after the catch-up change also completed with exit code 0.
- A controlled real SMTP test message was successfully received.
- A subsequent real `notifications.py --type DAY27` run completed and its emails were confirmed delivered.
- The owner reports `DAY27 SMTP DELIVERY: VERIFIED` and `DAY27 REAL SEND: VERIFIED`.

These are historical owner-confirmed results and were not repeated during this task. Never include passwords or app-password values in operational notes.

The approved v1.2.2 architecture is centralized:

```text
Colleague PCs:
    VehicleCheck-1.2.2.exe
    no SMTP secret required

srv-sql:
    VehicleCheck-Notifications-1.2.2.exe
    one scheduled task
    CARSM access
    VEHICLECHECK_SMTP_PASSWORD available only to the task identity
```

The notification runner is deployed at the path below. The v1.2.2 GUI build is confirmed, but its installation across colleague PCs has not been verified.

### Production SQL Server Agent configuration

The notification runner is installed on `srv-sql` at:

```text
C:\VehicleCheck\VehicleCheck-Notifications-1.2.2.exe
```

It runs centrally so colleagues use the GUI without SMTP credentials and the notification task has the server's CARSM access and SMTP runtime configuration. The SQL Server Agent service runs as `NT Service\SQLSERVERAGENT`. SMTP uses `smtp.gmail.com:587` with account `itimpcalin@gmail.com`; the password value is not stored in this guide. It is read only from the Windows System environment variable `VEHICLECHECK_SMTP_PASSWORD`. The owner confirms Agent could read the System variable after the SQL Server Agent service was restarted.

The configured SQL Server Agent job is:

| Setting | Value |
|---|---|
| Server | `srv-sql` |
| Job | `VehicleCheck Notifications` (enabled) |
| Step | `VehicleCheck Notifications` |
| Subsystem | `CmdExec` |
| Command | `C:\VehicleCheck\VehicleCheck-Notifications-1.2.2.exe` |
| On success / failure | Quit job reporting success / Quit job reporting failure |
| Schedule | Daily at 08:00, enabled |

Do not quote the entire CmdExec command. It has no command-line arguments, which preserves all-types processing. The Windows timezone is `GTB Standard Time`, corresponding to `Europe/Bucharest`; on 2026-10-08 its offset was UTC+03:00. The schedule was checked in SSMS. At that check, the next run was 2026-10-09 08:00 local (`next_run_date = 20261009`, `next_run_time = 80000`). These values confirm schedule configuration only, not that SQL Server Agent has automatically executed the job.

For an upgrade, a new build does not change the deployed executable or the Job Step. Deploy the new binary and explicitly update the CmdExec path to the intended version, then verify deployment, SMTP connectivity, and a normal notification run as separate checks. Do not schedule separate jobs per notification type; the no-argument job processes all applicable types and the SQL application lock is shared by notification processes.

### First automatic scheduled run — PRODUCTION VERIFIED (2026-10-09)

The owner-provided SQL Server Agent Job History export from `srv-sql` confirms the first automatic execution:

- Job: `VehicleCheck Notifications`; date/time: 2026-10-09 08:00:01, Europe/Bucharest local time.
- Trigger: `Schedule 674 (VehicleCheck Notifications)`. SQL Server Agent explicitly reported: `The job succeeded. The Job was invoked by Schedule 674 (VehicleCheck Notifications).` This confirms a schedule-triggered, automatic run rather than a manual start.
- Application mode: normal; execution identity: `NT Service\SQLSERVERAGENT`.
- CmdExec step: Success; overall job: Success; duration: `00:00:17`; retries: `0`.
- Processing message: `Procesarea notificărilor s-a încheiat cu succes.`

This confirms that notification processing completed successfully. The job history does not establish that each individual email was delivered.

Keep the following read-only SSMS procedure for checking automatic runs for future versions or schedules. Adjust the date cutoff in the queries to the execution being checked:

1. In SSMS, open **SQL Server Agent → Jobs → VehicleCheck Notifications → View History**.
2. Find the execution at the intended scheduled time. Confirm that the `VehicleCheck Notifications` step and the overall job both succeeded. The history messages should report `The step succeeded.` and `The job succeeded.`
3. Run the following read-only query in SSMS to inspect the request source in `msdb.dbo.sysjobactivity` and the linked job-history row. `run_requested_source = 1` means the Scheduler; `4` means a user/manual request. The other documented values are `2` (Alerter), `3` (Boot), and `6` (On Idle Schedule).

```sql
USE msdb;
GO

SELECT
    j.name AS job_name,
    a.session_id,
    a.run_requested_date,
    a.run_requested_source,
    a.run_requested_source_id,
    a.start_execution_date,
    a.stop_execution_date,
    a.job_history_id,
    h.step_id AS linked_history_step_id,
    h.step_name AS linked_history_step_name,
    h.run_status AS linked_history_run_status,
    h.message AS linked_history_message
FROM dbo.sysjobactivity AS a
JOIN dbo.sysjobs AS j
    ON j.job_id = a.job_id
LEFT JOIN dbo.sysjobhistory AS h
    ON h.instance_id = a.job_history_id
WHERE j.name = N'VehicleCheck Notifications'
  AND a.run_requested_date >= CONVERT(datetime, '2026-10-09T08:00:00', 126) -- Change this cutoff for a future run.
ORDER BY a.run_requested_date DESC;
```

4. If the activity row or linked history row is unavailable, inspect job and step outcomes directly with this read-only history query. It resolves the configured step by joining `msdb.dbo.sysjobsteps` and selecting the step named `VehicleCheck Notifications`; it does not assume a numeric step ID. `step_id = 0` in `sysjobhistory` is the overall job outcome. `run_status = 1` means succeeded.

```sql
USE msdb;
GO

SELECT TOP (20)
    j.name AS job_name,
    h.instance_id,
    h.step_id,
    h.step_name,
    js.step_id AS configured_step_id,
    js.step_name AS configured_step_name,
    js.subsystem,
    h.run_date,
    h.run_time,
    h.run_status,
    h.message
FROM dbo.sysjobhistory AS h
JOIN dbo.sysjobs AS j
    ON j.job_id = h.job_id
LEFT JOIN dbo.sysjobsteps AS js
    ON js.job_id = h.job_id
   AND js.step_id = h.step_id
WHERE j.name = N'VehicleCheck Notifications'
  AND h.run_date >= 20261009 -- Change this cutoff for a future run.
  AND (h.step_id = 0 OR js.step_name = N'VehicleCheck Notifications')
ORDER BY h.instance_id DESC;
```

`sysjobhistory` records job/step timestamps and outcomes but not whether a run was requested by the schedule or by a user. Use `sysjobactivity.run_requested_source` for that distinction when its row is available and corresponds to the matching history entry. Activity metadata is session-scoped and may reflect a later run of the same job in that session; history retention or missing activity metadata may also prevent source attribution. A successful history row alone does not prove automatic scheduling. If source attribution is absent, ambiguous, or reports `4` (User), leave automatic execution unverified.

For a future scheduled execution, mark it **production verified** only after the matching run is attributed to its schedule, the CmdExec step and overall job both report success, and the records refer to that same execution. A successful manual run, a configured next-run time, or an SMTP test does not establish automatic execution. The 2026-10-09 execution is verified by the owner-provided Job History export and its explicit Schedule 674 invocation message above.

The owner confirms the following separate v1.2.2 production validations: the SQL Server Agent service could read `VEHICLECHECK_SMTP_PASSWORD` after restart; the controlled SMTP test email was received; the first normal production run started manually in SQL Server Agent and reported successful notification processing, step success, and job success; and the first automatic scheduled run on 2026-10-09 is verified above. The automatic run confirms processing success, not delivery of every individual email. A v1.2.1 DAY27 dry-run through SQL Server Agent exited 0. These are owner-provided results and were not repeated for this documentation task.

Metadata references: [sysjobactivity](https://learn.microsoft.com/en-us/sql/relational-databases/system-tables/dbo-sysjobactivity-transact-sql) documents the request-source values and history link; [sysjobhistory](https://learn.microsoft.com/en-us/sql/relational-databases/system-tables/dbo-sysjobhistory-transact-sql) documents step/job outcomes and timestamps.

The SQL application lock prevents concurrent notification processes; it does not close the SMTP-accepted/SQL-marker-commit crash window. SMTP acceptance followed by a crash before marker commit can cause a duplicate on a later run. F-07 outbox work remains proposed and unimplemented.

The v1.2.0 packaging validation recorded a `--help` exit code of 0. Its initial DAY27 dry-run attempt exited 1; the owner later reported a successful rerun with SQL access, processing success, exit code 0, no email, and no marker update. The v1.2.1 executable's own `--help` and DAY27 dry-run results are recorded with its release build below.

On notification errors, inspect stderr and the exit code before deciding whether to rerun. SMTP recipient refusal is reported and the notification is not marked as sent; accepted recipients in a partial refusal may receive the notification again after retry. Do not assume that re-running is harmless.

## Secrets and configuration

- Keep SMTP credentials out of source control and configure `VEHICLECHECK_SMTP_PASSWORD` for the process account that runs notifications.
- Review `config.py` for environment-specific SQL Server, database, and SMTP host settings without copying credentials into logs or docs.
- The GUI uses SQL Server integrated authentication; notification sending is a separate action and additionally requires SMTP configuration.

## Tests and verification

Run the local unit suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v
```

Tests mock external SQL/SMTP services. The full test suite passed after the F-06 DAY27 catch-up change. Passing unit tests alone do not prove live database connectivity, SMTP acceptance, mailbox delivery, Task Scheduler configuration, or packaging correctness; owner-confirmed production checks are separately listed above.

## Packaging and releases

`VehicleCheck.spec` remains the one-file, windowed GUI build from `main.py`; its design is unchanged. The maintained `VehicleCheck-Notifications.spec` is a separate one-file console build from `notifications.py`, shares `APP_VERSION` from `version.py`, collects `tzdata`, and uses PyInstaller's normal `pyodbc` analysis. It excludes Tkinter and does not require `main.py` or GUI resources. PyInstaller 6.22.2 is installed in the project virtual environment; it is not listed in `requirements.txt`.

VehicleCheck v1.2.0 remains published at commit `ee1a255`, tag `v1.2.0`. VehicleCheck v1.2.2 is committed and pushed to `main` at `9305b88`, tag `v1.2.2`; local `main` and `origin/main` are synchronized there. The v1.2.2 GUI build is `VehicleCheck-1.2.2.exe`; installation on all colleague PCs has not been verified. The notification EXE was built at `dist/VehicleCheck-Notifications-1.2.2.exe` (9,159,730 bytes) and deployed at `C:\VehicleCheck\VehicleCheck-Notifications-1.2.2.exe`. Its version metadata and CLI `--help` were verified. SMTP testing, the normal manual run, and the first automatic scheduled run are separate owner-confirmed validations; the scheduled run on 2026-10-09 completed processing successfully, without proving delivery of every individual email.

v1.2.1 is published at commit `32ce2fb`, tag `v1.2.1`; its GUI and notification builds, tests, notification help, DAY27 dry-run, and GUI smoke check passed before publication. The v1.2.2 local builds used PyInstaller 6.22.2: `VehicleCheck-1.2.2.exe` (11,841,577 bytes) and `VehicleCheck-Notifications-1.2.2.exe` (9,159,730 bytes). The full suite passed (58 tests, 0 failures, 0 errors), and notification `--help` exited 0. The notification runner is now deployed on `srv-sql`; SQL Server Agent configuration and the successful manual production run are owner-confirmed. The first automatic scheduled execution is **PRODUCTION VERIFIED — 2026-10-09** as recorded above.
