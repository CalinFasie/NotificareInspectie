import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import db
import notifications


class RuntimeTests(unittest.TestCase):
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
