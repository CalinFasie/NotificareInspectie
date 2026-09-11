-- Run against the carsm database before using notification tracking.
IF COL_LENGTH('dbo._VEHICLES', 'LastCrpNotificationDate') IS NULL
    ALTER TABLE dbo._VEHICLES ADD LastCrpNotificationDate date NULL;

IF COL_LENGTH('dbo._VEHICLES', 'LastDay27NotificationDate') IS NULL
    ALTER TABLE dbo._VEHICLES ADD LastDay27NotificationDate date NULL;

IF COL_LENGTH('dbo._VEHICLES', 'LastOverdueNotificationDate') IS NULL
    ALTER TABLE dbo._VEHICLES ADD LastOverdueNotificationDate date NULL;
