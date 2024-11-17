from pytz import timezone
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QSystemTrayIcon
from PyQt5.QtCore import QTimer
from Classes import TimeSync, DataSync, LoadingScreen, LoadingSignals
from table_manager import TableManager
from work_time_manager import WorkTimeManager
from sync_manager import SyncManager
from loading_manager import LoadingManager
from window_manager import WindowManager
from signal_handler import SignalHandler
from internet_conn import is_internet_available

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize is internet available
        self.is_internet_available = is_internet_available
        
        # Initialize signals
        self.loading_signals = LoadingSignals()
        
        # Initialize TimeSync and core datetime
        self.time_sync = TimeSync()
        self.beirut_tz = timezone('Asia/Beirut')
        self.current_datetime = self.time_sync.get_current_datetime()
        self.current_date = self.current_datetime.date()
        print(f"initialized date and time : {self.current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize managers
        self.window_manager = WindowManager(self)
        self.signal_handler = SignalHandler(self)
        self.work_time_manager = WorkTimeManager(self.current_datetime, self.beirut_tz)
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

    def finish_loading(self):
        """Handler for loading completion signal"""
        self.loading_manager.finish_loading()
    
    def handle_ntp_sync_complete(self, ntp_time):
        """Handler for NTP sync completion"""
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

    def show_window(self):
        """Show and maximize the window"""
        self.window_manager.show_window()

    def initUI(self):
        """Initialize the user interface"""
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
        """Handle work in button clicks"""
        if self.work_time_manager.handle_work_in(row, staff_id, self.show_error_message):
            self.table_manager.refresh(force=True)

    def handle_work_off(self, row, staff_id, work_in_time):
        """Handle work off button clicks"""
        if self.work_time_manager.handle_work_off(row, staff_id, work_in_time, self.show_error_message):
            self.table_manager.refresh(force=True)

    def show_error_message(self, message):
        """Show error message to user"""
        QMessageBox.critical(self, "Error", message)

    def sync_data(self):
        """Method for manual data sync"""
        try:
            if self.data_sync.sync_data(self.current_datetime):
                self.table_manager.refresh(force=True)
        except Exception as e:
            print(f"Error during manual data sync: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event to minimize to both taskbar and system tray"""
        event.ignore()
        self.window_manager.minimize_to_taskbar()
        self.window_manager.show_tray_message(
            "Silver Attendance",
            "Application minimized to taskbar and system tray",
            QSystemTrayIcon.Information,
            2000
        )

    def close_application(self):
        """Clean shutdown of the application"""
        self.sync_manager.stop_timers()
        QApplication.quit()