import sqlite3
from contextlib import closing

DB_PATH = "hospital.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with closing(get_connection()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                department TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def book_appointment(patient_name, department, appointment_date, appointment_time, notes=""):
    with closing(get_connection()) as conn:
        conn.execute(
            """INSERT INTO appointments
               (patient_name, department, appointment_date, appointment_time, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (patient_name, department, appointment_date, appointment_time, notes)
        )
        conn.commit()

def list_appointments():
    with closing(get_connection()) as conn:
        return conn.execute(
            """SELECT id, patient_name, department, appointment_date,
                      appointment_time, notes, created_at
               FROM appointments ORDER BY appointment_date, appointment_time"""
        ).fetchall()

def delete_appointment(appointment_id):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
