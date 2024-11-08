# db_sync.py
import sqlite3
import requests
import json
from internet_conn import is_internet_available
from db_manager import DB_FILE
API_URL = "http://silverstage.alawiyeh.com/sync_staff.php"
SCHEDULES_API_URL = "http://silverstage.alawiyeh.com/sync_schedules.php"
TEMP_SCHEDULES_API_URL = "http://silverstage.alawiyeh.com/sync_temp_schedules.php"
# SYNC_STATUS_API_URL = ""

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

                # Calculate the difference between local and remote staff_ids
                staff_ids_to_delete = local_staff_ids - remote_staff_ids

                # Delete staff that are in local but not in remote
                for staff_id in staff_ids_to_delete:
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
    """Sync all schedule data from the remote API to the local database."""
    if not is_internet_available():
        print("No internet connection. Skipping schedule data sync.")
        return False

    try:
        # Fetch all schedule records from the remote API
        response = requests.get(SCHEDULES_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'success':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # Step 1: Fetch all local schedule data
            cursor.execute('SELECT staff_id, day_of_week FROM staff_schedule')
            local_schedule_data = cursor.fetchall()
            local_schedule_dict = {(int(staff_id), int(day_of_week)) for staff_id, day_of_week in local_schedule_data}

            # Step 2: Prepare remote schedule data and track keys
            remote_schedule_dict = set()

            for schedule in data['data']:
                staff_id = int(schedule['staff_id'])
                day_of_week = int(schedule['work_day'])

                remote_schedule_dict.add((staff_id, day_of_week))

                # Check if the staff_id and day_of_week exists in the local schedule
                cursor.execute('SELECT COUNT(1) FROM staff_schedule WHERE staff_id = ? AND day_of_week = ?', (staff_id, day_of_week))
                exists = cursor.fetchone()[0]

                if exists:
                    # Update the existing record
                    cursor.execute('''
                        UPDATE staff_schedule
                        SET scheduled_in = ?, scheduled_out = ?, day_off = ?, open_schedule = ?
                        WHERE staff_id = ? AND day_of_week = ?
                    ''', (
                        schedule['start_time'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        schedule['end_time'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        int(schedule['day_off']),
                        int(schedule['open_schedule']),
                        staff_id,
                        day_of_week
                    ))
                else:
                    # Insert new record if staff_id and day_of_week combination does not exist
                    cursor.execute('''
                        INSERT INTO staff_schedule (staff_id, day_of_week, scheduled_in, scheduled_out, day_off, open_schedule)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        staff_id,
                        day_of_week,
                        schedule['start_time'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        schedule['end_time'] if not int(schedule['day_off']) and not int(schedule['open_schedule']) else None,
                        int(schedule['day_off']),
                        int(schedule['open_schedule'])
                    ))

            # Step 3: Identify records that are in the local database but not in the remote data
            records_to_delete = local_schedule_dict - remote_schedule_dict

            # Step 4: Delete records that are in local but not in remote
            for staff_id, day_of_week in records_to_delete:
                cursor.execute('DELETE FROM staff_schedule WHERE staff_id = ? AND day_of_week = ?', (staff_id, day_of_week))

            # Commit the changes to the local database
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
    """Sync staff data from the remote API to the local database."""
    if not is_internet_available():
        print("No internet connection. Skipping staff data sync.")
        return False

    try:
        response = requests.get(TEMP_SCHEDULES_API_URL, timeout=5000)
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

                # Fetch all local temp schedule
                cursor.execute('SELECT staff_id, scheduled_in, scheduled_out, day_off, open_schedule FROM temp_schedule')
                local_temp_schedule = cursor.fetchall()

                local_temp_schedule_dict = {row[0]: (row[1], row[2], row[3], row[4]) for row in local_temp_schedule}
                remote_temp_schedule_dict = {staff['staff_id']: (staff['scheduled_in'], staff['scheduled_out'], staff['day_off'], staff['open_schedule']) for staff in data['data']}

                # Convert remote staff IDs to integers for consistency with local IDs
                remote_temp_schedule_dict = {int(staff['staff_id']): (staff['scheduled_in'], staff['scheduled_out'], staff['day_off'], staff['open_schedule']) for staff in data['data']}

                # Insert or update staff from remote API
                for staff_id, (scheduled_in, scheduled_out, day_off, open_schedule) in remote_temp_schedule_dict.items():
                    cursor.execute('''
                        INSERT INTO temp_schedule (staff_id, scheduled_in, scheduled_out, day_off, open_schedule)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(staff_id) 
                        DO UPDATE SET scheduled_in = excluded.scheduled_in, scheduled_out = excluded.scheduled_out, day_off = excluded.day_off, open_schedule = excluded.open_schedule
                        WHERE scheduled_in != excluded.scheduled_in OR scheduled_out != excluded.scheduled_out OR day_off != excluded.day_off OR open_schedule != excluded.open_schedule
                    ''', (staff_id, scheduled_in, scheduled_out, day_off, open_schedule))

                # Identify records that are in the local database but not in the remote data
                local_staff_ids = set(local_temp_schedule_dict.keys())
                remote_staff_ids = set(remote_temp_schedule_dict.keys())

                # Calculate the difference between local and remote staff_ids
                staff_ids_to_delete = local_staff_ids - remote_staff_ids

                # Delete staff that are in local but not in remote
                for staff_id in staff_ids_to_delete:
                    cursor.execute('DELETE FROM temp_schedule WHERE staff_id = ?', (staff_id,))

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