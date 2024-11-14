import os
import sys
from pytz import timezone
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox, QSystemTrayIcon, QMenu
from PyQt5.QtWidgets import QLabel, QTableWidget, QHeaderView
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt
from loading import LoadingScreen, LoadingSignals
from internet_conn import is_internet_available
from Classes import TimeSync, DataSync
from utilities import resource_path, minimize_to_taskbar
from table_manager import TableManager
from work_time_manager import WorkTimeManager
from sync_manager import SyncManager
from loading_manager import LoadingManager

class MainWindow(QWidget):
    
    def __init__(self):
        super().__init__()
        self.loading_signals = LoadingSignals()
        self.loading_signals.finished.connect(self.finish_loading)
        # self.loading_signals.progress.connect(self.update_loading_progress)
        # self.loading_signals.status.connect(self.update_loading_status)
        
        # Initialize TimeSync
        self.time_sync = TimeSync()
        self.beirut_tz = timezone('Asia/Beirut')
        self.current_datetime = self.time_sync.get_current_datetime()
        self.current_date = self.current_datetime.date()
        print(f"initialized date and time : {self.current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        self.work_time_manager = WorkTimeManager(self.current_datetime, self.beirut_tz)
        
        self.last_internet_status = is_internet_available()
        
        # Initialize DataSync
        self.data_sync = DataSync(self.current_datetime)
        self.sync_manager = SyncManager(self.time_sync, self.data_sync, self.current_datetime)

        # Connect signals
        self.sync_manager.sync_complete.connect(self.handle_sync_complete)
        self.sync_manager.time_updated.connect(self.handle_time_update)
        self.sync_manager.time_incremented.connect(self.handle_time_increment)

        # Create loading screen and manager
        self.loading_screen = LoadingScreen()
        self.loading_manager = LoadingManager(self.loading_screen, self)
        self.loading_screen.show()
        
        # Start loading sequence
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
        self.setWindowTitle("Silver Attendance")
        
        # Set window icon
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'images', 'sys_icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'images', 'sys_icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        
        main_layout = QVBoxLayout()

        # Logo
        logo_label = QLabel(self)
        pixmap = QPixmap(resource_path("images/logo.png"))
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        # Date and time display
        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.datetime_label)

        # Create table and set up its properties
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Scheduled In", "Work In", "Scheduled Out", "Work Off", "Hours"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table)

        # Initialize TableManager
        self.table_manager = TableManager(self.table, self.current_datetime, self.beirut_tz)
        self.table_manager.set_callbacks(
            handle_work_in_callback=self.handle_work_in,
            handle_work_off_callback=self.handle_work_off,
            show_error_callback=self.show_error_message
        )

        # Set the layout
        self.setLayout(main_layout)

        # FINALLY refresh the table
        self.table_manager.refresh(force=True)

    def check_data_sync(self):
        """Handler for data sync timer"""
        try:
            if self.data_sync.check_and_sync(self.current_datetime):
                self.table_manager.refresh(force=True)
        except Exception as e:
            print(f"Error during periodic data sync: {str(e)}")

    def sync_data(self):
        """Method for manual data sync"""
        try:
            if self.data_sync.sync_data(self.current_datetime):
                self.table_manager.refresh(force=True)
        except Exception as e:
            print(f"Error during manual data sync: {str(e)}")


    def handle_work_in(self, row, staff_id):
        if self.work_time_manager.handle_work_in(row, staff_id, self.show_error_message):
            self.table_manager.refresh(force=True)

    def handle_work_off(self, row, staff_id, work_in_time):
        if self.work_time_manager.handle_work_off(row, staff_id, work_in_time, self.show_error_message):
            self.table_manager.refresh(force=True)

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_window(self):
        # Refresh window icon
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'images', 'sys_icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'images', 'sys_icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        self.showNormal()  # Restore the window if it was minimized
        self.showMaximized()  # Maximize the window
        self.activateWindow()  # Bring the window to the foreground
        self.raise_()  # Raise the window to the top of the window stack 

    def setup_system_tray(self):
        """Set up the system tray icon and menu"""
        # Create the system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'images', 'sys_icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'images', 'sys_icon.ico')
        
        self.tray_icon.setIcon(QIcon(icon_path))
        
        # Create the menu
        tray_menu = QMenu()
        
        # Add menu items
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show_window)
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.close_application)
        
        # Set the menu for the tray icon
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show the tray icon
        self.tray_icon.show()

    def close_application(self):
        self.sync_manager.stop_timers()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        minimize_to_taskbar(self)
        self.tray_icon.showMessage("Silver Attendance", "Application minimized to taskbar", QSystemTrayIcon.Information, 2000)
        