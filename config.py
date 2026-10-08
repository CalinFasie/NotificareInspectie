import os
from datetime import datetime
from zoneinfo import ZoneInfo

SQL_SERVER = "srv-sql"
SQL_DATABASE = "carsm"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "itimpcalin@gmail.com"
SMTP_PASSWORD = os.environ.get("VEHICLECHECK_SMTP_PASSWORD")

APP_TIMEZONE = ZoneInfo("Europe/Bucharest")


def app_today():
    return datetime.now(APP_TIMEZONE).date()
