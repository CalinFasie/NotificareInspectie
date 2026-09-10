import pyodbc

from config import SQL_DATABASE, SQL_SERVER


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )


def get_user_config(username):
    with get_connection() as conn:
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
            FROM dbo.CONFIG
            WHERE Username = ?
              AND Active = 1
        """, username)

        return cursor.fetchone()


def get_active_advisors():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                Username,
                FullName,
                Email,
                ManagerEmail
            FROM dbo.CONFIG
            WHERE Role = 'ADVISOR'
              AND Active = 1
            ORDER BY FullName
        """)

        return cursor.fetchall()


def get_general_manager():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                Username,
                FullName,
                Email
            FROM dbo.CONFIG
            WHERE Role = 'GENERAL_MANAGER'
              AND Active = 1
        """)

        return cursor.fetchone()


def get_active_vehicles():
    with get_connection() as conn:
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
            FROM dbo.VEHICLES
            WHERE InvoiceDate IS NULL
            ORDER BY ReceptionDate, VehicleID
        """)

        return cursor.fetchall()


def get_vehicle(vehicle_id):
    with get_connection() as conn:
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
            FROM dbo.VEHICLES
            WHERE VehicleID = ?
        """, vehicle_id)

        return cursor.fetchone()


def add_vehicle(vin, model, reception_date, seller_username):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dbo.VEHICLES
                (VIN, Model, ReceptionDate, SellerUsername)
            VALUES
                (?, ?, ?, ?)
        """, vin, model, reception_date, seller_username)

        conn.commit()


def set_crp(vehicle_id, crp, advisor_username):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo.VEHICLES
            SET
                CRP = ?,
                AdvisorUsername = ?
            WHERE VehicleID = ?
              AND InvoiceDate IS NULL
        """, crp, advisor_username, vehicle_id)

        conn.commit()


def set_invoice_date(vehicle_id, invoice_date):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo.VEHICLES
            SET InvoiceDate = ?
            WHERE VehicleID = ?
              AND InvoiceDate IS NULL
        """, invoice_date, vehicle_id)

        conn.commit()


def change_vehicle_assignment(vehicle_id, seller_username, advisor_username):
    with get_connection() as conn:
        cursor = conn.cursor()

        if advisor_username:
            cursor.execute("""
                UPDATE dbo.VEHICLES
                SET
                    SellerUsername = ?,
                    AdvisorUsername = ?
                WHERE VehicleID = ?
            """, seller_username, advisor_username, vehicle_id)
        else:
            cursor.execute("""
                UPDATE dbo.VEHICLES
                SET
                    SellerUsername = ?,
                    CRP = NULL,
                    AdvisorUsername = NULL
                WHERE VehicleID = ?
            """, seller_username, vehicle_id)

        conn.commit()


def get_inspections(vehicle_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                InspectionID,
                VehicleID,
                InspectionDate,
                RecordedBy,
                RecordedAt
            FROM dbo.INSPECTIONS
            WHERE VehicleID = ?
            ORDER BY InspectionDate DESC, InspectionID DESC
        """, vehicle_id)

        return cursor.fetchall()


def get_last_inspection(vehicle_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                InspectionID,
                VehicleID,
                InspectionDate,
                RecordedBy,
                RecordedAt
            FROM dbo.INSPECTIONS
            WHERE VehicleID = ?
            ORDER BY InspectionDate DESC, InspectionID DESC
        """, vehicle_id)

        return cursor.fetchone()


def add_inspection(vehicle_id, inspection_date, recorded_by):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dbo.INSPECTIONS
                (VehicleID, InspectionDate, RecordedBy)
            VALUES
                (?, ?, ?)
        """, vehicle_id, inspection_date, recorded_by)

        conn.commit()


def update_inspection(inspection_id, inspection_date):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo.INSPECTIONS
            SET InspectionDate = ?
            WHERE InspectionID = ?
        """, inspection_date, inspection_id)

        conn.commit()


def get_notification_vehicles(today):
    with get_connection() as conn:
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

                s.FullName AS SellerName,
                s.Email AS SellerEmail,
                s.ManagerEmail AS SellerManagerEmail,

                a.FullName AS AdvisorName,
                a.Email AS AdvisorEmail,
                a.ManagerEmail AS AdvisorManagerEmail,

                (
                    SELECT MAX(i.InspectionDate)
                    FROM dbo.INSPECTIONS i
                    WHERE i.VehicleID = v.VehicleID
                      AND i.InspectionDate < ?
                ) AS LastInspectionBeforeToday

            FROM dbo.VEHICLES v

            INNER JOIN dbo.CONFIG s
                ON s.Username = v.SellerUsername

            LEFT JOIN dbo.CONFIG a
                ON a.Username = v.AdvisorUsername

            WHERE v.InvoiceDate IS NULL
        """, today)

        return cursor.fetchall()


def get_config_users():
    with get_connection() as conn:
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
            FROM dbo.CONFIG
            ORDER BY FullName
        """)

        return cursor.fetchall()


def add_config_user(username, full_name, role, email, manager_email=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dbo.CONFIG
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo.CONFIG
            SET
                Username = ?,
                FullName = ?,
                Role = ?,
                Email = ?,
                ManagerEmail = ?
            WHERE ConfigID = ?
        """,
            username,
            full_name,
            role,
            email,
            manager_email,
            config_id
        )

        conn.commit()


def set_config_user_active(config_id, active):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dbo.CONFIG
            SET Active = ?
            WHERE ConfigID = ?
        """, active, config_id)

        conn.commit()

def get_advisor_manager():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1
                Username,
                FullName,
                Email
            FROM dbo.CONFIG
            WHERE Role = 'ADVISOR_MANAGER'
              AND Active = 1
        """)

        return cursor.fetchone()
