import os
import sys
import threading
from pytz import timezone
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QSystemTrayIcon, QMenu
from PyQt5.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import QTimer, Qt
from datetime import datetime, timedelta
from loading import LoadingScreen, LoadingSignals
from internet_conn import is_internet_available
from db_functions import fetch_all_staff, update_work_in, update_work_off
from methods import TimeSync, DataSync

class MainWindow(QWidget):
    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    
    def __init__(self):
        super().__init__()
        self.loading_signals = LoadingSignals()
        self.loading_signals.finished.connect(self.finish_loading)
        self.loading_signals.progress.connect(self.update_loading_progress)
        self.loading_signals.status.connect(self.update_loading_status)
        
        # Initialize TimeSync
        self.time_sync = TimeSync()
        self.beirut_tz = timezone('Asia/Beirut')
        self.current_datetime = self.time_sync.get_current_datetime()
        self.current_date = self.current_datetime.date()
        print(f"initialized date and time : {self.current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        # Initialize sync parameters
        self.sync_interval = 300  # 5 minutes in seconds
        self.retry_interval = 60  # 1 minute in seconds
        self.max_retries = 5
        self.retries = 0
        self.internet_check_interval = 30  # 30 seconds
        self.last_internet_status = is_internet_available()
        self.last_sync_attempt = self.current_datetime
        
        # Initialize DataSync
        self.data_sync = DataSync(self.current_datetime)
 
        # Create and show loading screen first
        self.loading_screen = LoadingScreen()
        self.loading_screen.show()
        
        # Initialize app with a slight delay to let loading screen appear
        QTimer.singleShot(100, self.initialize_app)

    def update_loading_progress(self, value):
        if hasattr(self, 'loading_screen') and self.loading_screen:
            self.loading_screen.set_progress(value)

    def update_loading_status(self, text):
        if hasattr(self, 'loading_screen') and self.loading_screen:
            self.loading_screen.set_loading_text(text)

    def finish_loading(self):
        try:
            if hasattr(self, 'loading_screen') and self.loading_screen:
                self.loading_screen.hide()
                self.loading_screen.deleteLater()
                self.loading_screen = None
            self.show_window()
        except Exception as e:
            print(f"Error during finish loading: {str(e)}")
            self.show_window()

    def initialize_app(self):
        # Basic initialization (10%)
        self.loading_screen.set_loading_text("Initializing application...")
        self.loading_screen.set_progress(10)
        
        # UI Setup (15%)
        self.loading_screen.set_loading_text("Setting up user interface...")
        self.loading_screen.set_progress(15)
        self.initUI()
        
        # System tray (20%)
        self.loading_screen.set_loading_text("Configuring system tray...")
        self.loading_screen.set_progress(20)
        self.setup_system_tray()
        
        # Timers (25%)
        self.loading_screen.set_loading_text("Initializing timers...")
        self.loading_screen.set_progress(25)
        self.setup_timers()
        
        # Data sync (30-70%)
        self.loading_screen.set_loading_text("Syncing data...")
        self.loading_screen.set_progress(30)
        self.sync_data()
        self.loading_screen.set_progress(70)

        # Time sync (75-95%)
        self.loading_screen.set_loading_text("Updating time...")
        self.loading_screen.set_progress(75)
        self.current_datetime = self.time_sync.sync_with_system_time()
        
        self.loading_signals.status.emit("Syncing with NTP servers...")
        
        def perform_ntp_sync():
            try:
                ntp_time = self.time_sync.sync_with_ntp()
                if ntp_time:
                    self.current_datetime = ntp_time
                    self.loading_signals.progress.emit(85)
                
                self.loading_signals.progress.emit(95)
                self.loading_signals.status.emit("Loading complete!")
                self.loading_signals.progress.emit(100)
                
                # Signal completion
                self.loading_signals.finished.emit()
                
            except Exception as e:
                print(f"Error during NTP sync: {str(e)}")
                self.loading_signals.progress.emit(95)
                self.loading_signals.status.emit("Loading complete!")
                self.loading_signals.progress.emit(100)
                self.loading_signals.finished.emit()

        # Start NTP sync in background thread
        threading.Thread(target=perform_ntp_sync, daemon=True).start()

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
        pixmap = QPixmap(self.resource_path("images/logo.png"))
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        # Date and time display
        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.datetime_label)

        # Create table
        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Scheduled In", "Work In", "Scheduled Out", "Work Off", "Hours"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table)

        self.setLayout(main_layout)
        self.populate_table()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(QIcon(self.resource_path("images/sys_icon.ico")), self)
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show_window)
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.close_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def setup_timers(self):
        # Timer for updating internal clock every second
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_time)
        self.clock_timer.start(1000)  # 1 second

        # Timer for periodic time syncing
        self.time_sync_timer = QTimer(self)
        self.time_sync_timer.timeout.connect(self.periodic_time_sync_attempt)
        self.time_sync_timer.start(self.sync_interval * 1000)

        # Timer for periodic data syncing - FIXED interval to match original
        self.data_sync_timer = QTimer(self)
        self.data_sync_timer.timeout.connect(self.check_data_sync)
        self.data_sync_timer.start(30 * 1000)  # 30 seconds, same as original

        # Timer for periodic internet connection check
        self.internet_check_timer = QTimer(self)
        self.internet_check_timer.timeout.connect(self.check_internet_and_sync)
        self.internet_check_timer.start(self.internet_check_interval * 1000)

    def update_time(self):
        self.current_datetime = self.time_sync.increment_time()
        date_str = self.current_datetime.strftime("%A %d/%m/%Y")
        time_str = self.current_datetime.strftime("%I:%M:%S %p")
        self.datetime_label.setText(f"{date_str}\n{time_str}")

        if self.current_datetime.date() != self.current_date:
            self.current_date = self.current_datetime.date()
            self.populate_table()

    def periodic_time_sync_attempt(self):
        if not is_internet_available():
            print("No internet connection. Skipping periodic time sync.")
            self.retry_time_sync()
            return

        ntp_time = self.time_sync.sync_with_ntp()
        if ntp_time:
            self.retries = 0  # Reset retry counter on success
            self.current_datetime = ntp_time
            print(f"Periodic time sync successful at {self.current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("Failed to sync time. Starting retry process...")
            self.retry_time_sync()

    def retry_time_sync(self):
        if self.retries < self.max_retries:
            self.retries += 1
            print(f"Retrying sync... Attempt {self.retries}/{self.max_retries}")
            
            if not is_internet_available():
                print(f"No internet connection during retry attempt {self.retries}. Will retry again...")
                QTimer.singleShot(self.retry_interval * 1000, self.periodic_time_sync_attempt)
                return

            ntp_time = self.time_sync.sync_with_ntp()
            if ntp_time:
                self.retries = 0
                self.current_datetime = ntp_time
                print(f"Time sync successful on retry attempt {self.retries}")
            else:
                print(f"Sync failed on retry attempt {self.retries}. Scheduling next retry...")
                QTimer.singleShot(self.retry_interval * 1000, self.periodic_time_sync_attempt)
        else:
            print(f"Maximum retry attempts ({self.max_retries}) reached. Falling back to system time...")
            self.time_sync.fallback_to_system_time()
            self.current_datetime = self.time_sync.get_current_datetime()

    def check_internet_and_sync(self):
        current_internet_status = is_internet_available()
        if current_internet_status and not self.last_internet_status:
            print("Internet connection restored. Initiating sync...")
            self.sync_time_and_data()
        self.last_internet_status = current_internet_status

    def check_data_sync(self):
        """Handler for data sync timer - now properly syncs every 2 minutes"""
        try:
            if self.data_sync.check_and_sync(self.current_datetime):
                self.populate_table()
        except Exception as e:
            print(f"Error during periodic data sync: {str(e)}")

    def sync_data(self):
        """Method for manual data sync"""
        try:
            if self.data_sync.sync_data(self.current_datetime):
                self.populate_table()
        except Exception as e:
            print(f"Error during manual data sync: {str(e)}")

    def sync_time_and_data(self):
        ntp_time = self.time_sync.sync_with_ntp()
        if ntp_time:
            self.current_datetime = ntp_time
            print(f"Time synced successfully: {self.current_datetime}")
        else:
            print("Failed to sync time with NTP. Using current app time.")

        if self.data_sync.sync_data(self.current_datetime):
            self.populate_table()

    def populate_table(self):
        try:
            self.staff_data = fetch_all_staff(self.current_date.strftime("%Y-%m-%d"))
            self.table.setRowCount(0)
            row_height = 60

            for row, (staff_id, first_name, last_name, sched_in, sched_out, work_in, work_off, hours_worked, day_off, reason_id, open_schedule) in enumerate(self.staff_data):
                self.table.insertRow(row)
                self.table.setRowHeight(row, row_height)

                display_name = f"{first_name} {last_name[0]}."
                name_item = QTableWidgetItem(display_name)
                name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(row, 0, name_item)

                if day_off:
                    self.display_day_off(row)
                else:
                    # Convert times to AM/PM only for display
                    sched_in_display = self.format_time(sched_in)
                    sched_out_display = self.format_time(sched_out)
                    work_in_display = self.format_time(work_in)
                    work_off_display = self.format_time(work_off)
                    
                    # Scheduled In
                    sched_in_text = "Open" if open_schedule else (sched_in_display if sched_in else "")
                    self.table.setItem(row, 1, self.create_centered_item(sched_in_text))

                    # Work In
                    if not work_in:
                        self.create_work_in_button(row, staff_id, first_name, last_name, row_height)
                    else:
                        self.table.setItem(row, 2, self.create_work_time_item(work_in_display, sched_in_display if sched_in and not open_schedule else None))

                    # Scheduled Out
                    sched_out_text = "Open" if open_schedule else (sched_out_display if sched_out else "")
                    self.table.setItem(row, 3, self.create_centered_item(sched_out_text))

                    # Work Off
                    if work_in and not work_off:
                        self.create_work_off_button(row, staff_id, first_name, last_name, work_in, row_height)
                    elif work_off:
                        self.table.setItem(row, 4, self.create_work_time_item(work_off_display, sched_out_display if sched_out and not open_schedule else None, is_work_off=True))

                    # Hours
                    if hours_worked is not None:
                        hours_display = f"{hours_worked:.2f}"  # Display with 2 decimal places
                    else:
                        hours_display = ""
                    hours_item = self.create_centered_item(hours_display)
                    self.table.setItem(row, 5, hours_item)

        except Exception as e:
            self.show_error_message(f"Error populating table: {str(e)}")

    def create_work_time_item(self, work_time, scheduled_time, is_work_off=False):
        item = self.create_centered_item(work_time)
        if work_time and scheduled_time:
            time_difference = self.compare_times(work_time, scheduled_time)
            if is_work_off:
                if time_difference < 0:
                    item.setBackground(Qt.red)
                else:
                    item.setBackground(Qt.green)
            else:
                if time_difference > 0:
                    item.setBackground(Qt.red)
                else:
                    item.setBackground(Qt.green)
            item.setForeground(Qt.white)
        else:
            item.setForeground(Qt.black)
        item.setFont(self.bold_font())
        return item

    def display_day_off(self, row):
        self.table.setSpan(row, 1, 1, 5)
        day_off_item = QTableWidgetItem("DAY OFF")
        day_off_item.setTextAlignment(Qt.AlignCenter)
        day_off_item.setBackground(Qt.lightGray)
        day_off_item.setFont(self.bold_font())
        self.table.setItem(row, 1, day_off_item)

    def create_centered_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def create_work_in_button(self, row, staff_id, first_name, last_name, row_height):
        work_in_button = QPushButton(f"Work In")
        work_in_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_in_button.setFixedSize(120, int(row_height * 0.8))
        work_in_button.clicked.connect(lambda: self.handle_work_in(row, staff_id))
        self.table.setCellWidget(row, 2, self.create_centered_widget(work_in_button))

    def create_work_off_button(self, row, staff_id, first_name, last_name, work_in_time, row_height):
        work_off_button = QPushButton(f"Work Off")
        work_off_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_off_button.setFixedSize(120, int(row_height * 0.8))
        work_off_button.clicked.connect(lambda: self.handle_work_off(row, staff_id, work_in_time))
        self.table.setCellWidget(row, 4, self.create_centered_widget(work_off_button))

    def create_centered_widget(self, widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        container.setLayout(layout)
        return container
    
    def compare_times(self, time_str1, time_str2):
        try:
            time1 = datetime.strptime(time_str1, "%I:%M %p")
            time2 = datetime.strptime(time_str2, "%I:%M %p")
            return (time1 - time2).total_seconds()
        except ValueError:
            print(f"Error comparing times: {time_str1} and {time_str2}")
            return 0
        
    def bold_font(self):
        font = QFont()
        font.setBold(True)
        return font

    def handle_work_in(self, row, staff_id):
        try:
            current_time = self.current_datetime.strftime("%H:%M:%S")  # 24-hour format
            update_work_in(staff_id, current_time, self.current_date.strftime("%Y-%m-%d"))
            self.populate_table()  # Refresh the table with updated data
        except Exception as e:
            self.show_error_message(f"Error recording Work In: {str(e)}")

    def handle_work_off(self, row, staff_id, work_in_time):
        try:
            if work_in_time is None:
                raise ValueError("Work In time is not available")

            # Ensure work_in_time is timezone-aware
            work_in_dt = datetime.strptime(work_in_time, "%H:%M:%S")
            work_in_full = self.beirut_tz.localize(datetime.combine(self.current_date, work_in_dt.time()))

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

            update_work_off(staff_id, work_off_time, hours_worked, self.current_date.strftime("%Y-%m-%d"))
            self.populate_table()  # Refresh the table with updated data
        except Exception as e:
            self.show_error_message(f"Error recording Work Off: {str(e)}")

    def format_time(self, time_str):
        if not time_str:
            return ""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M:%S")
            return time_obj.strftime("%I:%M %p")  # AM/PM format
        except ValueError:
            return time_str

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

    def minimize_to_taskbar(self):
        self.showMinimized()

    def close_application(self):
        self.clock_timer.stop()
        self.time_sync_timer.stop()  # Updated name
        self.data_sync_timer.stop()  # Updated name
        self.internet_check_timer.stop()  # Add this to properly clean up
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.minimize_to_taskbar()
        self.tray_icon.showMessage("Silver Attendance", "Application minimized to taskbar", QSystemTrayIcon.Information, 2000)