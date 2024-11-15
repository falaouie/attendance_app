# Classes.py TimeSync, DataSync, NTPSyncWorker, LoadingSignals, LoadingScreen
import sys
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QDesktopWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, pyqtSignal
import ntplib
from datetime import datetime, timedelta, timezone as dt_timezone
from pytz import timezone
from PyQt5.QtCore import QThread, pyqtSignal, QObject, Qt
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
                print(f"Time Sync with {server}. {beirut_time}")
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

class LoadingSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout()
        
        # Logo
        logo_label = QLabel()

        # Get correct path whether running as script or exe
        if hasattr(sys, '_MEIPASS'):
            # Running as exe
            logo_path = os.path.join(sys._MEIPASS, 'images', 'logo.png')
        else:
            # Running as script
            logo_path = os.path.join(os.path.dirname(__file__), 'images', 'logo.png')
        
        pixmap = QPixmap(logo_path)
        scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)
        
        # Loading text
        self.loading_label = QLabel("Initializing...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #2196F3; font-size: 14px;")
        layout.addWidget(self.loading_label)
        
        self.setLayout(layout)
        self.center()
        
    def set_loading_text(self, text):
        self.loading_label.setText(text)
        
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def set_progress(self, value):
        self.progress.setValue(value)