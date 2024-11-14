from pytz import timezone
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtCore import QTimer
from loading import LoadingScreen, LoadingSignals
from internet_conn import is_internet_available
from Classes import TimeSync, DataSync
from table_manager import TableManager
from work_time_manager import WorkTimeManager
from sync_manager import SyncManager
from loading_manager import LoadingManager
from window_manager import WindowManager
from signal_handler import SignalHandler

class MainWindow(QWidget):
    
    def __init__(self):
        super().__init__()
        self.loading_signals = LoadingSignals()
        # self.loading_signals.finished.connect(self.finish_loading)
        
        # Initialize TimeSync
        self.time_sync = TimeSync()
        self.beirut_tz = timezone('Asia/Beirut')
        self.current_datetime = self.time_sync.get_current_datetime()
        self.current_date = self.current_datetime.date()
        print(f"initialized date and time : {self.current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize managers
        self.window_manager = WindowManager(self)
        self.signal_handler = SignalHandler(self)
        self.work_time_manager = WorkTimeManager(self.current_datetime, self.beirut_tz)
        
        self.last_internet_status = is_internet_available()
        
        # Initialize DataSync
        self.data_sync = DataSync(self.current_datetime)
        self.sync_manager = SyncManager(self.time_sync, self.data_sync, self.current_datetime)

        # Create loading screen and manager
        self.loading_screen = LoadingScreen()
        self.loading_manager = LoadingManager(self.loading_screen, self)

        # Set up all signals
        self.signal_handler.setup_signals()

        # Show loading screen and start sequence
        self.loading_screen.show()
        QTimer.singleShot(100, self.loading_manager.start_loading_sequence)

    def handle_time_increment(self, new_datetime):
        """Handle regular clock updates"""
        self.current_datetime = new_datetime
        self.work_time_manager.update_current_datetime(new_datetime)
        
        date_str = self.current_datetime.strftime("%A %d/%m/%Y")
        time_str = self.current_datetime.strftime("%I:%M:%S %p")
        self.datetime_label.setText(f"{date_str}\n{time_str}")

        if self.current_datetime.date() != self.current_date:
            self.current_date = self.current_datetime.date()
            self.table_manager.refresh()

    def handle_sync_complete(self, success):
        """Handle completion of sync operation"""
        if success:
            self.table_manager.refresh(force=True)

    def handle_time_update(self, new_datetime):
        """Handle time update from sync"""
        self.current_datetime = new_datetime
        self.work_time_manager.update_current_datetime(new_datetime)

    def update_loading_progress(self, value):
        if hasattr(self, 'loading_screen') and self.loading_screen:
            self.loading_screen.set_progress(value)

    def update_loading_status(self, text):
        if hasattr(self, 'loading_screen') and self.loading_screen:
            self.loading_screen.set_loading_text(text)

    def finish_loading(self):
        """Delegate to loading manager"""
        self.loading_manager.finish_loading()

    def handle_ntp_sync_complete(self, ntp_time):
        """Handler for NTP sync completion - this needs to be a class method"""
        if ntp_time:
            self.current_datetime = ntp_time
            print(f"NTP sync successful: {self.current_datetime}")
        else:
            print("NTP sync failed, using system time")
        
        # Clean up the worker
        if hasattr(self, 'ntp_worker'):
            self.ntp_worker.deleteLater()
        
        # Signal that loading is complete
        self.loading_signals.finished.emit()

    def initUI(self):
        """Initialize the user interface"""
        # Set up the window and layout
        self.window_manager.setup_window()
        
        # Initialize table manager with the table from window manager
        self.table_manager = TableManager(self.window_manager.table, 
                                        self.current_datetime, 
                                        self.beirut_tz)
        
        # Set up table manager callbacks
        self.table_manager.set_callbacks(
            handle_work_in_callback=self.handle_work_in,
            handle_work_off_callback=self.handle_work_off,
            show_error_callback=self.show_error_message
        )

        # Initial table refresh
        self.table_manager.refresh(force=True)

    def setup_system_tray(self):
        """Set up the system tray icon"""
        self.window_manager.setup_system_tray()

    def handle_work_in(self, row, staff_id):
        if self.work_time_manager.handle_work_in(row, staff_id, self.show_error_message):
            self.table_manager.refresh(force=True)

    def handle_work_off(self, row, staff_id, work_in_time):
        if self.work_time_manager.handle_work_off(row, staff_id, work_in_time, self.show_error_message):
            self.table_manager.refresh(force=True)

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)
    
    def sync_data(self):
        """Method for manual data sync"""
        try:
            if self.data_sync.sync_data(self.current_datetime):
                self.table_manager.refresh(force=True)
        except Exception as e:
            print(f"Error during manual data sync: {str(e)}")

    def check_data_sync(self):
        """Handler for data sync timer"""
        try:
            if self.data_sync.check_and_sync(self.current_datetime):
                self.table_manager.refresh(force=True)
        except Exception as e:
            print(f"Error during periodic data sync: {str(e)}")

    def show_window(self):
        """Show and maximize the window"""
        self.window_manager.show_window()

    def closeEvent(self, event):
        """Handle window close event"""
        event.ignore()
        self.window_manager.minimize_to_taskbar()
        self.window_manager.show_tray_message(
            "Silver Attendance",
            "Application minimized to taskbar"
        )

    def close_application(self):
        """Clean shutdown of the application"""
        self.sync_manager.stop_timers()
        QApplication.quit()
        