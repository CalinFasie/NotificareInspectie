import getpass
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from config import app_today

import db


DATE_FORMAT = "%Y-%m-%d"

MANAGER_ROLES = {
    "SELLER_MANAGER",
    "ADVISOR_MANAGER",
    "GENERAL_MANAGER",
}


def get_windows_username():
    return getpass.getuser()


def load_current_user():
    username = get_windows_username()
    user = db.get_user_config(username)

    if user is None:
        raise PermissionError(
            f"Utilizatorul Windows '{username}' nu este configurat sau este inactiv."
        )

    return user


def is_manager(user):
    return user.Role in MANAGER_ROLES


def can_add_vehicle(user):
    return (
        user.Role == "SELLER"
        or is_manager(user)
        or user.Role == "ADMIN"
    )


def can_enter_crp(user):
    return (
        user.Role == "ADVISOR"
        or is_manager(user)
        or user.Role == "ADMIN"
    )


def can_add_inspection(user):
    return (
        user.Role == "ADVISOR"
        or is_manager(user)
        or user.Role == "ADMIN"
    )


def can_edit_inspection(user):
    return is_manager(user) or user.Role == "ADMIN"


def can_invoice(user):
    return (
        user.Role == "SELLER"
        or is_manager(user)
        or user.Role == "ADMIN"
    )


def can_manage_config(user):
    return user.Role == "ADMIN"


def parse_date(value):
    return datetime.strptime(
        value.strip(),
        DATE_FORMAT
    ).date()


def calculate_vehicle_status(vehicle, today=None):
    if today is None:
        today = app_today()

    if vehicle.InvoiceDate is not None:
        return {
            "last_inspection": None,
            "next_inspection": None,
            "countdown": "",
            "status": "CLOSED",
        }

    last_inspection = db.get_last_inspection(
        vehicle.VehicleID
    )

    if last_inspection:
        data_start = last_inspection.InspectionDate
        last_inspection_date = last_inspection.InspectionDate
    else:
        data_start = vehicle.ReceptionDate
        last_inspection_date = None

    due_date = data_start + timedelta(days=29)
    days_to_due = (due_date - today).days

    if days_to_due > 3:
        status = "NORMAL"
        countdown = f"{days_to_due} zile"

    elif days_to_due > 0:
        status = "WARNING"

        if days_to_due == 1:
            countdown = "1 zi"
        else:
            countdown = f"{days_to_due} zile"

    elif days_to_due == 0:
        status = "OVERDUE"
        countdown = "Termen astăzi"

    else:
        status = "OVERDUE"
        overdue_days = abs(days_to_due)

        if overdue_days == 1:
            countdown = "Întârziere: 1 zi"
        else:
            countdown = f"Întârziere: {overdue_days} zile"

    return {
        "last_inspection": last_inspection_date,
        "next_inspection": due_date,
        "countdown": countdown,
        "status": status,
    }


def get_crp_display(vehicle):
    if vehicle.CRP:
        return vehicle.CRP

    created_date = vehicle.CreatedAt.date()
    crp_day = (app_today() - created_date).days + 1

    if crp_day >= 6:
        return "LIPSĂ - ÎNTÂRZIAT"

    return "LIPSĂ"


class VehicleCheckApp:

    def require_permission(self, permission):
        self.user = load_current_user()
        if not permission(self.user):
            raise PermissionError("Nu mai ai dreptul să efectuezi această operație.")

    def __init__(self, root, user):
        self.root = root
        self.user = user

        self.root.title("VehicleCheck")
        self.root.geometry("1250x650")

        self.create_header()
        self.create_table()
        self.create_buttons()

        self.refresh()

    def create_header(self):
        frame = ttk.Frame(self.root)
        frame.pack(
            fill="x",
            padx=10,
            pady=10,
        )

        ttk.Label(
            frame,
            text="VehicleCheck",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ttk.Label(
            frame,
            text=f"{self.user.FullName} | {self.user.Role}",
        ).pack(side="right")

    def create_table(self):
        frame = ttk.Frame(self.root)
        frame.pack(
            fill="both",
            expand=True,
            padx=10,
        )

        columns = (
            "VIN",
            "Model",
            "Reception",
            "Seller",
            "CRP",
            "Advisor",
            "LastInspection",
            "NextInspection",
            "Countdown",
            "Status",
        )

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "VIN": "VIN",
            "Model": "Model",
            "Reception": "Recepție",
            "Seller": "Seller",
            "CRP": "CRP",
            "Advisor": "Advisor",
            "LastInspection": "Ultima verificare",
            "NextInspection": "Următoarea verificare",
            "Countdown": "Countdown",
            "Status": "Status",
        }

        widths = {
            "VIN": 150,
            "Model": 120,
            "Reception": 90,
            "Seller": 100,
            "CRP": 130,
            "Advisor": 100,
            "LastInspection": 110,
            "NextInspection": 120,
            "Countdown": 130,
            "Status": 90,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )

            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview,
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

    def create_buttons(self):
        frame = ttk.Frame(self.root)
        frame.pack(
            fill="x",
            padx=10,
            pady=10,
        )

        self.btn_add = ttk.Button(
            frame,
            text="Adaugă vehicul",
            command=self.add_vehicle_dialog,
        )

        self.btn_crp = ttk.Button(
            frame,
            text="Introdu CRP",
            command=self.crp_dialog,
        )

        self.btn_inspection = ttk.Button(
            frame,
            text="Adaugă verificare",
            command=self.inspection_dialog,
        )

        self.btn_invoice = ttk.Button(
            frame,
            text="Facturează",
            command=self.invoice_dialog,
        )

        self.btn_history = ttk.Button(
            frame,
            text="Istoric verificări",
            command=self.history_dialog,
        )

        self.btn_refresh = ttk.Button(
            frame,
            text="Refresh",
            command=self.refresh,
        )

        buttons = [
            self.btn_add,
            self.btn_crp,
            self.btn_inspection,
            self.btn_invoice,
            self.btn_history,
            self.btn_refresh,
        ]

        for button in buttons:
            button.pack(
                side="left",
                padx=4,
            )

        if not can_add_vehicle(self.user):
            self.btn_add.configure(state="disabled")

        if not can_enter_crp(self.user):
            self.btn_crp.configure(state="disabled")

        if not can_add_inspection(self.user):
            self.btn_inspection.configure(state="disabled")

        if not can_invoice(self.user):
            self.btn_invoice.configure(state="disabled")

        if can_manage_config(self.user):
            ttk.Button(
                frame,
                text="Configurare",
                command=self.config_dialog,
            ).pack(
                side="right",
                padx=4,
            )

    def selected_vehicle_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "VehicleCheck",
                "Selectează un vehicul.",
            )
            return None

        return int(selection[0])

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            vehicles = db.get_active_vehicles()

            for vehicle in vehicles:
                status = calculate_vehicle_status(
                    vehicle
                )

                last_inspection = (
                    status["last_inspection"].strftime(
                        DATE_FORMAT
                    )
                    if status["last_inspection"]
                    else ""
                )

                next_inspection = (
                    status["next_inspection"].strftime(
                        DATE_FORMAT
                    )
                    if status["next_inspection"]
                    else ""
                )

                self.tree.insert(
                    "",
                    "end",
                    iid=str(vehicle.VehicleID),
                    values=(
                        vehicle.VIN,
                        vehicle.Model,
                        vehicle.ReceptionDate.strftime(
                            DATE_FORMAT
                        ),
                        vehicle.SellerUsername,
                        get_crp_display(vehicle),
                        vehicle.AdvisorUsername or "",
                        last_inspection,
                        next_inspection,
                        status["countdown"],
                        status["status"],
                    ),
                )

        except Exception as exc:
            messagebox.showerror(
                "Eroare",
                str(exc),
            )

    def add_vehicle_dialog(self):
        window = tk.Toplevel(self.root)
        window.title("Adaugă vehicul")
        window.resizable(False, False)

        ttk.Label(window, text="VIN").grid(
            row=0,
            column=0,
            padx=10,
            pady=8,
            sticky="w",
        )

        vin_entry = ttk.Entry(
            window,
            width=30,
        )
        vin_entry.grid(
            row=0,
            column=1,
            padx=10,
            pady=8,
        )

        ttk.Label(window, text="Model").grid(
            row=1,
            column=0,
            padx=10,
            pady=8,
            sticky="w",
        )

        model_entry = ttk.Entry(
            window,
            width=30,
        )
        model_entry.grid(
            row=1,
            column=1,
            padx=10,
            pady=8,
        )

        ttk.Label(
            window,
            text="ReceptionDate",
        ).grid(
            row=2,
            column=0,
            padx=10,
            pady=8,
            sticky="w",
        )

        reception_entry = ttk.Entry(
            window,
            width=30,
        )

        reception_entry.insert(
            0,
            app_today().strftime(DATE_FORMAT),
        )

        reception_entry.grid(
            row=2,
            column=1,
            padx=10,
            pady=8,
        )

        def save():
            try:
                vin = vin_entry.get().strip().upper()
                self.require_permission(can_add_vehicle)
                model = model_entry.get().strip()

                if len(vin) != 17:
                    raise ValueError(
                        "VIN trebuie să aibă 17 caractere."
                    )

                if not model:
                    raise ValueError(
                        "Modelul este obligatoriu."
                    )

                reception_date = parse_date(
                    reception_entry.get()
                )

                db.add_vehicle(
                    vin,
                    model,
                    reception_date,
                    self.user.Username,
                )

                window.destroy()
                self.refresh()

            except Exception as exc:
                messagebox.showerror(
                    "Eroare",
                    str(exc),
                    parent=window,
                )

        ttk.Button(
            window,
            text="Salvează",
            command=save,
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            pady=12,
        )

    def crp_dialog(self):
        vehicle_id = self.selected_vehicle_id()

        if vehicle_id is None:
            return

        vehicle = db.get_vehicle(vehicle_id)

        if vehicle.CRP:
            messagebox.showinfo(
                "VehicleCheck",
                "Vehiculul are deja CRP.",
            )
            return

        window = tk.Toplevel(self.root)
        window.title("Introdu CRP")
        window.resizable(False, False)

        ttk.Label(window, text="CRP").grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
        )

        crp_entry = ttk.Entry(
            window,
            width=30,
        )

        crp_entry.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
        )

        advisor_map = {}
        advisor_combo = None

        if self.user.Role != "ADVISOR":
            advisors = db.get_active_advisors()

            for advisor in advisors:
                advisor_map[
                    f"{advisor.FullName} ({advisor.Username})"
                ] = advisor.Username

            ttk.Label(
                window,
                text="Advisor",
            ).grid(
                row=1,
                column=0,
                padx=10,
                pady=10,
            )

            advisor_combo = ttk.Combobox(
                window,
                values=list(advisor_map.keys()),
                state="readonly",
                width=27,
            )

            advisor_combo.grid(
                row=1,
                column=1,
                padx=10,
                pady=10,
            )

        def save():
            try:
                crp = crp_entry.get().strip()
                self.require_permission(can_enter_crp)

                if not crp:
                    raise ValueError(
                        "CRP este obligatoriu."
                    )

                if self.user.Role == "ADVISOR":
                    selected_advisor = self.user.Username
                else:
                    if advisor_combo is None:
                        raise ValueError("Rolul s-a schimbat. Redeschide formularul CRP pentru a selecta Advisor.")
                    advisor_name = advisor_combo.get()

                    if not advisor_name:
                        raise ValueError(
                            "Selectează Advisor."
                        )

                    selected_advisor = advisor_map[
                        advisor_name
                    ]

                db.set_crp(
                    vehicle_id,
                    crp,
                    selected_advisor,
                )

                window.destroy()
                self.refresh()

            except Exception as exc:
                messagebox.showerror(
                    "Eroare",
                    str(exc),
                    parent=window,
                )

        ttk.Button(
            window,
            text="Salvează",
            command=save,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            pady=12,
        )

    def inspection_dialog(self):
        vehicle_id = self.selected_vehicle_id()

        if vehicle_id is None:
            return

        window = tk.Toplevel(self.root)
        window.title("Adaugă verificare")
        window.resizable(False, False)

        ttk.Label(
            window,
            text="Data verificării",
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
        )

        date_entry = ttk.Entry(
            window,
            width=20,
        )

        date_entry.insert(
            0,
            app_today().strftime(DATE_FORMAT),
        )

        date_entry.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
        )

        if self.user.Role == "ADVISOR":
            date_entry.configure(
                state="disabled"
            )

        def save():
            try:
                self.require_permission(can_add_inspection)
                if self.user.Role == "ADVISOR":
                    inspection_date = app_today()
                else:
                    inspection_date = parse_date(
                        date_entry.get()
                    )

                    if inspection_date > app_today():
                        raise ValueError(
                            "Data verificării nu poate fi în viitor."
                        )

                db.add_inspection(
                    vehicle_id,
                    inspection_date,
                    self.user.Username,
                )

                window.destroy()
                self.refresh()

            except Exception as exc:
                messagebox.showerror(
                    "Eroare",
                    str(exc),
                    parent=window,
                )

        ttk.Button(
            window,
            text="Salvează",
            command=save,
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            pady=12,
        )

    def invoice_dialog(self):
        vehicle_id = self.selected_vehicle_id()

        if vehicle_id is None:
            return

        window = tk.Toplevel(self.root)
        window.title("Facturare")
        window.resizable(False, False)

        ttk.Label(
            window,
            text="InvoiceDate",
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
        )

        date_entry = ttk.Entry(
            window,
            width=20,
        )

        date_entry.insert(
            0,
            app_today().strftime(DATE_FORMAT),
        )

        date_entry.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
        )

        def save():
            try:
                self.require_permission(can_invoice)
                invoice_date = parse_date(
                    date_entry.get()
                )

                db.set_invoice_date(
                    vehicle_id,
                    invoice_date,
                )

                window.destroy()
                self.refresh()

            except Exception as exc:
                messagebox.showerror(
                    "Eroare",
                    str(exc),
                    parent=window,
                )

        ttk.Button(
            window,
            text="Facturează",
            command=save,
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            pady=12,
        )

    def history_dialog(self):
        vehicle_id = self.selected_vehicle_id()

        if vehicle_id is None:
            return

        window = tk.Toplevel(self.root)
        window.title("Istoric verificări")
        window.geometry("650x400")

        tree = ttk.Treeview(
            window,
            columns=(
                "ID",
                "Date",
                "RecordedBy",
                "RecordedAt",
            ),
            show="headings",
        )

        tree.heading("ID", text="ID")
        tree.heading("Date", text="Data")
        tree.heading(
            "RecordedBy",
            text="Înregistrat de",
        )
        tree.heading(
            "RecordedAt",
            text="Înregistrat la",
        )

        tree.column("ID", width=60)
        tree.column("Date", width=120)
        tree.column("RecordedBy", width=150)
        tree.column("RecordedAt", width=180)

        tree.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10,
        )

        def load_history():
            for item in tree.get_children():
                tree.delete(item)

            inspections = db.get_inspections(
                vehicle_id
            )

            for inspection in inspections:
                tree.insert(
                    "",
                    "end",
                    iid=str(
                        inspection.InspectionID
                    ),
                    values=(
                        inspection.InspectionID,
                        inspection.InspectionDate.strftime(
                            DATE_FORMAT
                        ),
                        inspection.RecordedBy,
                        inspection.RecordedAt.strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    ),
                )

        def edit():
            selection = tree.selection()

            if not selection:
                messagebox.showwarning(
                    "VehicleCheck",
                    "Selectează o verificare.",
                    parent=window,
                )
                return

            inspection_id = int(selection[0])

            current_values = tree.item(
                selection[0],
                "values",
            )

            edit_window = tk.Toplevel(window)
            edit_window.title(
                "Modifică verificare"
            )

            ttk.Label(
                edit_window,
                text="Data verificării",
            ).grid(
                row=0,
                column=0,
                padx=10,
                pady=10,
            )

            entry = ttk.Entry(
                edit_window,
                width=20,
            )

            entry.insert(
                0,
                current_values[1],
            )

            entry.grid(
                row=0,
                column=1,
                padx=10,
                pady=10,
            )

            def save_edit():
                try:
                    self.require_permission(can_edit_inspection)
                    new_date = parse_date(
                        entry.get()
                    )

                    if new_date > app_today():
                        raise ValueError(
                            "Data verificării nu poate fi în viitor."
                        )

                    db.update_inspection(
                        inspection_id,
                        new_date,
                    )

                    edit_window.destroy()
                    load_history()
                    self.refresh()

                except Exception as exc:
                    messagebox.showerror(
                        "Eroare",
                        str(exc),
                        parent=edit_window,
                    )

            ttk.Button(
                edit_window,
                text="Salvează",
                command=save_edit,
            ).grid(
                row=1,
                column=0,
                columnspan=2,
                pady=10,
            )

        load_history()

        if can_edit_inspection(self.user):
            ttk.Button(
                window,
                text="Modifică verificarea",
                command=edit,
            ).pack(pady=5)

    def config_dialog(self):
        try:
            self.require_permission(can_manage_config)
        except Exception as exc:
            messagebox.showerror("Acces refuzat", str(exc))
            return

        window = tk.Toplevel(self.root)
        window.title("Configurare utilizatori")
        fields = ("Username", "FullName", "Role", "Email", "ManagerEmail")
        roles = ("SELLER", "ADVISOR", "SELLER_MANAGER", "ADVISOR_MANAGER",
                 "GENERAL_MANAGER", "ADMIN")
        tree = ttk.Treeview(window, columns=fields + ("Active",), show="headings", height=10)
        for field in fields + ("Active",):
            tree.heading(field, text=field)
            tree.column(field, width=140)
        tree.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        values = {field: tk.StringVar() for field in fields}
        selected = {"id": None}
        users = {}
        entries = {}
        for row, field in enumerate(fields, start=1):
            ttk.Label(window, text=field).grid(row=row, column=0, sticky="e")
            if field == "Role":
                entry = ttk.Combobox(window, textvariable=values[field],
                                     values=roles, state="readonly")
            else:
                entry = ttk.Entry(window, textvariable=values[field], width=40)
            entry.grid(row=row, column=1, padx=8, pady=4, sticky="w")
            entries[field] = entry

        def refresh():
            rows = db.get_config_users()
            users.clear()
            for item in tree.get_children():
                tree.delete(item)
            for user in rows:
                users[str(user.ConfigID)] = user
                tree.insert("", "end", iid=str(user.ConfigID),
                            values=tuple(getattr(user, field) or "" for field in fields)
                            + ("Da" if user.Active else "Nu",))

        def select(_event):
            selection = tree.selection()
            if selection:
                user = users[selection[0]]
                selected["id"] = user.ConfigID
                for field in fields:
                    values[field].set(getattr(user, field) or "")
                entries["Username"].configure(state="readonly")

        def new():
            selected["id"] = None
            entries["Username"].configure(state="normal")
            tree.selection_remove(*tree.selection())
            for value in values.values():
                value.set("")

        def save():
            try:
                self.require_permission(can_manage_config)
                data = [values[field].get().strip() for field in fields]
                if not all(data[:4]) or data[2] not in roles:
                    raise ValueError("Completează Username, FullName, Role și Email.")
                for email in (data[3], data[4]):
                    if email and ("@" not in email or any(c.isspace() for c in email)):
                        raise ValueError("Adresă email invalidă.")
                if any(u.Username.casefold() == data[0].casefold()
                       and u.ConfigID != selected["id"] for u in users.values()):
                    raise ValueError("Username există deja.")
                if selected["id"] is None:
                    db.add_config_user(*data)
                else:
                    current = users[str(selected["id"])]
                    if current.Username == self.user.Username and (
                        data[0] != current.Username or data[2] != "ADMIN"
                    ):
                        raise ValueError("Nu poți schimba propriul username sau rol în sesiunea curentă.")
                    db.update_config_user(selected["id"], *data)
                refresh()
                new()
            except Exception as exc:
                messagebox.showerror("Eroare", str(exc), parent=window)

        def toggle_active():
            if selected["id"] is None:
                return
            try:
                self.require_permission(can_manage_config)
                current = users[str(selected["id"])]
                if current.Username == self.user.Username:
                    raise ValueError("Nu poți dezactiva propriul cont.")
                db.set_config_user_active(current.ConfigID, not current.Active)
                refresh()
                new()
            except Exception as exc:
                messagebox.showerror("Eroare", str(exc), parent=window)

        tree.bind("<<TreeviewSelect>>", select)
        ttk.Button(window, text="Utilizator nou", command=new).grid(row=6, column=0, pady=10)
        ttk.Button(window, text="Salvează", command=save).grid(row=6, column=1, pady=10)
        ttk.Button(window, text="Activează / Dezactivează", command=toggle_active).grid(row=6, column=2)
        try:
            refresh()
        except Exception as exc:
            messagebox.showerror("Eroare", str(exc), parent=window)
            window.destroy()


def main():
    root = tk.Tk()

    try:
        user = load_current_user()

    except Exception as exc:
        root.withdraw()

        messagebox.showerror(
            "VehicleCheck",
            str(exc),
        )

        root.destroy()
        return

    VehicleCheckApp(
        root,
        user,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
