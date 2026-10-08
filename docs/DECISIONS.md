# Technical decisions and current constraints

This chronological log separates implemented behavior, tests, local commits, production validation, and proposals. Owner-confirmed production history is recorded without repeating live operations.

## 2026-10-08 — VehicleCheck uses CARSM

- **Date:** Current state recorded 2026-10-08; original decision date not established.
- **Decision:** The production database is CARSM on SQL Server host `srv-sql`; VehicleCheck remains the application name.
- **Context:** Source configuration targets `carsm`; schema and DB code use `dbo._CONFIG`, `dbo._VEHICLES`, and `dbo._INSPECTIONS`.
- **Reason:** Keep the product identity distinct from the production database identity and match the existing application configuration.
- **Consequences:** Use CARSM when referring to production data. `schema.sql` is for a new database and must not be run over existing tables.
- **Status:** Current; the owner confirms colleague GUI access to `srv-sql` / CARSM.

## 2026-10-08 — Retain Windows identity and application roles

- **Date:** Current state recorded 2026-10-08; original decision date not established.
- **Decision:** Leave the Windows username / `getpass.getuser()` identity and role behavior unchanged.
- **Context:** `db.py` uses `Trusted_Connection=yes`; GUI role checks use the mapped application account.
- **Reason:** The owner explicitly confirmed that this behavior works in production and chose not to change it now.
- **Consequences:** Account provisioning and role behavior remain dependent on Windows identity and `_CONFIG` contents.
- **Status:** F-02 — **ACCEPTED / DEFERRED RISK**. The production behavior remains as-is; this is not marked fixed.

## 2026-10-08 — Retain ODBC compatibility settings

- **Date:** Current state recorded 2026-10-08; original decision date not established.
- **Decision:** Leave current ODBC driver compatibility, encryption, and certificate behavior unchanged.
- **Context:** Driver selection prefers ODBC 18, then 17, then legacy `SQL Server`. The connection uses `Trusted_Connection=yes` and `TrustServerCertificate=yes`; explicit `Encrypt=yes` is commented out.
- **Reason:** The owner explicitly chose not to change the current production behavior at this time.
- **Consequences:** Do not claim encryption is verified. Review the target SQL Server and driver requirements before changing these settings.
- **Status:** F-03 — **ACCEPTED / DEFERRED RISK**. The production behavior remains as-is; this is not marked fixed.

## 2026-10-08 — Keep SMTP credentials in runtime configuration

- **Date:** Current state recorded 2026-10-08; original decision date not established.
- **Decision:** Read the SMTP password from `VEHICLECHECK_SMTP_PASSWORD` at runtime.
- **Context:** `config.py` reads this environment variable; the GUI and notification runner are separate operations.
- **Reason:** Avoid storing SMTP credentials in source control.
- **Consequences:** The Windows process account that sends notifications must receive the environment variable securely; colleagues using only the GUI should not need the SMTP password.
- **Status:** Current.

## 2026-10-08 — Add notification type selection

- **Date:** 2026-10-08 (`9068e80`).
- **Decision:** Allow the notification CLI to select CRP, DAY27, DAY30, or OVERDUE processing.
- **Context:** The CLI has a `--type` filter and a separate `--dry-run` mode.
- **Reason:** Support focused operations over the existing notification types.
- **Consequences:** The filter selects work; it does not redefine the notification business rules. Dry-run still requires SQL reads and does not validate SMTP.
- **Status:** Implemented in local committed source.

## 2026-10-07 — Fix F-01 notification CLI entry point

- **Date:** 2026-10-07 (`e30c2b7`).
- **Decision:** Fix the notification CLI entry point and support safe execution, including dry-run behavior.
- **Context:** F-01 concerned the notification CLI entry point.
- **Reason:** Make scheduled/manual notification invocation work through the intended CLI and support a non-sending preview path.
- **Consequences:** The production-data dry-run can validate reads and selection without sending email or updating notification markers.
- **Status:** F-01 — **FIXED**, committed locally. Owner confirms a production-data dry-run succeeded with exit code 0.

## 2026-10-08 — Fix F-06 DAY27 missed-run handling

- **Date:** 2026-10-08 (`925a8b4`).
- **Decision:** Permit DAY27 notification catch-up on cycle days 27, 28, and 29; do not send DAY27 on day 26 or perform DAY27 catch-up on day 30 or later. Send at most once per current inspection cycle when it succeeds.
- **Context:** Original behavior sent only when `cycle_day == 27`, so a missed scheduled run or SMTP failure could lose the reminder. `LastDay27NotificationDate` is evaluated relative to the inspection-cycle start; a marker from an older cycle does not block a new cycle.
- **Reason:** Cover scheduled runs missed on day 27 without sending a duplicate in the same cycle or extending DAY27 past its catch-up window.
- **Consequences:** A failed SMTP attempt does not write the marker and remains eligible for retry on day 28/29. Day 26 does not send; day 30+ does not catch up DAY27.
- **Status:** F-06 — **FIXED**, implemented and committed locally; full test suite passed after the change. Owner confirms a live production-data DAY27 dry-run later exited 0.

## 2026-10-08 — Highlight urgent Countdown rows

- **Date:** 2026-10-08 (`7dcc824`).
- **Decision:** Show the full main vehicle-list row text in red when the existing displayed Countdown is `<= 3`; leave missing/`None` values normal.
- **Context:** The UI uses the same Countdown value already displayed; it does not recalculate inspection dates for coloring.
- **Reason:** Make urgent rows visible while preserving the business calculation and table layout.
- **Consequences:** Countdown values above 3 keep their normal appearance; overdue/negative values are red because they are also `<= 3`; `None` and empty values remain normal. This is a separate UI enhancement and is not F-06.
- **Status:** Implemented and committed locally; tests passed.

## 2026-10-08 — DAY27 live delivery validation

- **Date:** Owner-confirmed production history recorded 2026-10-08; exact send dates not established here.
- **Decision:** Record the controlled SMTP and DAY27 production runs as verified.
- **Context:** The owner confirms a real SMTP test message was received, followed by a successful real `notifications.py --type DAY27` run with delivered emails.
- **Reason:** Distinguish production delivery evidence from mocked unit tests and a dry-run.
- **Consequences:** Do not expose or record passwords or app-password values. Do not interpret historical validation as authorization to send another message.
- **Status:** `DAY27 SMTP DELIVERY: VERIFIED`; `DAY27 REAL SEND: VERIFIED` (owner-confirmed).

## 2026-10-08 — Centralize notification sending

- **Date:** Planned state recorded 2026-10-08; original decision date not established.
- **Decision:** Run scheduled notification sending from one controlled, continuously available Windows machine/server rather than each colleague workstation.
- **Context:** Owner confirms colleague PCs use the GUI and connect successfully to `srv-sql` / CARSM. The Windows Server `srv-sql` is being considered as a notification host, but deployment is not confirmed.
- **Reason:** Centralize secret handling and scheduled operational ownership.
- **Consequences:** The designated host/account needs SQL access, SMTP runtime configuration, scheduling, monitoring, and recovery procedures.
- **Status:** Planned, not deployed.

## 2026-10-08 — Accept/defer F-07 risk for v1.2.0

- **Date:** Analysis recorded 2026-10-08.
- **Decision:** For v1.2.0, preserve SMTP-send-then-marker behavior and accept the rare duplicate risk if SMTP accepts a message but the process ends before the marker is persisted.
- **Context:** Current order is SMTP send, marker `UPDATE`, then SQL commit. The SQL application lock serializes active runs but does not close this crash/restart window.
- **Reason:** Mark-before-send could permanently lose legitimate notifications after an SMTP failure. A rushed schema change immediately before release is not warranted; the residual duplicate risk is accepted for this release.
- **Consequences:** Existing send-then-marker behavior remains. F-07 is not fixed, and a later run may send the same notification again if the marker was not committed.
- **Status:** F-07 — **ACCEPTED / DEFERRED RISK** for v1.2.0.

### Future technical work

Evaluate a durable notification outbox/audit mechanism with a notification identity, vehicle, notification type, inspection cycle, status, timestamps, and retry/recovery policy. It is not implemented. It must not be represented as guaranteeing exactly-once SMTP delivery.
