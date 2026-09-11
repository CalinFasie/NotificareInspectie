from contextlib import contextmanager
from datetime import date, datetime

import pyodbc

from config import SQL_DATABASE, SQL_SERVER


def get_sql_server_driver():
    installed_drivers = set(pyodbc.drivers())
    for driver in (
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "ODBC Driver 11 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server Native Client 10.0",
        "SQL Server",
    ):
        if driver in installed_drivers:
            return driver

    raise RuntimeError(
        "Nu este disponibil un driver ODBC compatibil cu aplicația. "
        "Instalează Microsoft ODBC Driver 18 sau 17 for SQL Server "
        "pe acest calculator, pentru arhitectura aplicației (32/64 biți)."
    )


def get_connection():
    driver = get_sql_server_driver()
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
    )
    # Driverul inclus în Windows nu oferă aceleași opțiuni ca ODBC/SNAC.
    if driver != "SQL Server":
        connection_string += "TrustServerCertificate=yes;"
    conn = pyodbc.connect(connection_string, timeout=10)
    conn.timeout = 30
    return conn


def _normalize_dates(row):
    """Normalizează coloanele DATE/DATETIME2 returnate ca text de drivere vechi."""
    if row is None:
        return None

    for column in (
        "ReceptionDate", "InvoiceDate", "InspectionDate",
        "LastCrpNotificationDate", "LastDay27NotificationDate",
        "LastOverdueNotificationDate", "LastInspectionDate",
        "LastInspectionBeforeToday",
    ):
        value = getattr(row, column, None)
        if isinstance(value, str):
            setattr(row, column, date.fromisoformat(value))
        elif isinstance(value, datetime):
            setattr(row, column, value.date())

    for column in ("CreatedAt", "RecordedAt"):
        value = getattr(row, column, None)
        if isinstance(value, str):
            setattr(row, column, datetime.fromisoformat(value))
    return row


def _date_parameter(value):
    """Trimite datele în format ISO, inclusiv prin drivere fără SQL_TYPE_DATE."""
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat() if isinstance(value, date) else value


@contextmanager
def connection_scope():
    conn = get_connection()
    try:
        with conn as active:
            yield active
    finally:
        conn.close()


@contextmanager
def notification_lock():
    conn = get_connection()
    acquired = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DECLARE @result int;
            EXEC @result = sys.sp_getapplock
                @Resource = 'VehicleCheck.notifications',
                @LockMode = 'Exclusive', @LockOwner = 'Session',
                @LockTimeout = 0;
            SELECT @result;
        """)
        acquired = cursor.fetchone()[0] >= 0
        if not acquired:
            raise RuntimeError("Procesul de notificări este deja activ sau blocarea SQL a eșuat.")
        yield
    finally:
        try:
            if acquired:
                conn.cursor().execute("""
                    EXEC sys.sp_releaseapplock
                        @Resource = 'VehicleCheck.notifications',
                        @LockOwner = 'Session';
                """)
        finally:
            conn.close()


def get_user_config(username):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                ConfigID,
                Username,
                FullName,
                Role,
                Email,
                ManagerEmail,
                Active
            FROM dbo._CONFIG
            WHERE Username = ?
              AND Active = 1
        """, username)

        return cursor.fetchone()


def get_active_advisors():
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                Username,
                FullName,
                Email,
                ManagerEmail
            FROM dbo._CONFIG
            WHERE Role = 'ADVISOR'
              AND Active = 1
            ORDER BY FullName
        """)

        return cursor.fetchall()


def get_general_manager():
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                Username,
                FullName,
                Email
            FROM dbo._CONFIG
            WHERE Role = 'GENERAL_MANAGER'
              AND Active = 1
        """)

        return cursor.fetchone()


def get_vehicles(status_filter="active"):
    filters = {
        "all": "",
        "active": "WHERE InvoiceDate IS NULL",
        "inactive": "WHERE InvoiceDate IS NOT NULL",
    }
    if status_filter not in filters:
        raise ValueError("Filtrul pentru vehicule nu este valid.")

    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                VehicleID,
                VIN,
                Model,
                ReceptionDate,
                CreatedAt,
                SellerUsername,
                CRP,
                AdvisorUsername,
                InvoiceDate
            FROM dbo._VEHICLES
            {filters[status_filter]}
            ORDER BY ReceptionDate, VehicleID
        """)

        return [_normalize_dates(row) for row in cursor.fetchall()]


def get_active_vehicles():
    return get_vehicles("active")


def get_vehicle(vehicle_id):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                VehicleID,
                VIN,
                Model,
                ReceptionDate,
                CreatedAt,
                SellerUsername,
                CRP,
                AdvisorUsername,
                InvoiceDate
            FROM dbo._VEHICLES
            WHERE VehicleID = ?
        """, vehicle_id)

        return _normalize_dates(cursor.fetchone())


def add_vehicle(vin, model, reception_date, seller_username):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dbo._VEHICLES
                (VIN, Model, ReceptionDate, SellerUsername)
            VALUES
                (?, ?, CONVERT(date, ?, 23), ?)
        """, vin, model, _date_parameter(reception_date), seller_username)

        conn.commit()


def set_crp(vehicle_id, crp, advisor_username):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo._VEHICLES
            SET
                CRP = ?,
                AdvisorUsername = ?
            WHERE VehicleID = ?
              AND InvoiceDate IS NULL
              AND CRP IS NULL
              AND EXISTS (
                  SELECT 1 FROM dbo._CONFIG
                  WHERE Username = ? AND Active = 1 AND Role = 'ADVISOR'
              )
        """, crp, advisor_username, vehicle_id, advisor_username)

        if cursor.rowcount != 1:
            raise ValueError("Vehiculul nu mai este activ, are deja CRP sau consilierul nu mai este activ. Reîncarcă lista.")
        conn.commit()


def set_invoice_date(vehicle_id, invoice_date):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo._VEHICLES
            SET InvoiceDate = CONVERT(date, ?, 23)
            WHERE VehicleID = ?
              AND InvoiceDate IS NULL
        """, _date_parameter(invoice_date), vehicle_id)

        if cursor.rowcount != 1:
            raise ValueError("Vehiculul nu mai este activ sau nu există. Reîncarcă lista.")
        conn.commit()


def change_vehicle_assignment(vehicle_id, seller_username, advisor_username):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT CRP, InvoiceDate FROM dbo._VEHICLES WITH (UPDLOCK, HOLDLOCK)
            WHERE VehicleID = ?
        """, vehicle_id)
        vehicle = cursor.fetchone()
        if vehicle is None or vehicle.InvoiceDate is not None:
            raise ValueError("Vehiculul nu mai este activ sau nu există.")
        if advisor_username and not vehicle.CRP:
            raise ValueError("Introdu CRP înainte de alocarea unui consilier.")

        cursor.execute("""
            SELECT Username FROM dbo._CONFIG WITH (UPDLOCK, HOLDLOCK)
            WHERE Username = ? AND Active = 1
              AND Role IN ('SELLER', 'SELLER_MANAGER', 'ADVISOR_MANAGER', 'GENERAL_MANAGER', 'ADMIN')
        """, seller_username)
        if cursor.fetchone() is None:
            raise ValueError("Seller trebuie să fie un utilizator activ cu drept de adăugare vehicule.")
        if advisor_username:
            cursor.execute("""
                SELECT Username FROM dbo._CONFIG WITH (UPDLOCK, HOLDLOCK)
                WHERE Username = ? AND Active = 1 AND Role = 'ADVISOR'
            """, advisor_username)
            if cursor.fetchone() is None:
                raise ValueError("Consilierul selectat nu mai este activ.")

        if advisor_username:
            cursor.execute("""
                UPDATE dbo._VEHICLES
                SET
                    SellerUsername = ?,
                    AdvisorUsername = ?
                WHERE VehicleID = ?
            """, seller_username, advisor_username, vehicle_id)
        else:
            cursor.execute("""
                UPDATE dbo._VEHICLES
                SET
                    SellerUsername = ?,
                    CRP = NULL,
                    AdvisorUsername = NULL
                WHERE VehicleID = ?
            """, seller_username, vehicle_id)

        conn.commit()


def get_inspections(vehicle_id):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                InspectionID,
                VehicleID,
                InspectionDate,
                RecordedBy,
                RecordedAt
            FROM dbo._INSPECTIONS
            WHERE VehicleID = ?
            ORDER BY InspectionDate DESC, InspectionID DESC
        """, vehicle_id)

        return [_normalize_dates(row) for row in cursor.fetchall()]


def get_last_inspection(vehicle_id):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                InspectionID,
                VehicleID,
                InspectionDate,
                RecordedBy,
                RecordedAt
            FROM dbo._INSPECTIONS
            WHERE VehicleID = ?
            ORDER BY InspectionDate DESC, InspectionID DESC
        """, vehicle_id)

        return _normalize_dates(cursor.fetchone())


def add_inspection(vehicle_id, inspection_date, recorded_by):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT InvoiceDate
            FROM dbo._VEHICLES WITH (UPDLOCK, HOLDLOCK)
            WHERE VehicleID = ?
        """, vehicle_id)
        vehicle = cursor.fetchone()
        if vehicle is None or vehicle.InvoiceDate is not None:
            raise ValueError("Nu poți adăuga verificări unui vehicul facturat sau inexistent.")
        cursor.execute("""
            INSERT INTO dbo._INSPECTIONS
                (VehicleID, InspectionDate, RecordedBy)
            VALUES
                (?, CONVERT(date, ?, 23), ?)
        """, vehicle_id, _date_parameter(inspection_date), recorded_by)

        conn.commit()


def update_inspection(inspection_id, inspection_date):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo._INSPECTIONS
            SET InspectionDate = CONVERT(date, ?, 23)
            WHERE InspectionID = ?
        """, _date_parameter(inspection_date), inspection_id)

        if cursor.rowcount != 1:
            raise ValueError("Verificarea nu mai există. Reîncarcă istoricul.")
        conn.commit()


def get_notification_vehicles(today):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                v.VehicleID,
                v.VIN,
                v.Model,
                v.ReceptionDate,
                v.CreatedAt,
                v.SellerUsername,
                v.CRP,
                v.AdvisorUsername,

                v.LastCrpNotificationDate,
                v.LastDay27NotificationDate,
                v.LastOverdueNotificationDate,

                s.FullName AS SellerName,
                s.Email AS SellerEmail,
                s.ManagerEmail AS SellerManagerEmail,

                a.FullName AS AdvisorName,
                a.Email AS AdvisorEmail,
                a.ManagerEmail AS AdvisorManagerEmail,

                (
                    SELECT MAX(i.InspectionDate)
                    FROM dbo._INSPECTIONS i
                    WHERE i.VehicleID = v.VehicleID
                ) AS LastInspectionDate,

                (
                    SELECT MAX(i.InspectionDate)
                    FROM dbo._INSPECTIONS i
                    WHERE i.VehicleID = v.VehicleID
                      AND i.InspectionDate < CONVERT(date, ?, 23)
                ) AS LastInspectionBeforeToday

            FROM dbo._VEHICLES v

            INNER JOIN dbo._CONFIG s
                ON s.Username = v.SellerUsername

            LEFT JOIN dbo._CONFIG a
                ON a.Username = v.AdvisorUsername

            WHERE v.InvoiceDate IS NULL
        """, _date_parameter(today))

        return [_normalize_dates(row) for row in cursor.fetchall()]

def get_config_users():
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                ConfigID,
                Username,
                FullName,
                Role,
                Email,
                ManagerEmail,
                Active
            FROM dbo._CONFIG
            ORDER BY FullName
        """)

        return cursor.fetchall()


def add_config_user(username, full_name, role, email, manager_email=None):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dbo._CONFIG
                (Username, FullName, Role, Email, ManagerEmail)
            VALUES
                (?, ?, ?, ?, ?)
        """, username, full_name, role, email, manager_email)

        conn.commit()


def update_config_user(
    config_id,
    username,
    full_name,
    role,
    email,
    manager_email,
):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Username FROM dbo._CONFIG WITH (UPDLOCK, HOLDLOCK)
            WHERE ConfigID = ?
        """, config_id)
        current = cursor.fetchone()
        if current is None:
            raise ValueError("Utilizatorul nu mai există.")
        if current.Username != username:
            raise ValueError("Username nu poate fi schimbat; este folosit în alocări și istoric.")
        cursor.execute("""
            UPDATE dbo._CONFIG
            SET
                FullName = ?,
                Role = ?,
                Email = ?,
                ManagerEmail = ?
            WHERE ConfigID = ?
        """,
            full_name,
            role,
            email,
            manager_email,
            config_id
        )

        conn.commit()


def set_config_user_active(config_id, active):
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo._CONFIG
            SET Active = ?
            WHERE ConfigID = ?
        """, active, config_id)

        if cursor.rowcount != 1:
            raise ValueError("Utilizatorul nu mai există. Reîncarcă lista.")
        conn.commit()

def get_advisor_manager():
    with connection_scope() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                Username,
                FullName,
                Email
            FROM dbo._CONFIG
            WHERE Role = 'ADVISOR_MANAGER'
              AND Active = 1
        """)

        return cursor.fetchone()

def mark_notification_sent(vehicle_id, notification_type, sent_date):
    columns = {
        "CRP": "LastCrpNotificationDate",
        "DAY27": "LastDay27NotificationDate",
        "OVERDUE": "LastOverdueNotificationDate",
    }

    column = columns.get(notification_type)

    if column is None:
        raise ValueError("Tip notificare invalid.")

    with connection_scope() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            UPDATE dbo._VEHICLES
            SET {column} = CONVERT(date, ?, 23)
            WHERE VehicleID = ?
            """,
            _date_parameter(sent_date),
            vehicle_id,
        )

        conn.commit()
