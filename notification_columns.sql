-- Run against the VehicleCheck database before using notification tracking.
IF COL_LENGTH('dbo.VEHICLES', 'LastCrpNotificationDate') IS NULL
    ALTER TABLE dbo.VEHICLES ADD LastCrpNotificationDate date NULL;

IF COL_LENGTH('dbo.VEHICLES', 'LastDay27NotificationDate') IS NULL
    ALTER TABLE dbo.VEHICLES ADD LastDay27NotificationDate date NULL;

IF COL_LENGTH('dbo.VEHICLES', 'LastOverdueNotificationDate') IS NULL
    ALTER TABLE dbo.VEHICLES ADD LastOverdueNotificationDate date NULL;
