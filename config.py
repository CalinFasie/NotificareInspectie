import os
from datetime import datetime
from zoneinfo import ZoneInfo

SQL_SERVER = "srv-sql"
SQL_DATABASE = "VehicleCheck"

SMTP_HOST = "mail.carscenter.ro"
SMTP_PORT = 587
SMTP_USER = "report@carscenter.ro"
SMTP_PASSWORD = os.environ.get("VEHICLECHECK_SMTP_PASSWORD")

APP_TIMEZONE = ZoneInfo("Europe/Bucharest")


def app_today():
    return datetime.now(APP_TIMEZONE).date()
