# db_manager.py
import sqlite3

DB_FILE = "attendance.db"

def init_db():
    """Initialize the database and create all tables if not exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_tbl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,  -- 0 (Monday) to 6 (Sunday)
            scheduled_in TEXT,
            scheduled_out TEXT,
            day_off INTEGER NOT NULL DEFAULT 0,
            open_schedule INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (staff_id) REFERENCES staff_tbl(staff_id),
            UNIQUE(staff_id, day_of_week)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            scheduled_in TEXT,
            scheduled_out TEXT,
            day_off INTEGER NOT NULL DEFAULT 0,
            open_schedule INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (staff_id) REFERENCES staff_tbl(staff_id),
            UNIQUE(staff_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            work_in TEXT,
            work_off TEXT,
            hours_worked REAL,
            FOREIGN KEY (staff_id) REFERENCES staff_tbl(staff_id),
            UNIQUE(staff_id, work_date)
        )
    ''')

    conn.commit()
    conn.close()