import argparse
import logging
import smtplib
import sys
from contextlib import nullcontext
from datetime import timedelta
from email.mime.text import MIMEText

import db
from config import (
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    app_today,
)

SMTP_TEST_SUBJECT = "[VehicleCheck TEST] SMTP verification"
SMTP_TEST_BODY = (
    "This is only a VehicleCheck SMTP connectivity test. "
    "No production notifications were processed."
)


def clean_recipients(recipients):
    result = []

    for email in recipients:
        if email:
            email = email.strip()
            if email and email.casefold() not in {item.casefold() for item in result}:
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
    recipients = clean_recipients(recipients)
    if not recipients:
        raise ValueError("Lista destinatarilor este goală.")
    if not SMTP_PASSWORD:
        raise RuntimeError(
            "Parola SMTP nu este configurată."
        )

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = SMTP_USER
    message["To"] = ", ".join(recipients)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        refused = smtp.sendmail(
            SMTP_USER,
            recipients,
            message.as_string(),
        )
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def deliver_notification(vehicle_id, notification_type, today, recipients, subject, body,
                         dry_run=False, cycle_day=None):
    if dry_run:
        cycle_day_detail = f" ZiCiclu={cycle_day}" if cycle_day is not None else ""
        logging.info("PREVIZUALIZARE VehicleID=%s Tip=%s Către=%s Subiect=%s%s",
                     vehicle_id, notification_type,
                     ", ".join(clean_recipients(recipients)), subject,
                     cycle_day_detail)
        return
    send_email(recipients, subject, body)
    db.mark_notification_sent(vehicle_id, notification_type, today)


def run_notifications(dry_run=False, notification_type=None):
    failures = 0
    with (nullcontext() if dry_run else db.notification_lock()):
        today = app_today()
        vehicles = db.get_notification_vehicles(today)
        active_advisors = db.get_active_advisors()
        advisor_manager = db.get_advisor_manager()
        general_manager = db.get_general_manager()
        for vehicle in vehicles:
            try:
                failures += process_vehicles([vehicle], today, active_advisors,
                                             advisor_manager, general_manager, dry_run=dry_run,
                                             notification_type=notification_type)
            except Exception:
                failures += 1
                logging.exception("Notificare eșuată pentru VehicleID=%s", vehicle.VehicleID)
    return failures


def process_vehicles(vehicles, today, active_advisors, advisor_manager, general_manager,
                     dry_run=False, notification_type=None):
    failures = 0
    for vehicle in vehicles:

        if notification_type in (None, "CRP"):
            try:
                if (
                    check_missing_crp(vehicle, today)
                    and vehicle.LastCrpNotificationDate != today
                ):
                    recipients = get_crp_recipients(
                        vehicle,
                        advisor_manager,
                    )

                    subject, body = build_crp_email(vehicle)

                    deliver_notification(vehicle.VehicleID, "CRP", today,
                                         recipients, subject, body, dry_run)
            except Exception:
                failures += 1
                logging.exception("Alerta CRP eșuată pentru VehicleID=%s", vehicle.VehicleID)

        cycle_start, cycle_day, due_date = get_inspection_cycle(
            vehicle,
            today,
        )

        inspection_done_today = (
            vehicle.LastInspectionDate == today
        )

        day27_sent_this_cycle = (
            vehicle.LastDay27NotificationDate is not None
            and vehicle.LastDay27NotificationDate >= cycle_start
        )

        if (
            notification_type in (None, "DAY27")
            and 27 <= cycle_day <= 29
            and not day27_sent_this_cycle
        ):
            recipients = get_day27_recipients(
                vehicle,
                advisor_manager,
                active_advisors,
            )

            subject, body = build_day27_email(
                vehicle,
                due_date,
            )

            deliver_notification(vehicle.VehicleID, "DAY27", today,
                                 recipients, subject, body, dry_run,
                                 cycle_day=cycle_day)

        elif (
            (
                notification_type in (None, "DAY30")
                and cycle_day == 30
            )
            or (
                notification_type in (None, "OVERDUE")
                and cycle_day > 30
                and not inspection_done_today
            )
        ) and vehicle.LastOverdueNotificationDate != today:
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

            deliver_notification(vehicle.VehicleID, "OVERDUE", today,
                                 recipients, subject, body, dry_run)

    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Notificări VehicleCheck")
    parser.add_argument("--type", dest="notification_type",
                        choices=("CRP", "DAY27", "DAY30", "OVERDUE"),
                        help="Procesează numai tipul de notificare selectat.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Citește SQL și afișează alertele fără emailuri sau actualizări SQL.")
    parser.add_argument("--smtp-test-recipient", metavar="EMAIL",
                        help="Trimite un singur email de test SMTP, fără procesarea notificărilor.")
    args = parser.parse_args(argv)

    if args.smtp_test_recipient is not None:
        if args.notification_type is not None or args.dry_run:
            parser.error("--smtp-test-recipient cannot be combined with --type or --dry-run")

        recipient = args.smtp_test_recipient.strip()
        if not recipient:
            parser.error("--smtp-test-recipient requires a non-empty email address")

        try:
            send_email([recipient], SMTP_TEST_SUBJECT, SMTP_TEST_BODY)
        except Exception as exc:
            logging.error(
                "SMTP connectivity test failed (%s); exception details omitted.",
                type(exc).__name__,
            )
            return 1

        logging.info("SMTP connectivity test email sent successfully.")
        return 0

    logging.info("Procesul de notificări a început.")
    logging.info("Modul de execuție: %s.", "dry-run" if args.dry_run else "normal")
    try:
        failures = run_notifications(
            dry_run=args.dry_run,
            notification_type=args.notification_type,
        )
    except Exception:
        logging.error("Procesarea notificărilor a eșuat.")
        return 1

    if failures:
        logging.error("Procesarea notificărilor s-a încheiat cu erori (%s).", failures)
        return 1

    logging.info("Procesarea notificărilor s-a încheiat cu succes.")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(main())
