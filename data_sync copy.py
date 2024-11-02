# data_sync.py
from datetime import datetime
from internet_conn import is_internet_available
from db_manager import sync_staff_data, sync_schedule_data, sync_temp_schedule_data

class DataSync:
    def __init__(self):
        self.last_sync_attempt = datetime.now()

    def check_and_sync(self, current_time):
        """Check if enough time has passed for next sync attempt"""
        if (current_time - self.last_sync_attempt).total_seconds() >= 120:  # 2 minutes
            return self.sync_data()
        return False
        
    def sync_data(self):
        """Synchronize all data with the server"""
        self.last_sync_attempt = datetime.now()
        if is_internet_available():
            if sync_staff_data() and sync_schedule_data() and sync_temp_schedule_data():
                print(f"data synchronized successfully at System time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                print(f"Failed to synchronize data. Using local data. {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return False
        else:
            print(f"No internet connection. Using local data. {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return False