# Operations guide

This guide describes current repository behavior, published v1.2.0 and v1.2.1 releases, the v1.2.2 patch candidate, and owner-confirmed production checks. Centralized notification deployment and Task Scheduler setup on `srv-sql` are still pending.

## Workstation GUI

The GUI is a Windows Tkinter application. The production SQL Server host is `srv-sql` and the database is CARSM. The owner confirms colleagues already use the GUI and connect successfully to this host/database. The current documented setup requires Python 3.10+, SQL Server access, and an installed supported ODBC driver. Install Python dependencies in the project virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The database connection uses Windows integrated authentication. The Windows username must map to an active application account in `dbo._CONFIG`; permissions are enforced by the application. Colleague workstations using only the GUI do not need the SMTP password. Notification sending is a separate operation.

The published workstation artifacts are `VehicleCheck-1.2.0.exe` and `VehicleCheck-1.2.1.exe`. The v1.2.2 GUI build target is `VehicleCheck-1.2.2.exe`. Colleague PCs run the GUI and do not receive `VEHICLECHECK_SMTP_PASSWORD`.

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

### Controlled SMTP connectivity test

When an operator needs to verify the configured SMTP connection, run the dedicated test mode with a controlled test inbox:

```powershell
.\dist\VehicleCheck-Notifications-1.2.2.exe --smtp-test-recipient "your-test-inbox@example.com"
```

This mode sends exactly one harmless email with subject `[VehicleCheck TEST] SMTP verification` and a body identifying it as a connectivity test. It uses the existing SMTP configuration and `VEHICLECHECK_SMTP_PASSWORD` available to the process identity. It does not run notification processing, read vehicle data, acquire the SQL notification lock, update SQL, or change notification markers. The option requires a non-empty recipient and cannot be combined with `--type` or `--dry-run`. SMTP/configuration failure returns exit code 1; success returns 0. This command sends a real email when an operator runs it, so use only an approved test inbox. It was not run during the v1.2.2 build task.

### Owner-confirmed production validation

- A production-data dry-run completed with exit code 0.
- The DAY27-only production-data dry-run after the catch-up change also completed with exit code 0.
- A controlled real SMTP test message was successfully received.
- A subsequent real `notifications.py --type DAY27` run completed and its emails were confirmed delivered.
- The owner reports `DAY27 SMTP DELIVERY: VERIFIED` and `DAY27 REAL SEND: VERIFIED`.

These are historical owner-confirmed results and were not repeated during this task. Never include passwords or app-password values in operational notes.

The approved intended architecture for v1.2.2 is centralized:

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

The v1.2.2 notification executable is intended for centralized execution; deployment is pending. Do not schedule separate tasks per notification type; the normal no-argument command processes all types and the SQL application lock is shared by notification processes. The intended schedule remains daily at 08:00 Europe/Bucharest. Task Scheduler uses the server's local time, so confirm its timezone before setup. The task account needs SQL access and the `VEHICLECHECK_SMTP_PASSWORD` environment variable in its process environment.

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

VehicleCheck v1.2.0 remains published at commit `ee1a255`, tag `v1.2.0`. `main` and `origin/main` are currently synchronized at the published v1.2.1 commit `32ce2fb`. The GUI release was built and smoke-tested successfully. The full v1.2.0 packaging suite passed: 54 tests, 0 failures, 0 errors. The notification EXE was built at `dist/VehicleCheck-Notifications-1.2.0.exe` (9,160,901 bytes); its version metadata and CLI `--help` were verified. The initial DAY27 dry-run failed, followed by an owner-reported successful rerun. No deployment was performed.

v1.2.1 is published at commit `32ce2fb`, tag `v1.2.1`; `main` and `origin/main` are synchronized there. Its GUI and notification builds, test suite, notification help, DAY27 dry-run, and GUI smoke check passed before publication. For v1.2.2, both maintained specs built with PyInstaller 6.22.2: `dist/VehicleCheck-1.2.2.exe` (11,841,577 bytes) and `dist/VehicleCheck-Notifications-1.2.2.exe` (9,159,730 bytes). Their version metadata was verified. The full suite passed (58 tests, 0 failures, 0 errors), and notification `--help` exited 0 with all supported options. The SMTP test mode was not invoked and no email was sent. No executable has been copied to `srv-sql`, and no scheduled task has been created.
