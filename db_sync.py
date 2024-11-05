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

            # Increase timeout to handle potential lock issues
            conn.execute('PRAGMA busy_timeout = 5000')

            cursor = conn.cursor()

            try:
                # Begin a transaction
                conn.execute('BEGIN TRANSACTION')

                # Fetch all local staff_ids
                cursor.execute('SELECT staff_id, first_name, last_name FROM staff_tbl')
                local_staff = cursor.fetchall()

                local_staff_dict = {row[0]: (row[1], row[2]) for row in local_staff}
                remote_staff_dict = {staff['staff_id']: (staff['first_name'], staff['last_name']) for staff in data['data']}

                # Convert remote staff IDs to integers for consistency with local IDs
                remote_staff_dict = {int(staff['staff_id']): (staff['first_name'], staff['last_name']) for staff in data['data']}

                # Insert or update staff from remote API
                for staff_id, (first_name, last_name) in remote_staff_dict.items():
                    print(f"Processing staff from remote: {staff_id}, {first_name}, {last_name}")
                    cursor.execute('''
                        INSERT INTO staff_tbl (staff_id, first_name, last_name)
                        VALUES (?, ?, ?)
                        ON CONFLICT(staff_id) 
                        DO UPDATE SET first_name = excluded.first_name, last_name = excluded.last_name
                        WHERE first_name != excluded.first_name OR last_name != excluded.last_name
                    ''', (staff_id, first_name, last_name))

                # Identify records that are in the local database but not in the remote data
                local_staff_ids = set(local_staff_dict.keys())
                remote_staff_ids = set(remote_staff_dict.keys())

                print("Local staff IDs:", local_staff_ids)
                print("Remote staff IDs:", remote_staff_ids)

                # Calculate the difference between local and remote staff_ids
                staff_ids_to_delete = local_staff_ids - remote_staff_ids
                print("Staff IDs to delete:", staff_ids_to_delete)

                # Delete staff that are in local but not in remote
                for staff_id in staff_ids_to_delete:
                    print(f"Deleting staff from local: {staff_id}")
                    cursor.execute('DELETE FROM staff_tbl WHERE staff_id = ?', (staff_id,))

                # Commit the transaction
                conn.commit()

            except sqlite3.IntegrityError as e:
                # Handle unique constraint failure or other integrity errors
                print(f"Integrity error: {str(e)}")
                conn.rollback()
                return False

            except sqlite3.Error as e:
                # Rollback the transaction if any other database error occurs
                conn.rollback()
                print(f"Database error: {str(e)}")
                return False

            finally:
                # Always close the connection
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