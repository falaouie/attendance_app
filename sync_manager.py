from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt
from internet_conn import is_internet_available

class SyncManager(QObject):
    # Signals for notifying the main window
    sync_complete = pyqtSignal(bool)  # True if successful
    time_updated = pyqtSignal(object)  # Sends the new datetime
    time_incremented = pyqtSignal(object)  # For clock updates

    def __init__(self, time_sync, data_sync, current_datetime):
        super().__init__()
        self.time_sync = time_sync
        self.data_sync = data_sync
        self.current_datetime = current_datetime
        
        # Sync parameters
        self.sync_interval = 120  # 2 minutes in seconds
        self.retry_interval = 60  # 1 minute in seconds
        self.max_retries = 5
        self.retries = 0
        self.internet_check_interval = 30  # 30 seconds
        self.last_internet_status = is_internet_available()

        # Initialize timers
        self.setup_timers()

    def setup_timers(self):
        """Initialize and start all timers"""
        # Timer for updating internal clock every second
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_time)
        self.clock_timer.start(1000)  # 1 second
        
        # Timer for periodic sync operations
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.periodic_sync_attempt)
        self.sync_timer.setTimerType(Qt.PreciseTimer)
        self.sync_timer.start(self.sync_interval * 1000)

        # Timer for periodic internet connection check
        self.internet_check_timer = QTimer(self)
        self.internet_check_timer.timeout.connect(self.check_internet_and_sync)
        self.internet_check_timer.start(self.internet_check_interval * 1000)

    def update_time(self):
        """Update internal clock"""
        self.current_datetime = self.time_sync.increment_time()
        self.time_incremented.emit(self.current_datetime)

    def periodic_sync_attempt(self):
        """Combined time and data sync operation"""
        if not is_internet_available():
            print("No internet connection. Skipping sync.")
            self.retry_sync()
            return

        ntp_time = self.time_sync.sync_with_ntp()
        if ntp_time:
            self.retries = 0  # Reset retry counter on success
            self.current_datetime = ntp_time
            self.time_updated.emit(ntp_time)
            
            # Immediately sync data after successful time sync
            if self.data_sync.sync_data(self.current_datetime):
                self.sync_complete.emit(True)
            else:
                self.sync_complete.emit(False)
        else:
            print("Failed to sync time. Starting retry process...")
            self.retry_sync()

    def retry_sync(self):
        """Combined retry for both time and data sync"""
        if self.retries < self.max_retries:
            self.retries += 1
            print(f"Retrying sync... Attempt {self.retries}/{self.max_retries}")
            
            if not is_internet_available():
                print(f"No internet connection during retry attempt {self.retries}. Will retry again...")
                QTimer.singleShot(self.retry_interval * 1000, self.periodic_sync_attempt)
                return

            ntp_time = self.time_sync.sync_with_ntp()
            if ntp_time:
                self.retries = 0
                self.current_datetime = ntp_time
                print(f"Time sync successful on retry attempt {self.retries}")
                self.time_updated.emit(ntp_time)
                
                # Try data sync after successful time sync
                if self.data_sync.sync_data(self.current_datetime):
                    self.sync_complete.emit(True)
                else:
                    self.sync_complete.emit(False)
            else:
                print(f"Sync failed on retry attempt {self.retries}. Scheduling next retry...")
                QTimer.singleShot(self.retry_interval * 1000, self.periodic_sync_attempt)
        else:
            print(f"Maximum retry attempts ({self.max_retries}) reached. Falling back to system time...")
            self.time_sync.fallback_to_system_time()
            self.current_datetime = self.time_sync.get_current_datetime()
            self.time_updated.emit(self.current_datetime)
            self.sync_complete.emit(False)

    def sync_time_and_data(self):
        """Manual sync operation"""
        ntp_time = self.time_sync.sync_with_ntp()
        if ntp_time:
            self.current_datetime = ntp_time
            print(f"Time synced successfully: {self.current_datetime}")
            self.time_updated.emit(ntp_time)
        else:
            print("Failed to sync time with NTP. Using current app time.")

        if self.data_sync.sync_data(self.current_datetime):
            self.sync_complete.emit(True)
        else:
            self.sync_complete.emit(False)

    def check_internet_and_sync(self):
        """Check internet connection and initiate sync if connection is restored"""
        current_internet_status = is_internet_available()
        if current_internet_status and not self.last_internet_status:
            print("Internet connection restored. Initiating sync...")
            self.periodic_sync_attempt()
        self.last_internet_status = current_internet_status

    def update_current_datetime(self, current_datetime):
        """Update the current datetime used by the manager"""
        self.current_datetime = current_datetime

    def stop_timers(self):
        """Stop all timers - should be called before application closes"""
        self.clock_timer.stop()
        self.sync_timer.stop()
        self.internet_check_timer.stop()