import ntplib
from datetime import datetime, timedelta, timezone as dt_timezone
from pytz import timezone
from PyQt5.QtCore import QThread, pyqtSignal
from internet_conn import is_internet_available
from db_sync import sync_staff_data, sync_schedule_data, sync_temp_schedule_data

class TimeSync:
    def __init__(self):
        self.beirut_tz = timezone('Asia/Beirut')
        self.current_datetime = datetime.now(self.beirut_tz)
        self.time_difference_threshold = timedelta(minutes=5)
        self.ntp_servers = [
            'time.google.com',
            'pool.ntp.org',          # Global NTP pool
            'time.nist.gov',         # NIST's public time server
            'time.cloudflare.com',   # Cloudflare's NTP service
        ]
        
    def get_current_datetime(self):
        return self.current_datetime
    
    def increment_time(self):
        self.current_datetime += timedelta(seconds=1)
        return self.current_datetime
    
    def sync_with_system_time(self):
        system_time = datetime.now(self.beirut_tz)
        self.current_datetime = system_time
        return self.current_datetime

    def sync_with_ntp(self):
        if not is_internet_available():
            print("No internet connection. Cannot sync with NTP server.")
            return None

        last_error = None
        for server in self.ntp_servers:
            try:
                client = ntplib.NTPClient()
                response = client.request(server, version=3, timeout=5)
                ntp_time = datetime.fromtimestamp(response.tx_time, dt_timezone.utc)
                beirut_time = ntp_time.astimezone(self.beirut_tz)
                print(f"Successfully synced time with NTP server {server}. Current time: {beirut_time}")
                self.current_datetime = beirut_time
                return beirut_time
                
            except (ntplib.NTPException, OSError) as e:
                last_error = e
                print(f"Failed to sync with {server}: {str(e)}")
                continue
                
        # If we get here, all servers failed
        print(f"Failed to sync with all NTP servers. Last error: {str(last_error)}")
        return None

    def fallback_to_system_time(self):
        system_time = datetime.now(self.beirut_tz)
        time_difference = abs(system_time - self.current_datetime)

        if time_difference <= self.time_difference_threshold:
            self.current_datetime = system_time
            print(f"Synced with system time. Time difference was within threshold: {time_difference}")
        else:
            print(f"Time difference exceeds threshold. Using App time, Current time might be inaccurate. Difference: {time_difference}")

class DataSync:
    def __init__(self, current_datetime):
        self.last_sync_attempt = current_datetime
        self.sync_counter = 0

    def sync_data(self, app_time):
        """Synchronize all data with the server"""
        if is_internet_available():
            if sync_staff_data() and sync_schedule_data() and sync_temp_schedule_data():
                self.sync_counter += 1
                print(f"Data sync #{self.sync_counter} completed at App time: {app_time.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                print(f"Failed to synchronize data. Using local data. {app_time.strftime('%Y-%m-%d %H:%M:%S')}")
                return False
        else:
            print(f"No internet connection. Using local data. {app_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return False
        

class NTPSyncWorker(QThread):
    finished = pyqtSignal(object)  # Signal to emit the NTP time result
    progress = pyqtSignal(int)     # Signal for progress updates
    status = pyqtSignal(str)       # Signal for status messages
    
    def __init__(self, time_sync):
        super().__init__()
        self.time_sync = time_sync
    
    def run(self):
        try:
            self.status.emit("Syncing with NTP servers...")
            self.progress.emit(85)
            
            ntp_time = self.time_sync.sync_with_ntp()
            
            self.progress.emit(95)
            self.status.emit("Loading complete!")
            self.progress.emit(100)
            
            # Emit the result (could be None if sync failed)
            self.finished.emit(ntp_time)
            
        except Exception as e:
            print(f"Error during NTP sync: {str(e)}")
            self.progress.emit(95)
            self.status.emit("Loading complete!")
            self.progress.emit(100)
            self.finished.emit(None)