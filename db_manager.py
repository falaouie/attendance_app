# db_manager.py
import sqlite3
from datetime import datetime, date
import requests
import json
from internet_conn import is_internet_available

DB_FILE = "attendance.db"
API_URL = "http://silverstage.alawiyeh.com/sync_staff.php"
SCHEDULES_API_URL = "http://silverstage.alawiyeh.com/sync_schedules.php"
TEMP_SCHEDULES_API_URL = "http://silverstage.alawiyeh.com/sync_temp_schedules.php"

def init_db():
    """Initialize the database and create all tables from scratch."""
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
            date TEXT NOT NULL,
            scheduled_in TEXT,
            scheduled_out TEXT,
            day_off INTEGER NOT NULL DEFAULT 0,
            reason_id INTEGER,
            open_schedule INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (staff_id) REFERENCES staff_tbl(staff_id),
            FOREIGN KEY (id) REFERENCES reason_tbl(id),
            UNIQUE(staff_id, date)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            work_in TEXT,
            work_off TEXT,
            hours_worked REAL,
            FOREIGN KEY (staff_id) REFERENCES staff_tbl(staff_id),
            UNIQUE(staff_id, date)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reason_tbl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def sync_staff_data():
    """Sync staff data from the remote API to the local database."""
    if not is_internet_available():
        print("No internet connection. Skipping staff data sync.")
        return False

    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'success':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM staff_tbl')

            for staff in data['data']:
                cursor.execute('''
                    INSERT INTO staff_tbl (staff_id, first_name, last_name)
                    VALUES (?, ?, ?)
                ''', (staff['staff_id'], staff['first_name'], staff['last_name']))

            conn.commit()
            conn.close()
            return True
    except requests.RequestException as e:
        print(f"Error syncing staff data: {str(e)}")
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {str(e)}")
    
    return False

def sync_schedule_data():
    """Sync schedule data from the remote API to the local database."""
    if not is_internet_available():
        print("No internet connection. Skipping schedule data sync.")
        return False

    try:
        response = requests.get(SCHEDULES_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'success':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM staff_schedule')

            for schedule in data['data']:
                day_of_week = int(schedule['work_day'])
                if 0 <= day_of_week <= 6:
                    cursor.execute('''
                        INSERT INTO staff_schedule (staff_id, day_of_week, scheduled_in, scheduled_out, day_off, open_schedule)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        schedule['staff_id'],
                        day_of_week,
                        schedule['start_time'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        schedule['end_time'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        int(schedule['day_off']),
                        int(schedule['open_schedule'])
                    ))
                else:
                    print(f"Invalid work day: {day_of_week}")

            conn.commit()
            conn.close()
            return True
    except requests.RequestException as e:
        print(f"Error syncing schedule data: {str(e)}")
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {str(e)}")
    except KeyError as e:
        print(f"Key error in schedule data: {str(e)}")
    except ValueError as e:
        print(f"Value error in schedule data: {str(e)}")
    
    return False

def sync_temp_schedule_data():
    """Sync temporary schedule data from the remote API to the local database."""
    if not is_internet_available():
        print("No internet connection. Skipping temporary schedule data sync.")
        return False

    try:
        response = requests.get(TEMP_SCHEDULES_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'success':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM temp_schedule')

            for schedule in data['data']:
                try:
                    cursor.execute('''
                        INSERT INTO temp_schedule (staff_id, date, scheduled_in, scheduled_out, day_off, reason_id, open_schedule)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        schedule['staff_id'],
                        schedule['date'],
                        schedule['scheduled_in'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        schedule['scheduled_out'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        int(schedule['day_off']),
                        schedule.get('reason_id'),
                        int(schedule['open_schedule'])
                    ))
                except Exception as e:
                    print(f"Error inserting record: {e}")
                    print(f"Problematic record: {schedule}")

            conn.commit()
            conn.close()
            return True
        else:
            print(f"API returned non-success status: {data.get('status')}")
            print(f"API message: {data.get('message', 'No message provided')}")
    except requests.RequestException as e:
        print(f"Request error syncing temporary schedule data: {str(e)}")
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {str(e)}")
    except KeyError as e:
        print(f"Key error in temporary schedule data: {str(e)}")
    except ValueError as e:
        print(f"Value error in temporary schedule data: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in sync_temp_schedule_data: {str(e)}")
    
    return False

def fetch_all_staff(target_date=None):
    """Fetch all staff and their attendance data for a specific date."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    day_of_week = datetime.strptime(target_date, "%Y-%m-%d").weekday()

    cursor.execute('''
        SELECT staff_tbl.staff_id, staff_tbl.first_name, staff_tbl.last_name, 
               COALESCE(temp_schedule.scheduled_in, staff_schedule.scheduled_in, '') as scheduled_in,
               COALESCE(temp_schedule.scheduled_out, staff_schedule.scheduled_out, '') as scheduled_out,
               staff_attendance.work_in, staff_attendance.work_off, 
               staff_attendance.hours_worked, 
               COALESCE(temp_schedule.day_off, staff_schedule.day_off, 0) as day_off,
               temp_schedule.reason_id,
               COALESCE(temp_schedule.open_schedule, staff_schedule.open_schedule, 0) as open_schedule
        FROM staff_tbl
        LEFT JOIN staff_schedule ON staff_tbl.staff_id = staff_schedule.staff_id
            AND staff_schedule.day_of_week = ?
        LEFT JOIN temp_schedule ON staff_tbl.staff_id = temp_schedule.staff_id
            AND temp_schedule.date = ?
        LEFT JOIN staff_attendance ON staff_tbl.staff_id = staff_attendance.staff_id
            AND staff_attendance.date = ?
    ''', (day_of_week, target_date, target_date))
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_work_in(staff_id, work_in_time, current_date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO staff_attendance (staff_id, date, work_in)
        VALUES (?, ?, ?)
        ON CONFLICT(staff_id, date) DO UPDATE SET work_in = ?
    ''', (staff_id, current_date, work_in_time, work_in_time))
    
    conn.commit()
    conn.close()

def update_work_off(staff_id, work_off_time, hours_worked, current_date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE staff_attendance
            SET work_off = ?, hours_worked = ?
            WHERE staff_id = ? AND date = ?
        ''', (work_off_time, hours_worked, staff_id, current_date))
        conn.commit()
    except Exception as e:
        print(f"Error in update_work_off: {e}")
    finally:
        conn.close()

# def set_temp_schedule(staff_id, date, scheduled_in, scheduled_out, day_off, reason_id, open_schedule):
#     """Set a temporary schedule for a staff member on a specific date."""
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
    
#     cursor.execute('''
#         INSERT INTO temp_schedule (staff_id, date, scheduled_in, scheduled_out, day_off, reason_id, open_schedule)
#         VALUES (?, ?, ?, ?, ?, ?, ?)
#         ON CONFLICT(staff_id, date) DO UPDATE SET 
#         scheduled_in = ?, scheduled_out = ?, day_off = ?, reason_id = ?, open_schedule = ?
#     ''', (staff_id, date, scheduled_in, scheduled_out, day_off, reason_id, open_schedule,
#           scheduled_in, scheduled_out, day_off, reason_id, open_schedule))
    
#     conn.commit()
#     conn.close()

# if __name__ == "__main__":
#     print("Initializing database and syncing data...")
#     init_db()
#     sync_staff_data()
#     sync_schedule_data()
#     sync_temp_schedule_data() 
#     print("Database initialized and synced.")