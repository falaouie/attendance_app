# work_time_manager.py
from datetime import datetime, timedelta
from db_functions import update_work_in, update_work_off

class WorkTimeManager:
    def __init__(self, current_datetime, beirut_tz):
        self.current_datetime = current_datetime
        self.beirut_tz = beirut_tz

    def handle_work_in(self, row, staff_id, error_callback):
        """
        Handle work in time recording
        
        Args:
            row: Row number in the table
            staff_id: ID of the staff member
            error_callback: Function to call if an error occurs
        """
        try:
            current_time = self.current_datetime.strftime("%H:%M:%S")  # 24-hour format
            update_work_in(staff_id, current_time, self.current_datetime.date().strftime("%Y-%m-%d"))
            return True
        except Exception as e:
            error_callback(f"Error recording Work In: {str(e)}")
            return False

    def handle_work_off(self, row, staff_id, work_in_time, error_callback):
        """
        Handle work off time recording and calculate hours worked
        
        Args:
            row: Row number in the table
            staff_id: ID of the staff member
            work_in_time: Time when the staff member started working
            error_callback: Function to call if an error occurs
        """
        try:
            if work_in_time is None:
                raise ValueError("Work In time is not available")

            # Ensure work_in_time is timezone-aware
            work_in_dt = datetime.strptime(work_in_time, "%H:%M:%S")
            work_in_full = self.beirut_tz.localize(datetime.combine(self.current_datetime.date(), work_in_dt.time()))

            # Ensure current_datetime is timezone-aware
            current_datetime = self.beirut_tz.localize(self.current_datetime.replace(tzinfo=None))

            # Calculate the time difference
            time_diff = current_datetime - work_in_full

            # Handle cases where work spans midnight
            if time_diff.days < 0:
                time_diff = timedelta(days=1) + time_diff

            # Calculate hours worked
            hours_worked = time_diff.total_seconds() / 3600

            # Format work_off_time in 24-hour format for database
            work_off_time = current_datetime.strftime("%H:%M:%S")

            update_work_off(staff_id, work_off_time, hours_worked, self.current_datetime.date().strftime("%Y-%m-%d"))
            return True
        except Exception as e:
            error_callback(f"Error recording Work Off: {str(e)}")
            return False

    def update_current_datetime(self, current_datetime):
        """
        Update the current datetime used by the manager
        
        Args:
            current_datetime: New datetime to use
        """
        self.current_datetime = current_datetime