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
