import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import db
import main
import notifications


class RuntimeTests(unittest.TestCase):
    def test_connection_uses_best_available_driver(self):
        driver18 = "ODBC Driver 18 for SQL Server"
        driver17 = "ODBC Driver 17 for SQL Server"
        cases = [
            ([driver18], driver18),
            ([driver17], driver17),
            (["ODBC Driver 13 for SQL Server"], "ODBC Driver 13 for SQL Server"),
            (["ODBC Driver 11 for SQL Server"], "ODBC Driver 11 for SQL Server"),
            (["SQL Server Native Client 11.0"], "SQL Server Native Client 11.0"),
            (["SQL Server Native Client 10.0"], "SQL Server Native Client 10.0"),
            (["SQL Server"], "SQL Server"),
            (["PostgreSQL Unicode", driver17, driver18], driver18),
            ([driver18, driver17], driver18),
            (["SQL Server", "SQL Server Native Client 11.0", driver17], driver17),
            (["SQL Server", "SQL Server Native Client 11.0"], "SQL Server Native Client 11.0"),
        ]
        for installed, expected in cases:
            with self.subTest(installed=installed):
                with (
                    patch.object(db.pyodbc, "drivers", return_value=installed),
                    patch.object(db.pyodbc, "connect") as connect,
                ):
                    conn = db.get_connection()

                connect.assert_called_once()
                attributes = dict(
                    part.split("=", 1)
                    for part in connect.call_args.args[0].split(";") if part
                )
                self.assertEqual(attributes["DRIVER"], "{" + expected + "}")
                self.assertEqual(attributes["SERVER"], db.SQL_SERVER)
                self.assertEqual(attributes["DATABASE"], db.SQL_DATABASE)
                self.assertEqual(attributes["Trusted_Connection"], "yes")
                self.assertEqual(attributes["Encrypt"], "yes")
                if expected == "SQL Server":
                    self.assertNotIn("TrustServerCertificate", attributes)
                else:
                    self.assertEqual(attributes["TrustServerCertificate"], "yes")
                self.assertEqual(connect.call_args.kwargs["timeout"], 10)
                self.assertIs(conn, connect.return_value)
                self.assertEqual(conn.timeout, 30)

    def test_connection_requires_compatible_driver(self):
        for installed in ([], ["PostgreSQL Unicode"], ["SQL Server Custom"]):
            with self.subTest(installed=installed):
                with (
                    patch.object(db.pyodbc, "drivers", return_value=installed),
                    patch.object(db.pyodbc, "connect") as connect,
                ):
                    with self.assertRaisesRegex(RuntimeError, "ODBC Driver 18 sau 17"):
                        db.get_connection()
                    connect.assert_not_called()

    def test_connection_propagates_server_error(self):
        failure = RuntimeError("SQL login failed")
        with (
            patch.object(db.pyodbc, "drivers", return_value=[
                "ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server",
            ]),
            patch.object(db.pyodbc, "connect", side_effect=failure) as connect,
        ):
            with self.assertRaises(RuntimeError) as caught:
                db.get_connection()
            self.assertIs(caught.exception, failure)
            connect.assert_called_once()

    def test_vehicle_reads_normalize_dates(self):
        reception = date(2026, 9, 1)
        created = datetime(2026, 9, 1, 8, 30)
        for getter, args, multiple in (
            (db.get_vehicles, ("all",), True),
            (db.get_vehicle, (1,), False),
        ):
            for as_text in (True, False):
                with self.subTest(getter=getter.__name__, as_text=as_text):
                    row = SimpleNamespace(
                        VehicleID=1, VIN="2026-09-01", CRP=None,
                        ReceptionDate=reception.isoformat() if as_text else reception,
                        CreatedAt=created.isoformat(" ") if as_text else created,
                        InvoiceDate=None,
                    )
                    with patch.object(db, "get_connection") as connect:
                        cursor = connect.return_value.__enter__.return_value.cursor.return_value
                        cursor.fetchall.return_value = [row]
                        cursor.fetchone.return_value = row
                        result = getter(*args)
                    vehicle = result[0] if multiple else result
                    self.assertIs(vehicle, row)
                    self.assertEqual(vehicle.ReceptionDate, reception)
                    self.assertEqual(vehicle.CreatedAt, created)
                    self.assertIsNone(vehicle.InvoiceDate)
                    self.assertEqual(vehicle.VIN, "2026-09-01")
                    with (
                        patch.object(db, "get_last_inspection", return_value=None),
                        patch.object(main, "app_today", return_value=date(2026, 9, 12)),
                    ):
                        status = main.calculate_vehicle_status(vehicle)
                        self.assertEqual(status["next_inspection"], date(2026, 9, 30))
                        self.assertEqual(status["countdown"], "18 zile")
                        self.assertEqual(main.get_crp_display(vehicle), "LIPSĂ - ÎNTÂRZIAT")

            with patch.object(db, "get_connection") as connect:
                cursor = connect.return_value.__enter__.return_value.cursor.return_value
                cursor.fetchall.return_value = []
                cursor.fetchone.return_value = None
                self.assertEqual(getter(*args), [] if multiple else None)

    def test_inspection_reads_normalize_dates(self):
        for getter, multiple in ((db.get_inspections, True), (db.get_last_inspection, False)):
            with self.subTest(getter=getter.__name__):
                row = SimpleNamespace(
                    InspectionID=1, InspectionDate="2026-09-12",
                    RecordedAt="2026-09-12 09:14:05", RecordedBy="calin",
                )
                with patch.object(db, "get_connection") as connect:
                    cursor = connect.return_value.__enter__.return_value.cursor.return_value
                    cursor.fetchall.return_value = [row]
                    cursor.fetchone.return_value = row
                    result = getter(1)
                inspection = result[0] if multiple else result
                self.assertEqual(inspection.InspectionDate, date(2026, 9, 12))
                self.assertEqual(inspection.RecordedAt, datetime(2026, 9, 12, 9, 14, 5))
                self.assertEqual(inspection.RecordedAt.strftime("%d.%m.%Y %H:%M"), "12.09.2026 09:14")

        with patch.object(db, "get_connection") as connect:
            connect.return_value.__enter__.return_value.cursor.return_value.fetchone.return_value = None
            self.assertIsNone(db.get_last_inspection(999))

    def test_notifications_skip_already_sent_legacy_dates(self):
        today = date(2026, 9, 12)
        row = SimpleNamespace(
            VehicleID=1, VIN="TEST", Model="Model", CRP=None,
            ReceptionDate="2026-08-13", CreatedAt="2026-08-01 08:00:00",
            LastInspectionDate="2026-08-13", LastInspectionBeforeToday="2026-08-13",
            LastCrpNotificationDate="2026-09-12", LastDay27NotificationDate="2026-09-12",
            LastOverdueNotificationDate="2026-09-12",
            SellerName="Seller", SellerEmail="seller@example.com", SellerManagerEmail=None,
            AdvisorUsername="advisor", AdvisorName="Advisor",
            AdvisorEmail="advisor@example.com", AdvisorManagerEmail=None,
        )
        with (
            patch.object(db, "get_connection") as connect,
            patch.object(db, "notification_lock"),
            patch.object(db, "get_active_advisors", return_value=[]),
            patch.object(db, "get_advisor_manager", return_value=None),
            patch.object(db, "get_general_manager", return_value=None),
            patch.object(notifications, "app_today", return_value=today),
            patch.object(notifications, "send_email") as send,
            patch.object(db, "mark_notification_sent") as mark,
        ):
            cursor = connect.return_value.__enter__.return_value.cursor.return_value
            cursor.fetchall.return_value = [row]
            self.assertEqual(notifications.run_notifications(), 0)
            send.assert_not_called()
            mark.assert_not_called()
            self.assertEqual(cursor.execute.call_args.args[1:], ("2026-09-12",))
        self.assertEqual(row.LastCrpNotificationDate, today)
        self.assertEqual(row.LastDay27NotificationDate, today)
        self.assertEqual(row.LastOverdueNotificationDate, today)
        self.assertEqual(row.LastInspectionDate, date(2026, 8, 13))
        self.assertEqual(notifications.get_inspection_cycle(row, today)[1], 31)

    def test_date_writes_use_iso_parameters(self):
        day = date(2026, 9, 12)
        cases = (
            (db.add_vehicle, ("VIN", "Model", day, "seller"), ("VIN", "Model", "2026-09-12", "seller")),
            (db.set_invoice_date, (1, day), ("2026-09-12", 1)),
            (db.add_inspection, (1, day, "advisor"), (1, "2026-09-12", "advisor")),
            (db.update_inspection, (1, day), ("2026-09-12", 1)),
            (db.mark_notification_sent, (1, "CRP", day), ("2026-09-12", 1)),
        )
        for operation, args, expected in cases:
            with self.subTest(operation=operation.__name__), patch.object(db, "get_connection") as connect:
                conn = connect.return_value.__enter__.return_value
                cursor = conn.cursor.return_value
                cursor.rowcount = 1
                cursor.fetchone.return_value = SimpleNamespace(InvoiceDate=None)
                operation(*args)
                self.assertEqual(cursor.execute.call_args.args[1:], expected)
                self.assertIn("CONVERT(date, ?, 23)", cursor.execute.call_args.args[0])
                conn.commit.assert_called_once()

    def test_connection_is_closed_on_error(self):
        with patch.object(db, "get_connection") as connect:
            with self.assertRaises(ValueError):
                with db.connection_scope():
                    raise ValueError("failure")
            connect.return_value.close.assert_called_once()
            self.assertIs(connect.return_value.__exit__.call_args.args[0], ValueError)

    def test_lock_is_released_on_error(self):
        with patch.object(db, "get_connection") as connect:
            conn = connect.return_value
            conn.cursor.return_value.fetchone.return_value = (0,)
            with self.assertRaises(ValueError):
                with db.notification_lock():
                    raise ValueError("failure")
            sql = [call.args[0] for call in conn.cursor.return_value.execute.call_args_list]
            self.assertTrue(any("sp_releaseapplock" in command for command in sql))
            conn.close.assert_called_once()

    def test_lock_rejection_does_not_run_work(self):
        with patch.object(db, "get_connection") as connect:
            conn = connect.return_value
            conn.cursor.return_value.fetchone.return_value = (-1,)
            work = MagicMock()
            with self.assertRaises(RuntimeError):
                with db.notification_lock():
                    work()
            work.assert_not_called()
            conn.close.assert_called_once()

    def test_preview_never_sends_or_marks(self):
        with patch.object(notifications, "send_email") as send, patch.object(db, "mark_notification_sent") as mark:
            with self.assertLogs(level="INFO"):
                notifications.deliver_notification(1, "CRP", date(2026, 9, 10),
                                                   ["a@example.com"], "Subject", "Body", True)
            send.assert_not_called()
            mark.assert_not_called()

    def test_preview_does_not_acquire_sql_lock(self):
        with (
            patch.object(db, "notification_lock") as lock,
            patch.object(db, "get_notification_vehicles", return_value=[]),
            patch.object(db, "get_active_advisors", return_value=[]),
            patch.object(db, "get_advisor_manager", return_value=None),
            patch.object(db, "get_general_manager", return_value=None),
        ):
            self.assertEqual(notifications.run_notifications(dry_run=True), 0)
            lock.assert_not_called()

    def test_assignment_rejects_advisor_without_crp(self):
        with patch.object(db, "get_connection") as connect:
            conn = connect.return_value.__enter__.return_value
            conn.cursor.return_value.fetchone.return_value = SimpleNamespace(CRP=None, InvoiceDate=None)
            with self.assertRaises(ValueError):
                db.change_vehicle_assignment(1, "seller", "advisor")
            conn.commit.assert_not_called()

    def test_assignment_checks_selected_users(self):
        with patch.object(db, "get_connection") as connect:
            conn = connect.return_value.__enter__.return_value
            cursor = conn.cursor.return_value
            cursor.fetchone.side_effect = [SimpleNamespace(CRP="123", InvoiceDate=None), None]
            with self.assertRaises(ValueError):
                db.change_vehicle_assignment(1, "inactive", "advisor")
            conn.commit.assert_not_called()

    def test_recipient_normalization(self):
        self.assertEqual(notifications.clean_recipients([" A@example.com ", "a@example.com", "", None]),
                         ["A@example.com"])

    def test_assignment_updates_valid_users(self):
        with patch.object(db, "get_connection") as connect:
            conn = connect.return_value.__enter__.return_value
            cursor = conn.cursor.return_value
            cursor.fetchone.side_effect = [SimpleNamespace(CRP="123", InvoiceDate=None),
                                          SimpleNamespace(Username="seller"),
                                          SimpleNamespace(Username="advisor")]
            db.change_vehicle_assignment(1, "seller", "advisor")
            conn.commit.assert_called_once()
            self.assertEqual(cursor.execute.call_args.args[1:], ("seller", "advisor", 1))
