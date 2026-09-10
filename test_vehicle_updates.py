import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import db


class VehicleUpdateTests(unittest.TestCase):
    def test_no_update_is_reported_without_commit(self):
        for operation, args in (
            (db.set_crp, (1, "CRP", "advisor")),
            (db.set_invoice_date, (1, date(2026, 9, 10))),
        ):
            with self.subTest(operation=operation.__name__), patch.object(db, "get_connection") as connect:
                conn = connect.return_value.__enter__.return_value
                conn.cursor.return_value.rowcount = 0
                with self.assertRaises(ValueError):
                    operation(*args)
                conn.commit.assert_not_called()

    def test_successful_updates_commit(self):
        for operation, args in (
            (db.set_crp, (1, "CRP", "advisor")),
            (db.set_invoice_date, (1, date(2026, 9, 10))),
        ):
            with self.subTest(operation=operation.__name__), patch.object(db, "get_connection") as connect:
                conn = connect.return_value.__enter__.return_value
                conn.cursor.return_value.rowcount = 1
                operation(*args)
                conn.commit.assert_called_once()

    def test_closed_or_missing_vehicle_cannot_receive_inspection(self):
        for vehicle in (None, SimpleNamespace(InvoiceDate=date(2026, 9, 10))):
            with self.subTest(vehicle=vehicle), patch.object(db, "get_connection") as connect:
                conn = connect.return_value.__enter__.return_value
                cursor = conn.cursor.return_value
                cursor.fetchone.return_value = vehicle
                with self.assertRaises(ValueError):
                    db.add_inspection(1, date(2026, 9, 10), "advisor")
                self.assertEqual(cursor.execute.call_count, 1)
                conn.commit.assert_not_called()

    def test_active_vehicle_receives_inspection(self):
        with patch.object(db, "get_connection") as connect:
            conn = connect.return_value.__enter__.return_value
            cursor = conn.cursor.return_value
            cursor.fetchone.return_value = SimpleNamespace(InvoiceDate=None)
            db.add_inspection(1, date(2026, 9, 10), "advisor")
            self.assertEqual(cursor.execute.call_count, 2)
            conn.commit.assert_called_once()
