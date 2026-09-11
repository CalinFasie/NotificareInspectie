-- Schema pentru o bază nouă, deja creată și selectată.
-- Nu executați peste tabele existente.
CREATE TABLE dbo._CONFIG
(
    ConfigID INT IDENTITY(1,1) NOT NULL,
    Username NVARCHAR(100) NOT NULL,
    FullName NVARCHAR(150) NOT NULL,
    Role VARCHAR(30) NOT NULL,
    Email NVARCHAR(255) NOT NULL,
    ManagerEmail NVARCHAR(255) NULL,
    Active BIT NOT NULL
        CONSTRAINT DF_CONFIG_Active DEFAULT (1),

    CONSTRAINT PK_CONFIG
        PRIMARY KEY (ConfigID),

    CONSTRAINT UQ_CONFIG_Username
        UNIQUE (Username),

    CONSTRAINT CK_CONFIG_Role
        CHECK
        (
            Role IN
            (
                'SELLER',
                'ADVISOR',
                'SELLER_MANAGER',
                'ADVISOR_MANAGER',
                'GENERAL_MANAGER',
                'ADMIN'
            )
        )
);
GO


CREATE TABLE dbo._VEHICLES
(
    VehicleID INT IDENTITY(1,1) NOT NULL,
    VIN CHAR(17) NOT NULL,
    Model NVARCHAR(100) NOT NULL,
    ReceptionDate DATE NOT NULL,
    CreatedAt DATETIME2(0) NOT NULL
        CONSTRAINT DF_VEHICLES_CreatedAt DEFAULT (SYSDATETIME()),
    SellerUsername NVARCHAR(100) NOT NULL,
    CRP NVARCHAR(50) NULL,
    AdvisorUsername NVARCHAR(100) NULL,
    InvoiceDate DATE NULL,

    CONSTRAINT PK_VEHICLES
        PRIMARY KEY (VehicleID),

    CONSTRAINT UQ_VEHICLES_VIN
        UNIQUE (VIN),

    CONSTRAINT FK_VEHICLES_Seller
        FOREIGN KEY (SellerUsername)
        REFERENCES dbo._CONFIG (Username),

    CONSTRAINT FK_VEHICLES_Advisor
        FOREIGN KEY (AdvisorUsername)
        REFERENCES dbo._CONFIG (Username),

    CONSTRAINT CK_VEHICLES_CRP_Advisor
        CHECK
        (
            (CRP IS NULL AND AdvisorUsername IS NULL)
            OR
            (CRP IS NOT NULL AND AdvisorUsername IS NOT NULL)
        ),

    CONSTRAINT CK_VEHICLES_VIN_Length
        CHECK (LEN(VIN) = 17)
);
GO


CREATE TABLE dbo._INSPECTIONS
(
    InspectionID INT IDENTITY(1,1) NOT NULL,
    VehicleID INT NOT NULL,
    InspectionDate DATE NOT NULL,
    RecordedBy NVARCHAR(100) NOT NULL,
    RecordedAt DATETIME2(0) NOT NULL
        CONSTRAINT DF_INSPECTIONS_RecordedAt DEFAULT (SYSDATETIME()),

    CONSTRAINT PK_INSPECTIONS
        PRIMARY KEY (InspectionID),

    CONSTRAINT FK_INSPECTIONS_Vehicle
        FOREIGN KEY (VehicleID)
        REFERENCES dbo._VEHICLES (VehicleID),

    CONSTRAINT FK_INSPECTIONS_RecordedBy
        FOREIGN KEY (RecordedBy)
        REFERENCES dbo._CONFIG (Username),

    CONSTRAINT UQ_INSPECTIONS_Vehicle_Date
        UNIQUE (VehicleID, InspectionDate)
);
GO

-- Evidența notificărilor păstrată în implementarea curentă.
ALTER TABLE dbo._VEHICLES ADD
    LastCrpNotificationDate date NULL,
    LastDay27NotificationDate date NULL,
    LastOverdueNotificationDate date NULL;
