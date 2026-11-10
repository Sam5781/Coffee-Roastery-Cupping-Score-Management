"""
Coffee Roastery & Cupping Score Management Dashboard
-----------------------------------------------------
A single-file Python desktop application using Tkinter and SQLite.

Run:
    python coffee_roastery.py

The SQLite database (coffee_roastery.db) is created automatically in the
same folder as this script. Sample data is inserted only when all three
tables are empty.

Note:
    Tkinter requires a desktop environment. Standard hosted Google Colab
    sessions do not support normal desktop Tkinter windows.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import date


# Keep the database beside this Python script, regardless of the
# directory from which the script is launched.
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "coffee_roastery.db"


# ----------------------------- DATABASE -----------------------------

def get_connection():
    """Open a SQLite connection and explicitly enable foreign keys."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the relational schema and seed it only if completely empty."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roasteries (
                roastery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                roastery_name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                contact_email TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS roast_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                roastery_id INTEGER NOT NULL,
                bean_origin TEXT NOT NULL,
                roast_date TEXT NOT NULL,
                FOREIGN KEY (roastery_id)
                    REFERENCES roasteries(roastery_id)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cupping_scores (
                score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                score_type TEXT NOT NULL,
                score_value REAL NOT NULL CHECK (score_value >= 0),
                FOREIGN KEY (batch_id)
                    REFERENCES roast_batches(batch_id)
                    ON DELETE CASCADE
            )
        """)

        # Seed only when every table has zero records.
        counts = []
        for table in ("roasteries", "roast_batches", "cupping_scores"):
            counts.append(conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0])

        if sum(counts) == 0:
            conn.execute(
                "INSERT INTO roasteries (roastery_name, contact_email) VALUES (?, ?)",
                ("Highland Coffee Works", "hello@highlandcoffee.example")
            )
            conn.execute(
                "INSERT INTO roasteries (roastery_name, contact_email) VALUES (?, ?)",
                ("Bean & Bloom Roasters", "roast@beanandbloom.example")
            )

            conn.execute("""
                INSERT INTO roast_batches (roastery_id, bean_origin, roast_date)
                VALUES
                    (1, 'Ethiopia Yirgacheffe', '2026-10-20'),
                    (1, 'Colombia Huila', '2026-10-22'),
                    (2, 'Brazil Cerrado', '2026-10-24')
            """)

            conn.execute("""
                INSERT INTO cupping_scores (batch_id, score_type, score_value)
                VALUES
                    (1, 'Aroma', 8.7),
                    (1, 'Acidity', 8.4),
                    (1, 'Body', 8.2),
                    (2, 'Aroma', 8.5),
                    (2, 'Acidity', 8.1),
                    (3, 'Body', 8.0)
            """)


def insert_roast_record(roastery_name, contact_email, bean_origin,
                        score_type, score_value):
    """Insert or reuse a roastery, then create one batch and one score."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT roastery_id FROM roasteries WHERE roastery_name = ?",
            (roastery_name,)
        ).fetchone()

        if row:
            roastery_id = row[0]
        else:
            cursor = conn.execute(
                """INSERT INTO roasteries (roastery_name, contact_email)
                   VALUES (?, ?)""",
                (roastery_name, contact_email)
            )
            roastery_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO roast_batches (roastery_id, bean_origin, roast_date)
               VALUES (?, ?, ?)""",
            (roastery_id, bean_origin, date.today().isoformat())
        )
        batch_id = cursor.lastrowid

        conn.execute(
            """INSERT INTO cupping_scores (batch_id, score_type, score_value)
               VALUES (?, ?, ?)""",
            (batch_id, score_type, score_value)
        )

    return batch_id


def delete_record(table, record_id):
    """Delete one selected record; SQLite handles cascading child deletes."""
    allowed_tables = {
        "roasteries": "roastery_id",
        "roast_batches": "batch_id",
        "cupping_scores": "score_id",
    }
    if table not in allowed_tables:
        raise ValueError("Invalid table selected.")

    primary_key = allowed_tables[table]
    with get_connection() as conn:
        cursor = conn.execute(
            f"DELETE FROM {table} WHERE {primary_key} = ?",
            (record_id,)
        )
        if cursor.rowcount == 0:
            raise ValueError("That record no longer exists. Please refresh the list.")


def fetch_all(query, params=()):
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


# ----------------------------- GUI APP ------------------------------

class CoffeeRoasteryApp:
    BG = "#F4F0E6"
    PANEL = "#FFFDF7"
    GREEN = "#234B3B"
    GREEN_DARK = "#183629"
    GREEN_LIGHT = "#DCE8DD"
    BROWN = "#8A5A3B"
    TEXT = "#25352C"
    MUTED = "#68756C"
    RED = "#A33A32"

    def __init__(self, root):
        self.root = root
        self.root.title("Coffee Roastery | Cupping Score Manager")
        self.root.geometry("1180x780")
        self.root.minsize(980, 680)
        self.root.configure(bg=self.BG)

        self._configure_style()
        self._build_header()
        self._build_main_content()
        self.refresh_all()

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=self.TEXT,
            fieldbackground="#FFFFFF",
            rowheight=29,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background=self.GREEN,
            foreground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padding=(8, 9)
        )
        style.map(
            "Treeview",
            background=[("selected", "#C8DCCB")],
            foreground=[("selected", self.GREEN_DARK)]
        )
        style.configure(
            "TNotebook",
            background=self.BG,
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background="#E4E0D5",
            foreground=self.TEXT,
            padding=(18, 10),
            font=("Segoe UI", 9, "bold")
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.GREEN)],
            foreground=[("selected", "#FFFFFF")]
        )
        style.configure(
            "TCombobox",
            padding=7,
            fieldbackground="#FFFFFF"
        )

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.GREEN, padx=28, pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="☕  COFFEE ROASTERY",
            bg=self.GREEN,
            fg="#F7F1E5",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")

        tk.Label(
            header,
            text="ROAST TRACKING  /  CUPPING SCORE MANAGEMENT",
            bg=self.GREEN,
            fg="#D8E4D8",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(5, 0))

    def _build_main_content(self):
        content = tk.Frame(self.root, bg=self.BG, padx=24, pady=18)
        content.pack(fill="both", expand=True)

        intro = tk.Frame(content, bg=self.BG)
        intro.pack(fill="x", pady=(0, 13))

        tk.Label(
            intro,
            text="Roastery Management Dashboard",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w")

        tk.Label(
            intro,
            text="Create roast records, manage database entries and inspect live table data.",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(3, 0))

        self.notebook = ttk.Notebook(content)
        self.notebook.pack(fill="both", expand=True)

        self.insert_tab = tk.Frame(self.notebook, bg=self.BG, padx=18, pady=18)
        self.delete_tab = tk.Frame(self.notebook, bg=self.BG, padx=18, pady=18)
        self.data_tab = tk.Frame(self.notebook, bg=self.BG, padx=12, pady=12)

        self.notebook.add(self.insert_tab, text="  ADD ROAST RECORD  ")
        self.notebook.add(self.delete_tab, text="  DELETE RECORDS  ")
        self.notebook.add(self.data_tab, text="  DATABASE TABLES  ")

        self._build_insert_panel()
        self._build_delete_panel()
        self._build_data_panel()

        footer = tk.Frame(content, bg=self.BG)
        footer.pack(fill="x", pady=(10, 0))
        self.status_var = tk.StringVar(value="Database connected.")
        tk.Label(
            footer,
            textvariable=self.status_var,
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 8)
        ).pack(side="left")

        tk.Label(
            footer,
            text=f"SQLite database: {DB_PATH.name}",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 8)
        ).pack(side="right")

    def _section_heading(self, parent, title, subtitle):
        tk.Label(
            parent, text=title, bg=self.BG, fg=self.GREEN_DARK,
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")
        tk.Label(
            parent, text=subtitle, bg=self.BG, fg=self.MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(3, 14))

    def _make_field(self, parent, label, variable, row, column,
                    width=34, show=None):
        holder = tk.Frame(parent, bg=self.PANEL)
        holder.grid(row=row, column=column, sticky="ew", padx=10, pady=9)

        tk.Label(
            holder, text=label, bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))

        entry = tk.Entry(
            holder, textvariable=variable, width=width,
            font=("Segoe UI", 10), relief="solid", bd=1,
            highlightthickness=1, highlightbackground="#DDD8CB",
            highlightcolor=self.GREEN, show=show
        )
        entry.pack(fill="x", ipady=8)
        return entry

    def _build_insert_panel(self):
        self._section_heading(
            self.insert_tab,
            "Add a new roast record",
            "A submission creates one roast batch and one cupping score."
        )

        card = tk.Frame(
            self.insert_tab, bg=self.PANEL, padx=18, pady=16,
            highlightthickness=1, highlightbackground="#E2DDCF"
        )
        card.pack(fill="x", anchor="n")

        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        self.roastery_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.origin_var = tk.StringVar()
        self.score_type_var = tk.StringVar(value="Aroma")
        self.score_value_var = tk.StringVar()

        self._make_field(card, "ROASTERY NAME *", self.roastery_var, 0, 0)
        self._make_field(card, "CONTACT EMAIL (required for a new roastery) *",
                         self.email_var, 0, 1)
        self._make_field(card, "BEAN ORIGIN *", self.origin_var, 1, 0)

        score_holder = tk.Frame(card, bg=self.PANEL)
        score_holder.grid(row=1, column=1, sticky="ew", padx=10, pady=9)
        tk.Label(
            score_holder, text="SCORE TYPE *", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))
        self.score_type_combo = ttk.Combobox(
            score_holder, textvariable=self.score_type_var,
            values=("Aroma", "Acidity", "Body", "Flavor", "Aftertaste",
                    "Balance", "Overall"),
            state="normal", font=("Segoe UI", 10)
        )
        self.score_type_combo.pack(fill="x", ipady=5)

        self._make_field(card, "SCORE VALUE * (numeric, zero or greater)",
                         self.score_value_var, 2, 0)

        note = tk.Label(
            card,
            text="Tip: If the roastery already exists, its saved contact email is retained.",
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8)
        )
        note.grid(row=2, column=1, sticky="w", padx=10, pady=9)

        actions = tk.Frame(self.insert_tab, bg=self.BG)
        actions.pack(fill="x", pady=15)

        tk.Button(
            actions, text="＋  ADD RECORD", command=self.add_record,
            bg=self.GREEN, fg="white", activebackground=self.GREEN_DARK,
            activeforeground="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=22, pady=11
        ).pack(side="left")

        tk.Button(
            actions, text="CLEAR FORM", command=self.clear_insert_form,
            bg="#E5E0D4", fg=self.TEXT, activebackground="#D8D1C2",
            relief="flat", cursor="hand2", font=("Segoe UI", 9, "bold"),
            padx=18, pady=11
        ).pack(side="left", padx=10)

        tk.Label(
            self.insert_tab,
            text="* Required fields. Roast date is recorded automatically as today's date.",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8)
        ).pack(anchor="w")

    def clear_insert_form(self):
        self.roastery_var.set("")
        self.email_var.set("")
        self.origin_var.set("")
        self.score_type_var.set("Aroma")
        self.score_value_var.set("")

    def add_record(self):
        name = self.roastery_var.get().strip()
        email = self.email_var.get().strip()
        origin = self.origin_var.get().strip()
        score_type = self.score_type_var.get().strip()
        score_text = self.score_value_var.get().strip()

        if not all((name, origin, score_type, score_text)):
            messagebox.showwarning(
                "Missing information",
                "Please complete all required fields."
            )
            return

        if "@" not in email or "." not in email.split("@")[-1]:
            # A contact email is required for a new roastery. For an existing
            # roastery, the stored email is used and this field can be blank.
            existing = fetch_all(
                "SELECT roastery_id FROM roasteries WHERE roastery_name = ?",
                (name,)
            )
            if not existing:
                messagebox.showwarning(
                    "Contact email required",
                    "Enter a valid contact email for a new roastery."
                )
                return

        try:
            score_value = float(score_text)
        except ValueError:
            messagebox.showwarning(
                "Invalid score",
                "Score value must be a number, such as 8.5."
            )
            return

        if score_value < 0:
            messagebox.showwarning(
                "Invalid score",
                "Score value cannot be negative."
            )
            return

        try:
            batch_id = insert_roast_record(
                name, email, origin, score_type, score_value
            )
            self.clear_insert_form()
            self.refresh_all()
            self.status_var.set(f"New roast batch #{batch_id} added successfully.")
            messagebox.showinfo(
                "Record added",
                f"Roast batch #{batch_id} and its cupping score were saved."
            )
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))

    def _build_delete_panel(self):
        self._section_heading(
            self.delete_tab,
            "Delete database records",
            "Choose the record type and a specific entry. Parent deletions cascade to child records."
        )

        card = tk.Frame(
            self.delete_tab, bg=self.PANEL, padx=20, pady=18,
            highlightthickness=1, highlightbackground="#E2DDCF"
        )
        card.pack(fill="x", anchor="n")

        self.delete_type_var = tk.StringVar(value="Roastery")
        self.delete_choice_var = tk.StringVar()

        tk.Label(
            card, text="RECORD TYPE", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))

        self.delete_type_combo = ttk.Combobox(
            card, textvariable=self.delete_type_var,
            values=("Roastery", "Roast Batch", "Cupping Score"),
            state="readonly", font=("Segoe UI", 10)
        )
        self.delete_type_combo.pack(fill="x", ipady=5)
        self.delete_type_combo.bind(
            "<<ComboboxSelected>>", lambda event: self.refresh_delete_choices()
        )

        tk.Label(
            card, text="SELECT RECORD", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(17, 6))

        self.delete_choice_combo = ttk.Combobox(
            card, textvariable=self.delete_choice_var,
            state="readonly", font=("Segoe UI", 10)
        )
        self.delete_choice_combo.pack(fill="x", ipady=5)

        tk.Label(
            card,
            text="Deleting a roastery removes its batches and scores. Deleting a batch removes its scores. Deleting a score affects only that score.",
            bg=self.PANEL, fg=self.MUTED, wraplength=850,
            justify="left", font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(14, 0))

        buttons = tk.Frame(self.delete_tab, bg=self.BG)
        buttons.pack(fill="x", pady=15)

        tk.Button(
            buttons, text="DELETE SELECTED", command=self.delete_selected,
            bg=self.RED, fg="white", activebackground="#812B25",
            activeforeground="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=22, pady=11
        ).pack(side="left")

        tk.Button(
            buttons, text="REFRESH OPTIONS", command=self.refresh_delete_choices,
            bg="#E5E0D4", fg=self.TEXT, activebackground="#D8D1C2",
            relief="flat", cursor="hand2", font=("Segoe UI", 9, "bold"),
            padx=18, pady=11
        ).pack(side="left", padx=10)

    def refresh_delete_choices(self):
        kind = self.delete_type_var.get()

        if kind == "Roastery":
            rows = fetch_all(
                "SELECT roastery_id, roastery_name FROM roasteries ORDER BY roastery_name"
            )
            options = [f"ID {r[0]} — {r[1]}" for r in rows]
        elif kind == "Roast Batch":
            rows = fetch_all("""
                SELECT b.batch_id, r.roastery_name, b.bean_origin
                FROM roast_batches b
                JOIN roasteries r ON r.roastery_id = b.roastery_id
                ORDER BY b.batch_id
            """)
            options = [
                f"ID {r[0]} — {r[1]} | {r[2]}" for r in rows
            ]
        else:
            rows = fetch_all("""
                SELECT s.score_id, s.score_type, s.score_value, b.bean_origin
                FROM cupping_scores s
                JOIN roast_batches b ON b.batch_id = s.batch_id
                ORDER BY s.score_id
            """)
            options = [
                f"ID {r[0]} — {r[1]}: {r[2]} | {r[3]}" for r in rows
            ]

        self.delete_choice_combo["values"] = options
        self.delete_choice_var.set(options[0] if options else "")
        self.delete_choice_combo.set(self.delete_choice_var.get())

    def delete_selected(self):
        selected = self.delete_choice_var.get().strip()
        if not selected:
            messagebox.showwarning(
                "Nothing selected", "There are no records available to delete."
            )
            return

        try:
            record_id = int(selected.split("—", 1)[0].replace("ID", "").strip())
        except (ValueError, IndexError):
            messagebox.showwarning(
                "Invalid selection", "Please select a valid record from the dropdown."
            )
            self.refresh_delete_choices()
            return

        kind = self.delete_type_var.get()
        table_map = {
            "Roastery": "roasteries",
            "Roast Batch": "roast_batches",
            "Cupping Score": "cupping_scores",
        }
        table = table_map[kind]

        warning = (
            "Delete this roastery and ALL its roast batches and cupping scores?"
            if kind == "Roastery" else
            "Delete this roast batch and ALL its cupping scores?"
            if kind == "Roast Batch" else
            "Delete only this cupping score?"
        )

        if not messagebox.askyesno("Confirm deletion", warning):
            return

        try:
            delete_record(table, record_id)
            self.refresh_all()
            self.status_var.set(f"{kind} record #{record_id} deleted.")
            messagebox.showinfo("Deletion complete", "The selected record was deleted.")
        except (sqlite3.Error, ValueError) as error:
            messagebox.showerror("Could not delete record", str(error))
            self.refresh_all()

    def _build_data_panel(self):
        self._section_heading(
            self.data_tab,
            "Live database tables",
            "Select a tab to inspect the joined view or an individual SQLite table."
        )

        self.data_notebook = ttk.Notebook(self.data_tab)
        self.data_notebook.pack(fill="both", expand=True)

        self.join_frame = tk.Frame(self.data_notebook, bg=self.PANEL, padx=8, pady=8)
        self.roastery_frame = tk.Frame(self.data_notebook, bg=self.PANEL, padx=8, pady=8)
        self.batch_frame = tk.Frame(self.data_notebook, bg=self.PANEL, padx=8, pady=8)
        self.score_frame = tk.Frame(self.data_notebook, bg=self.PANEL, padx=8, pady=8)

        self.data_notebook.add(self.join_frame, text="Combined View")
        self.data_notebook.add(self.roastery_frame, text="Roasteries")
        self.data_notebook.add(self.batch_frame, text="Roast Batches")
        self.data_notebook.add(self.score_frame, text="Cupping Scores")

        self.tree_join = self._create_tree(
            self.join_frame,
            ("batch_id", "roastery_name", "bean_origin", "roast_date",
             "score_type", "score_value"),
            ("Batch ID", "Roastery Name", "Bean Origin", "Roast Date",
             "Score Type", "Score Value"),
            (75, 175, 190, 110, 115, 95)
        )
        self.tree_roasteries = self._create_tree(
            self.roastery_frame,
            ("roastery_id", "roastery_name", "contact_email"),
            ("Roastery ID", "Roastery Name", "Contact Email"),
            (110, 260, 300)
        )
        self.tree_batches = self._create_tree(
            self.batch_frame,
            ("batch_id", "roastery_id", "bean_origin", "roast_date"),
            ("Batch ID", "Roastery ID", "Bean Origin", "Roast Date"),
            (100, 120, 250, 150)
        )
        self.tree_scores = self._create_tree(
            self.score_frame,
            ("score_id", "batch_id", "score_type", "score_value"),
            ("Score ID", "Batch ID", "Score Type", "Score Value"),
            (100, 110, 180, 140)
        )

        refresh_bar = tk.Frame(self.data_tab, bg=self.BG)
        refresh_bar.pack(fill="x", pady=(10, 0))
        tk.Button(
            refresh_bar, text="↻  REFRESH TABLES", command=self.refresh_all,
            bg=self.GREEN, fg="white", activebackground=self.GREEN_DARK,
            activeforeground="white", relief="flat", cursor="hand2",
            font=("Segoe UI", 9, "bold"), padx=18, pady=9
        ).pack(side="right")

    def _create_tree(self, parent, columns, headings, widths):
        container = tk.Frame(parent, bg=self.PANEL)
        container.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            container, columns=columns, show="headings", height=13
        )
        y_scroll = ttk.Scrollbar(
            container, orient="vertical", command=tree.yview
        )
        x_scroll = ttk.Scrollbar(
            container, orient="horizontal", command=tree.xview
        )
        tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, minwidth=70, anchor="center")

        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        return tree

    @staticmethod
    def _fill_tree(tree, rows):
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=row)

    def refresh_all(self):
        joined = fetch_all("""
            SELECT b.batch_id, r.roastery_name, b.bean_origin, b.roast_date,
                   s.score_type, s.score_value
            FROM roast_batches b
            JOIN roasteries r ON r.roastery_id = b.roastery_id
            LEFT JOIN cupping_scores s ON s.batch_id = b.batch_id
            ORDER BY b.batch_id, s.score_id
        """)

        roasteries = fetch_all("""
            SELECT roastery_id, roastery_name, contact_email
            FROM roasteries ORDER BY roastery_id
        """)

        batches = fetch_all("""
            SELECT batch_id, roastery_id, bean_origin, roast_date
            FROM roast_batches ORDER BY batch_id
        """)

        scores = fetch_all("""
            SELECT score_id, batch_id, score_type, score_value
            FROM cupping_scores ORDER BY score_id
        """)

        self._fill_tree(self.tree_join, joined)
        self._fill_tree(self.tree_roasteries, roasteries)
        self._fill_tree(self.tree_batches, batches)
        self._fill_tree(self.tree_scores, scores)
        self.refresh_delete_choices()


def main():
    try:
        initialize_database()
    except sqlite3.Error as error:
        print(f"Database initialization failed: {error}")
        return

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(
            "Unable to open the Tkinter window. Run this script in a local "
            "desktop environment such as VS Code on Windows, macOS or Linux."
        )
        print(f"Details: {error}")
        return

    CoffeeRoasteryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
