import contextlib
import io
import subprocess
import sys
import unittest
import smtplib
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import notifications


class NotificationTests(unittest.TestCase):
    def run_case(self, cycle_day, *, done=False, sent=False, crp="CRP", fail=False, fail_crp=False):
        today = date(2026, 9, 10)
        vehicle = SimpleNamespace(
            VehicleID=1, VIN="TEST", Model="Model", SellerName="Seller",
            SellerEmail="seller@example.com", SellerManagerEmail=None,
            AdvisorUsername="advisor", AdvisorName="Advisor",
            AdvisorEmail="advisor@example.com", AdvisorManagerEmail=None,
            ReceptionDate=today - timedelta(days=cycle_day - 1),
            CreatedAt=datetime(2026, 8, 1), CRP=crp,
            LastInspectionBeforeToday=None,
            LastInspectionDate=today if done else None,
            LastCrpNotificationDate=today if sent else None,
            LastDay27NotificationDate=today if sent else None,
            LastOverdueNotificationDate=today if sent else None,
        )
        with (
            patch.object(notifications.db, "notification_lock"),
            patch.object(notifications, "app_today", return_value=today),
            patch.object(notifications.db, "get_notification_vehicles", return_value=[vehicle]),
            patch.object(notifications.db, "get_active_advisors", return_value=[]),
            patch.object(notifications.db, "get_advisor_manager", return_value=None),
            patch.object(notifications.db, "get_general_manager", return_value=None),
            patch.object(notifications.db, "mark_notification_sent") as mark,
            patch.object(notifications, "send_email") as send,
        ):
            if fail:
                send.side_effect = RuntimeError("SMTP failed")
                with self.assertLogs(level="ERROR"):
                    self.assertEqual(notifications.run_notifications(), 1)
                mark.assert_not_called()
            elif fail_crp:
                send.side_effect = [RuntimeError("CRP failed"), None]
                with self.assertLogs(level="ERROR"):
                    self.assertEqual(notifications.run_notifications(), 1)
            else:
                notifications.run_notifications()
            return send.call_count, [call.args[1] for call in mark.call_args_list]

    def test_schedule(self):
        for day, expected in [(26, []), (27, ["DAY27"]), (28, []),
                              (30, ["OVERDUE"]), (31, ["OVERDUE"])]:
            with self.subTest(day=day):
                self.assertEqual(self.run_case(day), (len(expected), expected))

    def test_same_day_inspection_preserves_current_rule(self):
        self.assertEqual(self.run_case(31, done=True), (0, []))
        self.assertEqual(self.run_case(30, done=True), (1, ["OVERDUE"]))

    def test_already_sent_today(self):
        for day in (27, 30, 31):
            with self.subTest(day=day):
                self.assertEqual(self.run_case(day, sent=True, crp=None), (0, []))

    def test_crp_and_inspection_alerts_are_independent(self):
        self.assertEqual(self.run_case(27, crp=None), (2, ["CRP", "DAY27"]))

    def test_failed_send_is_not_marked(self):
        self.run_case(30, fail=True)

    def test_crp_failure_does_not_skip_inspection(self):
        self.assertEqual(self.run_case(27, crp=None, fail_crp=True), (2, ["DAY27"]))

    def test_partial_refusal_is_reported(self):
        with (
            patch.object(notifications, "SMTP_PASSWORD", "test"),
            patch.object(notifications.smtplib, "SMTP") as smtp,
        ):
            smtp.return_value.__enter__.return_value.sendmail.return_value = {
                "bad@example.com": (550, b"Rejected")
            }
            with self.assertRaises(smtplib.SMTPRecipientsRefused):
                notifications.send_email(["ok@example.com", "bad@example.com"], "Test", "Body")

    def test_empty_recipients_do_not_connect(self):
        with patch.object(notifications.smtplib, "SMTP") as smtp:
            with self.assertRaises(ValueError):
                notifications.send_email([], "Test", "Body")
            smtp.assert_not_called()

    def test_cli_dry_run_invokes_workflow_and_returns_success(self):
        with patch.object(notifications, "run_notifications", return_value=0) as run:
            with self.assertLogs(level="INFO") as captured:
                result = notifications.main(["--dry-run"])

        run.assert_called_once_with(dry_run=True)
        self.assertEqual(result, 0)
        messages = "\n".join(captured.output)
        self.assertIn("a început", messages)
        self.assertIn("dry-run", messages)
        self.assertIn("cu succes", messages)

    def test_cli_without_dry_run_invokes_workflow_and_returns_success(self):
        with patch.object(notifications, "run_notifications", return_value=0) as run:
            with self.assertLogs(level="INFO") as captured:
                result = notifications.main([])

        run.assert_called_once_with(dry_run=False)
        self.assertEqual(result, 0)
        self.assertIn("normal", "\n".join(captured.output))

    def test_cli_processing_failure_returns_nonzero(self):
        with patch.object(notifications, "run_notifications", return_value=1) as run:
            with self.assertLogs(level="ERROR") as captured:
                result = notifications.main([])

        run.assert_called_once_with(dry_run=False)
        self.assertNotEqual(result, 0)
        self.assertIn("s-a încheiat cu erori (1)", "\n".join(captured.output))

    def test_cli_unexpected_failure_returns_nonzero(self):
        with patch.object(notifications, "run_notifications", side_effect=RuntimeError("sensitive details")):
            with self.assertLogs(level="ERROR") as captured:
                result = notifications.main([])

        self.assertNotEqual(result, 0)
        self.assertIn("a eșuat", "\n".join(captured.output))
        self.assertNotIn("sensitive details", "\n".join(captured.output))

    def test_cli_argument_parsing(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(SystemExit) as help_exit:
                notifications.main(["--help"])
        self.assertEqual(help_exit.exception.code, 0)
        self.assertIn("--dry-run", stdout.getvalue())

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as invalid_exit:
                notifications.main(["--unexpected-option"])
        self.assertEqual(invalid_exit.exception.code, 2)

    def test_importing_notifications_does_not_execute_workflow(self):
        script = "\n".join((
            "import sys, types",
            "def unexpected(*args, **kwargs):",
            "    raise AssertionError('notification workflow ran during import')",
            "db = types.ModuleType('db')",
            "for name in ('notification_lock', 'get_notification_vehicles', 'get_active_advisors', 'get_advisor_manager', 'get_general_manager'):",
            "    setattr(db, name, unexpected)",
            "sys.modules['db'] = db",
            "config = types.ModuleType('config')",
            "config.SMTP_HOST = config.SMTP_PASSWORD = config.SMTP_USER = ''",
            "config.SMTP_PORT = 0",
            "config.app_today = unexpected",
            "sys.modules['config'] = config",
            "import notifications",
        ))
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_error_does_not_stop_next_vehicle(self):
        with (
            patch.object(notifications.db, "notification_lock"),
            patch.object(notifications.db, "get_notification_vehicles", return_value=[
                SimpleNamespace(VehicleID=1), SimpleNamespace(VehicleID=2)]),
            patch.object(notifications.db, "get_active_advisors", return_value=[]),
            patch.object(notifications.db, "get_advisor_manager", return_value=None),
            patch.object(notifications.db, "get_general_manager", return_value=None),
            patch.object(notifications, "process_vehicles", side_effect=[RuntimeError("failure"), 0]) as process,
            self.assertLogs(level="ERROR"),
        ):
            self.assertEqual(notifications.run_notifications(), 1)
            self.assertEqual(process.call_count, 2)
