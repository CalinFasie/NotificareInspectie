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


_DEFAULT_DAY27_MARKER = object()


class NotificationTests(unittest.TestCase):
    def run_case(self, cycle_day, *, done=False, sent=False,
                 day27_marker=_DEFAULT_DAY27_MARKER, today=None, cycle_start=None,
                 crp="CRP", fail=False, fail_crp=False, notification_type=None,
                 dry_run=False):
        if today is None:
            today = date(2026, 9, 10)
        if cycle_start is None:
            cycle_start = today - timedelta(days=cycle_day - 1)
        if day27_marker is _DEFAULT_DAY27_MARKER:
            day27_marker = today if sent else None

        vehicle = SimpleNamespace(
            VehicleID=1, VIN="TEST", Model="Model", SellerName="Seller",
            SellerEmail="seller@example.com", SellerManagerEmail=None,
            AdvisorUsername="advisor", AdvisorName="Advisor",
            AdvisorEmail="advisor@example.com", AdvisorManagerEmail=None,
            ReceptionDate=cycle_start,
            CreatedAt=datetime(2026, 8, 1), CRP=crp,
            LastInspectionBeforeToday=None,
            LastInspectionDate=today if done else None,
            LastCrpNotificationDate=today if sent else None,
            LastDay27NotificationDate=day27_marker,
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
                    self.assertEqual(
                        notifications.run_notifications(
                            dry_run=dry_run,
                            notification_type=notification_type,
                        ),
                        1,
                    )
                mark.assert_not_called()
            elif fail_crp:
                send.side_effect = [RuntimeError("CRP failed"), None]
                with self.assertLogs(level="ERROR"):
                    self.assertEqual(
                        notifications.run_notifications(
                            dry_run=dry_run,
                            notification_type=notification_type,
                        ),
                        1,
                    )
            else:
                notifications.run_notifications(
                    dry_run=dry_run,
                    notification_type=notification_type,
                )
            return send.call_count, [call.args[1] for call in mark.call_args_list]

    def test_schedule(self):
        for day, expected in [(26, []), (27, ["DAY27"]), (28, ["DAY27"]),
                              (29, ["DAY27"]), (30, ["OVERDUE"]),
                              (31, ["OVERDUE"])]:
            with self.subTest(day=day):
                self.assertEqual(self.run_case(day), (len(expected), expected))

    def test_day27_catch_up_window(self):
        for day, expected in ((26, 0), (27, 1), (28, 1), (29, 1),
                              (30, 0), (31, 0), (45, 0)):
            with self.subTest(day=day):
                self.assertEqual(
                    self.run_case(day, notification_type="DAY27"),
                    (expected, ["DAY27"] if expected else []),
                )

    def test_day27_sent_on_day27_is_not_resent_on_days28_or29(self):
        cycle_start = date(2026, 8, 15)
        sent_date = cycle_start + timedelta(days=26)
        for day, today in (
            (28, cycle_start + timedelta(days=27)),
            (29, cycle_start + timedelta(days=28)),
        ):
            with self.subTest(day=day):
                self.assertEqual(
                    self.run_case(
                        day,
                        today=today,
                        cycle_start=cycle_start,
                        day27_marker=sent_date,
                        notification_type="DAY27",
                    ),
                    (0, []),
                )

    def test_day27_catch_up_sent_on_day28_is_not_resent_on_day29(self):
        cycle_start = date(2026, 8, 15)
        day28 = cycle_start + timedelta(days=27)
        day29 = cycle_start + timedelta(days=28)
        self.assertEqual(
            self.run_case(
                28,
                today=day28,
                cycle_start=cycle_start,
                notification_type="DAY27",
            ),
            (1, ["DAY27"]),
        )
        self.assertEqual(
            self.run_case(
                29,
                today=day29,
                cycle_start=cycle_start,
                day27_marker=day28,
                notification_type="DAY27",
            ),
            (0, []),
        )

    def test_previous_cycle_day27_marker_does_not_block_new_cycle(self):
        cycle_start = date(2026, 8, 15)
        self.assertEqual(
            self.run_case(
                27,
                cycle_start=cycle_start,
                day27_marker=cycle_start - timedelta(days=1),
                notification_type="DAY27",
            ),
            (1, ["DAY27"]),
        )

    def test_failed_day27_send_can_retry_on_day28(self):
        cycle_start = date(2026, 8, 15)
        day27 = cycle_start + timedelta(days=26)
        day28 = cycle_start + timedelta(days=27)
        failed_send_count, failed_marks = self.run_case(
            27,
            today=day27,
            cycle_start=cycle_start,
            fail=True,
            notification_type="DAY27",
        )
        self.assertEqual((failed_send_count, failed_marks), (1, []))
        self.assertEqual(
            self.run_case(
                28,
                today=day28,
                cycle_start=cycle_start,
                notification_type="DAY27",
            ),
            (1, ["DAY27"]),
        )

    def test_same_day_inspection_preserves_current_rule(self):
        self.assertEqual(self.run_case(31, done=True), (0, []))
        self.assertEqual(self.run_case(30, done=True), (1, ["OVERDUE"]))

    def test_already_sent_today(self):
        for day in (27, 30, 31):
            with self.subTest(day=day):
                self.assertEqual(self.run_case(day, sent=True, crp=None), (0, []))
        self.assertEqual(
            self.run_case(27, sent=True, crp=None, notification_type="DAY27"),
            (0, []),
        )

    def test_day27_filter_sends_only_day27(self):
        self.assertEqual(
            self.run_case(27, crp=None, notification_type="DAY27"),
            (1, ["DAY27"]),
        )

    def test_day27_filter_skips_day30_and_overdue(self):
        for day in (30, 31):
            with self.subTest(day=day):
                self.assertEqual(
                    self.run_case(day, notification_type="DAY27"),
                    (0, []),
                )

    def test_day30_and_overdue_filters_select_their_cycle_days(self):
        self.assertEqual(self.run_case(30, notification_type="DAY30"), (1, ["OVERDUE"]))
        self.assertEqual(self.run_case(31, notification_type="OVERDUE"), (1, ["OVERDUE"]))
        self.assertEqual(self.run_case(31, notification_type="DAY30"), (0, []))
        self.assertEqual(self.run_case(30, notification_type="OVERDUE"), (0, []))

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

        run.assert_called_once_with(dry_run=True, notification_type=None)
        self.assertEqual(result, 0)
        messages = "\n".join(captured.output)
        self.assertIn("a început", messages)
        self.assertIn("dry-run", messages)
        self.assertIn("cu succes", messages)

    def test_cli_without_dry_run_invokes_workflow_and_returns_success(self):
        with patch.object(notifications, "run_notifications", return_value=0) as run:
            with self.assertLogs(level="INFO") as captured:
                result = notifications.main([])

        run.assert_called_once_with(dry_run=False, notification_type=None)
        self.assertEqual(result, 0)
        self.assertIn("normal", "\n".join(captured.output))

    def test_cli_accepts_notification_type_filters(self):
        for argv, expected_type, expected_dry_run in (
            (["--type", "DAY27"], "DAY27", False),
            (["--type", "DAY27", "--dry-run"], "DAY27", True),
            (["--type", "CRP"], "CRP", False),
            (["--type", "DAY30"], "DAY30", False),
            (["--type", "OVERDUE"], "OVERDUE", False),
        ):
            with self.subTest(argv=argv):
                with patch.object(notifications, "run_notifications", return_value=0) as run:
                    with self.assertLogs(level="INFO"):
                        self.assertEqual(notifications.main(argv), 0)
                run.assert_called_once_with(
                    dry_run=expected_dry_run,
                    notification_type=expected_type,
                )

    def test_day27_dry_run_previews_only_day27_without_sending_or_marking(self):
        with self.assertLogs(level="INFO") as captured:
            send_count, marked_types = self.run_case(
                27,
                crp=None,
                notification_type="DAY27",
                dry_run=True,
            )

        previews = [line for line in captured.output if "PREVIZUALIZARE" in line]
        self.assertEqual(send_count, 0)
        self.assertEqual(marked_types, [])
        self.assertEqual(len(previews), 1)
        self.assertIn("Tip=DAY27", previews[0])
        self.assertIn("ZiCiclu=27", previews[0])
        self.assertNotRegex(previews[0], r"Tip=(CRP|DAY30|OVERDUE)")

    def test_cli_processing_failure_returns_nonzero(self):
        with patch.object(notifications, "run_notifications", return_value=1) as run:
            with self.assertLogs(level="ERROR") as captured:
                result = notifications.main([])

        run.assert_called_once_with(dry_run=False, notification_type=None)
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
        self.assertIn("--type", stdout.getvalue())
        self.assertIn("--smtp-test-recipient", stdout.getvalue())
        for notification_type in ("CRP", "DAY27", "DAY30", "OVERDUE"):
            self.assertIn(notification_type, stdout.getvalue())

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as invalid_exit:
                notifications.main(["--type", "INVALID"])
        self.assertEqual(invalid_exit.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as invalid_option_exit:
                notifications.main(["--unexpected-option"])
        self.assertEqual(invalid_option_exit.exception.code, 2)

    def test_smtp_test_sends_once_to_requested_recipient_and_returns_zero(self):
        recipient = "test-inbox@example.com"
        with (
            patch.object(notifications, "send_email") as send,
            self.assertLogs(level="INFO") as captured,
        ):
            result = notifications.main(["--smtp-test-recipient", recipient])

        self.assertEqual(result, 0)
        send.assert_called_once_with(
            [recipient],
            "[VehicleCheck TEST] SMTP verification",
            "This is only a VehicleCheck SMTP connectivity test. "
            "No production notifications were processed.",
        )
        self.assertIn("sent successfully", "\n".join(captured.output))

    def test_smtp_test_skips_notification_workflow_and_all_sql_operations(self):
        with (
            patch.object(notifications, "send_email"),
            patch.object(notifications, "run_notifications") as run,
            patch.object(notifications, "process_vehicles") as process,
            patch.object(notifications.db, "notification_lock") as lock,
            patch.object(notifications.db, "get_notification_vehicles") as get_vehicles,
            patch.object(notifications.db, "get_active_advisors") as get_advisors,
            patch.object(notifications.db, "mark_notification_sent") as mark,
            self.assertLogs(level="INFO"),
        ):
            result = notifications.main([
                "--smtp-test-recipient",
                "test-inbox@example.com",
            ])

        self.assertEqual(result, 0)
        run.assert_not_called()
        process.assert_not_called()
        lock.assert_not_called()
        get_vehicles.assert_not_called()
        get_advisors.assert_not_called()
        mark.assert_not_called()

    def test_smtp_test_failure_returns_one_without_logging_password(self):
        password = "test-password-must-not-be-logged"
        with (
            patch.object(notifications, "SMTP_PASSWORD", password),
            patch.object(
                notifications,
                "send_email",
                side_effect=RuntimeError(f"SMTP authentication failed for {password}"),
            ),
            self.assertLogs(level="ERROR") as captured,
        ):
            result = notifications.main([
                "--smtp-test-recipient",
                "test-inbox@example.com",
            ])

        messages = "\n".join(captured.output)
        self.assertEqual(result, 1)
        self.assertIn("RuntimeError", messages)
        self.assertNotIn(password, messages)

    def test_smtp_test_rejects_missing_empty_and_incompatible_arguments(self):
        invalid_arguments = (
            ["--smtp-test-recipient"],
            ["--smtp-test-recipient", ""],
            ["--smtp-test-recipient", "   "],
            ["--smtp-test-recipient", "test-inbox@example.com", "--type", "DAY27"],
            ["--smtp-test-recipient", "test-inbox@example.com", "--dry-run"],
        )

        with patch.object(notifications, "send_email") as send:
            for argv in invalid_arguments:
                with self.subTest(argv=argv):
                    with contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as exit_error:
                            notifications.main(argv)
                    self.assertEqual(exit_error.exception.code, 2)

        send.assert_not_called()

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
