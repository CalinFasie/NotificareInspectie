import smtplib
from datetime import date, timedelta
from email.mime.text import MIMEText

import db
from config import (
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)


def clean_recipients(recipients):
    result = []

    for email in recipients:
        if email and email not in result:
            result.append(email)

    return result


def get_crp_recipients(vehicle, advisor_manager):
    return clean_recipients([
        vehicle.SellerEmail,
        vehicle.SellerManagerEmail,
        advisor_manager.Email if advisor_manager else None,
    ])


def get_day27_recipients(vehicle, advisor_manager, active_advisors):
    if vehicle.AdvisorUsername:
        return clean_recipients([
            vehicle.SellerEmail,
            vehicle.AdvisorEmail,
            vehicle.SellerManagerEmail,
            vehicle.AdvisorManagerEmail,
        ])

    recipients = [
        vehicle.SellerEmail,
        vehicle.SellerManagerEmail,
        advisor_manager.Email if advisor_manager else None,
    ]

    recipients.extend(
        advisor.Email
        for advisor in active_advisors
    )

    return clean_recipients(recipients)


def get_day30_recipients(
    vehicle,
    advisor_manager,
    general_manager,
    active_advisors,
):
    if vehicle.AdvisorUsername:
        return clean_recipients([
            vehicle.SellerEmail,
            vehicle.AdvisorEmail,
            vehicle.SellerManagerEmail,
            vehicle.AdvisorManagerEmail,
            general_manager.Email if general_manager else None,
        ])

    recipients = [
        vehicle.SellerEmail,
        vehicle.SellerManagerEmail,
        advisor_manager.Email if advisor_manager else None,
        general_manager.Email if general_manager else None,
    ]

    recipients.extend(
        advisor.Email
        for advisor in active_advisors
    )

    return clean_recipients(recipients)


def get_inspection_cycle(vehicle, today):
    if vehicle.LastInspectionBeforeToday:
        data_start = vehicle.LastInspectionBeforeToday
    else:
        data_start = vehicle.ReceptionDate

    cycle_day = (today - data_start).days + 1
    due_date = data_start + timedelta(days=29)

    return data_start, cycle_day, due_date


def check_missing_crp(vehicle, today):
    if vehicle.CRP:
        return False

    created_date = vehicle.CreatedAt.date()
    crp_day = (today - created_date).days + 1

    return crp_day >= 6


def build_crp_email(vehicle):
    subject = f"[VehicleCheck] CRP lipsă - {vehicle.VIN}"

    body = (
        f"Vehicul: {vehicle.VIN}\n"
        f"Model: {vehicle.Model}\n"
        f"Recepție: {vehicle.ReceptionDate:%d.%m.%Y}\n"
        f"Seller: {vehicle.SellerName}\n\n"
        f"CRP nu a fost introdus în termenul de 5 zile."
    )

    return subject, body


def build_day27_email(vehicle, due_date):
    subject = f"[VehicleCheck] Verificare în 3 zile - {vehicle.VIN}"

    advisor = vehicle.AdvisorName or "NEALOCAT"

    body = (
        f"Vehicul: {vehicle.VIN}\n"
        f"Model: {vehicle.Model}\n"
        f"Recepție: {vehicle.ReceptionDate:%d.%m.%Y}\n"
        f"Seller: {vehicle.SellerName}\n"
        f"Advisor: {advisor}\n"
        f"Termen verificare: {due_date:%d.%m.%Y}\n\n"
        f"Mai sunt 3 zile până la termenul verificării tehnice."
    )

    if not vehicle.AdvisorUsername:
        body += "\n\nCRP lipsă / Consilier nealocat"

    return subject, body


def build_day30_email(vehicle, due_date, cycle_day):
    if cycle_day == 30:
        status = "Termen astăzi"
    else:
        overdue_days = cycle_day - 30

        if overdue_days == 1:
            status = "Întârziere: 1 zi"
        else:
            status = f"Întârziere: {overdue_days} zile"

    subject = f"[VehicleCheck] Verificare scadentă - {vehicle.VIN}"

    advisor = vehicle.AdvisorName or "NEALOCAT"

    body = (
        f"Vehicul: {vehicle.VIN}\n"
        f"Model: {vehicle.Model}\n"
        f"Recepție: {vehicle.ReceptionDate:%d.%m.%Y}\n"
        f"Seller: {vehicle.SellerName}\n"
        f"Advisor: {advisor}\n"
        f"Termen verificare: {due_date:%d.%m.%Y}\n"
        f"Status: {status}"
    )

    if not vehicle.AdvisorUsername:
        body += "\n\nCRP lipsă / Consilier nealocat"

    return subject, body


def send_email(recipients, subject, body):
    if not SMTP_PASSWORD:
        raise RuntimeError(
            "Parola SMTP nu este configurată."
        )

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = SMTP_USER
    message["To"] = ", ".join(recipients)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(
            SMTP_USER,
            recipients,
            message.as_string(),
        )


def run_notifications():
    today = date.today()

    vehicles = db.get_notification_vehicles(today)
    active_advisors = db.get_active_advisors()
    advisor_manager = db.get_advisor_manager()
    general_manager = db.get_general_manager()

    for vehicle in vehicles:

        if check_missing_crp(vehicle, today):
            recipients = get_crp_recipients(
                vehicle,
                advisor_manager,
            )

            subject, body = build_crp_email(vehicle)

            send_email(
                recipients,
                subject,
                body,
            )

        data_start, cycle_day, due_date = get_inspection_cycle(
            vehicle,
            today,
        )

        if cycle_day == 27:
            recipients = get_day27_recipients(
                vehicle,
                advisor_manager,
                active_advisors,
            )

            subject, body = build_day27_email(
                vehicle,
                due_date,
            )

            send_email(
                recipients,
                subject,
                body,
            )

        elif cycle_day >= 30:
            recipients = get_day30_recipients(
                vehicle,
                advisor_manager,
                general_manager,
                active_advisors,
            )

            subject, body = build_day30_email(
                vehicle,
                due_date,
                cycle_day,
            )

            send_email(
                recipients,
                subject,
                body,
            )
