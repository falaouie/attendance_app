# db_sync.py
import sqlite3
import requests
import json
from internet_conn import is_internet_available
from db_manager import DB_FILE
API_URL = "http://silverstage.alawiyeh.com/sync_staff.php"
SCHEDULES_API_URL = "http://silverstage.alawiyeh.com/sync_schedules.php"
TEMP_SCHEDULES_API_URL = "http://silverstage.alawiyeh.com/sync_temp_schedules.php"

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