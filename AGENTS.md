# Repository guidance

## Project

VehicleCheck is a Windows desktop application for vehicle, CRP, inspection, and email-notification management. The GUI is implemented with Tkinter/ttk and uses SQL Server through `pyodbc`. The notification runner is `notifications.py`.

The production database is CARSM on SQL Server host `srv-sql`; VehicleCheck is the application name, not the database name. The business timezone is Europe/Bucharest.

Read `docs/PROJECT_STATUS.md`, `docs/DECISIONS.md`, and `docs/OPERATIONS.md` before making changes that touch deployment, identity, SQL, or notifications.

## Scope and safety

- Keep changes narrow and preserve existing behavior unless the task explicitly asks to change it.
- Do not change notification rules (CRP, DAY27, DAY30, OVERDUE), SQL schema, database connectivity, SMTP behavior, authentication, or filtering as a side effect of a UI task.
- Do not run the live notification command, send email, or make production database changes unless the user explicitly authorizes that operation.
- Do not run destructive SQL. Preserve authentication and authorization behavior unless explicitly asked to change it.
- `--dry-run` avoids SMTP sends and marker updates, but still reads from SQL Server. It is not proof of live SMTP delivery.
- `schema.sql` is for creating a new database. Do not execute it over existing application tables. Review and use the separate migration appropriate to the requested change.
- Never put passwords, recipient data, connection strings, or other secrets into source, logs, tests, or documentation. SMTP credentials are read from `VEHICLECHECK_SMTP_PASSWORD`.
- Never print secret values or commit SMTP passwords. `VEHICLECHECK_SMTP_PASSWORD` must remain runtime configuration.
- Record owner-confirmed history as owner-confirmed, without claiming you independently repeated it. Treat scheduled-task, build, release, and deployment state as unverified until checked. Distinguish mocked tests, local dry runs, live integration checks, and deployed behavior.
- Preserve existing unrelated worktree changes and untracked artifacts. Inspect `git status --short` before editing; do not clean, reset, or stage unrelated files.
- Do not commit, push, tag, merge, or change branches unless explicitly requested.

## Data and identity

- Current code targets SQL Server database `carsm` (CARSM) and tables `dbo._CONFIG`, `dbo._VEHICLES`, and `dbo._INSPECTIONS`.
- SQL uses Windows integrated authentication (`Trusted_Connection=yes`). The application maps the current Windows username to an active `_CONFIG` user and applies application roles.
- Keep database operations parameterized and preserve transaction/commit behavior.
- Connection details and operational caveats are described in `docs/OPERATIONS.md`; do not infer that TLS encryption is verified from the current connection string.

## Notifications

- Notification markers currently live on `_VEHICLES`: `LastCrpNotificationDate`, `LastDay27NotificationDate`, and `LastOverdueNotificationDate`.
- `notification_lock()` serializes notification runs with a SQL Server application lock. It does not make SMTP and SQL atomic and does not close the crash window between SMTP acceptance and marker commit.
- SMTP failures are not marked as sent, allowing retries. Partial recipient acceptance can result in accepted recipients receiving a later retry.
- Preserve the current CRP, DAY27 catch-up, DAY30, and OVERDUE rules unless the task explicitly changes them.
- DAY27 has no notification on cycle day 26; it may send once on days 27–29 for the current inspection cycle if not already successfully sent; it has no DAY27 catch-up on day 30 or later. An SMTP failure must not mark it as sent.
- `--type` supports `CRP`, `DAY27`, `DAY30`, and `OVERDUE`. Without `--type`, preserve the existing all-types behavior. `--dry-run` reads SQL without SMTP sends or marker updates.
- F-06 is the DAY27 missed-run issue and is fixed by the days 27–29 catch-up behavior. Countdown red-row highlighting is a separate UI enhancement.
- The owner confirms DAY27 SMTP delivery and real DAY27 send were verified in production. This historical fact does not authorize an agent to send another email.
- F-01 (notification CLI entry point) is fixed. F-02 identity behavior and F-03 ODBC/encryption/certificate behavior are owner-accepted deferred risks; do not mark them fixed or change them without authorization.
- F-07 remains a recommended design change only: a transactional notification outbox/audit table has not been implemented or migrated.
- Centralized notification execution is planned. `srv-sql` is a Windows Server under consideration as the host, not a confirmed deployment.

## UI

- Preserve existing Tkinter/ttk layout, filtering, and selection behavior when making presentation changes.
- In the main vehicle list, the existing displayed Countdown value `<= 3` is shown in red across the row; missing/`None` Countdown remains normal. Keep this presentation consistent when rows are inserted or refreshed.

## Verification

- Tests use `unittest` and generally mock external SQL/SMTP services.
- Before presenting a code change as ready, run the full local suite and `git diff --check`:

  ```powershell
  .\.venv\Scripts\python.exe -B -m unittest -v
  ```

- Report exact pass/fail/error totals and any skipped live integration separately. Do not claim live SQL or SMTP validation from mocked tests.
- Run `git diff --check` after edits. Review the final diff and confirm unrelated files remain untouched.
- Stage only intended paths. Do not use `git add .` when targeted staging is safer.
- Report changed files and tests run. Distinguish unit-tested, dry-run verified, real SMTP verified, deployed, and pushed-to-GitHub states.
