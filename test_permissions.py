import unittest
from types import SimpleNamespace
from unittest.mock import patch

import db
import main


class PermissionTests(unittest.TestCase):
    def test_disabled_user_is_rejected(self):
        app = main.VehicleCheckApp.__new__(main.VehicleCheckApp)
        app.user = SimpleNamespace(Role="ADMIN")
        with patch.object(main.db, "get_user_config", return_value=None):
            with self.assertRaises(PermissionError):
                app.require_permission(main.can_manage_config)

    def test_changed_role_is_rechecked(self):
        app = main.VehicleCheckApp.__new__(main.VehicleCheckApp)
        app.user = SimpleNamespace(Role="ADMIN")
        with patch.object(main, "load_current_user", return_value=SimpleNamespace(Role="SELLER")):
            with self.assertRaises(PermissionError):
                app.require_permission(main.can_manage_config)
            app.require_permission(main.can_add_vehicle)
            self.assertEqual(app.user.Role, "SELLER")

    def test_username_rename_is_rejected_before_update(self):
        with patch.object(db, "get_connection") as connection:
            cursor = connection.return_value.__enter__.return_value.cursor.return_value
            cursor.fetchone.return_value = SimpleNamespace(Username="original")
            with self.assertRaises(ValueError):
                db.update_config_user(1, "renamed", "Name", "SELLER", "a@example.com", None)
            self.assertEqual(cursor.execute.call_count, 1)

    def test_other_user_fields_can_be_updated(self):
        with patch.object(db, "get_connection") as connection:
            conn = connection.return_value.__enter__.return_value
            cursor = conn.cursor.return_value
            cursor.fetchone.return_value = SimpleNamespace(Username="original")
            db.update_config_user(1, "original", "Name", "SELLER", "a@example.com", None)
            self.assertEqual(cursor.execute.call_count, 2)
            conn.commit.assert_called_once()
