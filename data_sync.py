from datetime import datetime
from internet_conn import is_internet_available
from db_manager import sync_staff_data, sync_schedule_data, sync_temp_schedule_data

class DataSync:
    def __init__(self, current_datetime):
        self.last_sync_attempt = current_datetime

    def check_and_sync(self, app_time):
        """Check if enough time has passed for next sync attempt"""
        time_diff = (app_time - self.last_sync_attempt).total_seconds()
        if time_diff >= 120:  # 2 minutes
            success = self.sync_data(app_time)
            if success:
                self.last_sync_attempt = app_time
            return success
        return False

    def sync_data(self, app_time):
        """Synchronize all data with the server"""
        if is_internet_available():
            if sync_staff_data() and sync_schedule_data() and sync_temp_schedule_data():
                print(f"data synchronized successfully at App hon time: {app_time.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                print(f"Failed to synchronize data. Using local data. {app_time.strftime('%Y-%m-%d %H:%M:%S')}")
                return False
        else:
            print(f"No internet connection. Using local data. {app_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return False