import unittest
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import notifications


class NotificationTests(unittest.TestCase):
    def run_case(self, cycle_day, *, done=False, sent=False, crp="CRP", fail=False):
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
                with self.assertRaises(RuntimeError):
                    notifications.run_notifications()
                mark.assert_not_called()
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
