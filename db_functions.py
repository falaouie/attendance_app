# db_functions.py

# def fetch_all_staff(target_date=None):
#     """Fetch all staff and their attendance data for a specific date."""
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
    
#     if target_date is None:
#         target_date = date.today().strftime("%Y-%m-%d")

#     day_of_week = datetime.strptime(target_date, "%Y-%m-%d").weekday()

#     cursor.execute('''
#         SELECT staff_tbl.staff_id, staff_tbl.first_name, staff_tbl.last_name, 
#                COALESCE(temp_schedule.scheduled_in, staff_schedule.scheduled_in, '') as scheduled_in,
#                COALESCE(temp_schedule.scheduled_out, staff_schedule.scheduled_out, '') as scheduled_out,
#                staff_attendance.work_in, staff_attendance.work_off, 
#                staff_attendance.hours_worked, 
#                COALESCE(temp_schedule.day_off, staff_schedule.day_off, 0) as day_off,
#                temp_schedule.reason_id,
#                COALESCE(temp_schedule.open_schedule, staff_schedule.open_schedule, 0) as open_schedule
#         FROM staff_tbl
#         LEFT JOIN staff_schedule ON staff_tbl.staff_id = staff_schedule.staff_id
#             AND staff_schedule.day_of_week = ?
#         LEFT JOIN temp_schedule ON staff_tbl.staff_id = temp_schedule.staff_id
#             AND temp_schedule.date = ?
#         LEFT JOIN staff_attendance ON staff_tbl.staff_id = staff_attendance.staff_id
#             AND staff_attendance.date = ?
#     ''', (day_of_week, target_date, target_date))
    
#     rows = cursor.fetchall()
#     conn.close()
#     return rows

# def update_work_in(staff_id, work_in_time, current_date):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
    
#     cursor.execute('''
#         INSERT INTO staff_attendance (staff_id, date, work_in)
#         VALUES (?, ?, ?)
#         ON CONFLICT(staff_id, date) DO UPDATE SET work_in = ?
#     ''', (staff_id, current_date, work_in_time, work_in_time))
    
#     conn.commit()
#     conn.close()

# def update_work_off(staff_id, work_off_time, hours_worked, current_date):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     try:
#         cursor.execute('''
#             UPDATE staff_attendance
#             SET work_off = ?, hours_worked = ?
#             WHERE staff_id = ? AND date = ?
#         ''', (work_off_time, hours_worked, staff_id, current_date))
#         conn.commit()
#     except Exception as e:
#         print(f"Error in update_work_off: {e}")
#     finally:
#         conn.close()