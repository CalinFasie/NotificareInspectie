import getpass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import db

LOCAL_TIMEZONE = ZoneInfo("Europe/Bucharest")

MANAGER_ROLES = {
    "SELLER_MANAGER",
    "ADVISOR_MANAGER",
    "GENERAL_MANAGER",
}

VALID_ROLES = {
    "SELLER",
    "ADVISOR",
    "SELLER_MANAGER",
    "ADVISOR_MANAGER",
    "GENERAL_MANAGER",
    "ADMIN",
}


def get_windows_username():
    return getpass.getuser()


def get_today():
    return datetime.now(LOCAL_TIMEZONE).date()


def load_current_user():
    username = get_windows_username()
    user = db.get_user_config(username)

    if user is None:
        raise PermissionError(
            f"Utilizatorul Windows '{username}' nu este configurat sau este inactiv."
        )

    if user.Role not in VALID_ROLES:
        raise PermissionError(
            f"Rol invalid pentru utilizatorul '{username}'."
        )

    return user


def is_manager(user):
    return user.Role in MANAGER_ROLES


def can_add_vehicle(user):
    return user.Role == "SELLER" or is_manager(user) or user.Role == "ADMIN"


def can_enter_crp(user):
    return user.Role == "ADVISOR" or is_manager(user) or user.Role == "ADMIN"


def can_add_inspection(user):
    return user.Role == "ADVISOR" or is_manager(user) or user.Role == "ADMIN"


def can_add_retroactive_inspection(user):
    return is_manager(user) or user.Role == "ADMIN"


def can_edit_inspection(user):
    return is_manager(user) or user.Role == "ADMIN"


def can_invoice(user):
    return user.Role == "SELLER" or is_manager(user) or user.Role == "ADMIN"


def can_manage_config(user):
    return user.Role == "ADMIN"


def can_change_assignment(user):
    return user.Role == "ADMIN"


def get_inspection_data_start(vehicle):
    last_inspection = db.get_last_inspection(vehicle.VehicleID)

    if last_inspection:
        return last_inspection.InspectionDate

    return vehicle.ReceptionDate


def calculate_vehicle_status(vehicle, today=None):
    if today is None:
        today = get_today()

    if vehicle.InvoiceDate is not None:
        return {
            "data_start": None,
            "last_inspection": None,
            "next_inspection": None,
            "cycle_day": None,
            "countdown": "",
            "status": "CLOSED",
        }

    last_inspection = db.get_last_inspection(vehicle.VehicleID)

    if last_inspection:
        data_start = last_inspection.InspectionDate
        last_inspection_date = last_inspection.InspectionDate
    else:
        data_start = vehicle.ReceptionDate
        last_inspection_date = None

    cycle_day = (today - data_start).days + 1
    next_inspection = data_start + timedelta(days=29)

    if cycle_day <= 29:
        days_remaining = (next_inspection - today).days

        if days_remaining == 0:
            countdown = "Termen astăzi"
        else:
            countdown = f"{days_remaining} zile"

        if cycle_day >= 27:
            status = "WARNING"
        else:
            status = "NORMAL"

    elif cycle_day == 30:
        countdown = "Termen astăzi"
        status = "OVERDUE"

    else:
        overdue_days = cycle_day - 30
        countdown = f"Întârziere: {overdue_days} zi"

        if overdue_days != 1:
            countdown = f"Întârziere: {overdue_days} zile"

        status = "OVERDUE"

    return {
        "data_start": data_start,
        "last_inspection": last_inspection_date,
        "next_inspection": next_inspection,
        "cycle_day": cycle_day,
        "countdown": countdown,
        "status": status,
    }


def get_crp_display(vehicle, today=None):
    if today is None:
        today = get_today()

    if vehicle.CRP:
        return vehicle.CRP

    created_date = vehicle.CreatedAt.date()
    crp_day = (today - created_date).days + 1

    if crp_day >= 6:
        return "LIPSĂ - ÎNTÂRZIAT"

    return "LIPSĂ"


def load_main_table():
    vehicles = db.get_active_vehicles()
    rows = []

    for vehicle in vehicles:
        inspection_status = calculate_vehicle_status(vehicle)

        rows.append({
            "VehicleID": vehicle.VehicleID,
            "VIN": vehicle.VIN,
            "Model": vehicle.Model,
            "ReceptionDate": vehicle.ReceptionDate,
            "Seller": vehicle.SellerUsername,
            "CRP": get_crp_display(vehicle),
            "Advisor": vehicle.AdvisorUsername or "",
            "LastInspection": inspection_status["last_inspection"],
            "NextInspection": inspection_status["next_inspection"],
            "Countdown": inspection_status["countdown"],
            "Status": inspection_status["status"],
        })

    return rows


def add_vehicle(user, vin, model, reception_date):
    if not can_add_vehicle(user):
        raise PermissionError("Nu ai dreptul să adaugi vehicule.")

    db.add_vehicle(
        vin=vin.strip().upper(),
        model=model.strip(),
        reception_date=reception_date,
        seller_username=user.Username,
    )


def enter_crp(user, vehicle_id, crp):
    if not can_enter_crp(user):
        raise PermissionError("Nu ai dreptul să introduci CRP.")

    db.set_crp(
        vehicle_id=vehicle_id,
        crp=crp.strip(),
        advisor_username=user.Username,
    )


def add_inspection(user, vehicle_id, inspection_date=None):
    if not can_add_inspection(user):
        raise PermissionError("Nu ai dreptul să introduci verificări.")

    if inspection_date is None:
        inspection_date = get_today()

    if user.Role == "ADVISOR" and inspection_date != get_today():
        raise PermissionError(
            "Advisor poate introduce doar verificarea cu data curentă."
        )

    if inspection_date != get_today() and not can_add_retroactive_inspection(user):
        raise PermissionError(
            "Nu ai dreptul să introduci verificări retroactive."
        )

    db.add_inspection(
        vehicle_id=vehicle_id,
        inspection_date=inspection_date,
        recorded_by=user.Username,
    )


def edit_inspection(user, inspection_id, inspection_date):
    if not can_edit_inspection(user):
        raise PermissionError("Nu ai dreptul să modifici verificări.")

    db.update_inspection(
        inspection_id=inspection_id,
        inspection_date=inspection_date,
    )


def invoice_vehicle(user, vehicle_id, invoice_date=None):
    if not can_invoice(user):
        raise PermissionError("Nu ai dreptul să facturezi vehiculul.")

    if invoice_date is None:
        invoice_date = get_today()

    db.set_invoice_date(
        vehicle_id=vehicle_id,
        invoice_date=invoice_date,
    )
