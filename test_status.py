import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import main


class StatusTests(unittest.TestCase):
    def test_inspection_boundaries(self):
        start = date(2026, 8, 1)
        vehicle = SimpleNamespace(VehicleID=1, ReceptionDate=start, InvoiceDate=None)
        with patch.object(main.db, "get_last_inspection", return_value=None):
            for day, status, text in ((26, "NORMAL", "4 zile"),
                                      (27, "WARNING", "3 zile"),
                                      (29, "WARNING", "1 zi"),
                                      (30, "OVERDUE", "Termen astăzi"),
                                      (31, "OVERDUE", "Întârziere: 1 zi")):
                with self.subTest(day=day):
                    result = main.calculate_vehicle_status(vehicle, start + timedelta(days=day - 1))
                    self.assertEqual((result["status"], result["countdown"]), (status, text))

    def test_inspection_resets_cycle(self):
        today = date(2026, 9, 10)
        vehicle = SimpleNamespace(VehicleID=1, ReceptionDate=date(2026, 1, 1), InvoiceDate=None)
        with patch.object(main.db, "get_last_inspection", return_value=SimpleNamespace(InspectionDate=today)):
            result = main.calculate_vehicle_status(vehicle, today)
            self.assertEqual(result["countdown"], "29 zile")

    def test_closed_vehicle_does_not_load_inspections(self):
        vehicle = SimpleNamespace(InvoiceDate=date(2026, 9, 10))
        with patch.object(main.db, "get_last_inspection") as read:
            self.assertEqual(main.calculate_vehicle_status(vehicle)["status"], "CLOSED")
            read.assert_not_called()
