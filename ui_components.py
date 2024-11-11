import os
import sys
from pytz import timezone
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMessageBox, QSystemTrayIcon
from PyQt5.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt
from datetime import datetime, timedelta
from loading import LoadingScreen, LoadingSignals
from internet_conn import is_internet_available
from db_functions import fetch_all_staff, update_work_in, update_work_off
from Classes import TimeSync, DataSync, NTPSyncWorker
from utilities import format_time, resource_path, setup_system_tray, minimize_to_taskbar
from ui_builders import create_centered_item, create_work_time_item, create_centered_widget, bold_font


class MainWindow(QWidget):
    
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
        # Initialize sync parameters - now just one interval
        self.sync_interval = 120  # 2 minutes in seconds
        self.retry_interval = 60  # 1 minute in seconds
        self.max_retries = 5
        self.retries = 0
        self.internet_check_interval = 30  # 30 seconds
        self.last_internet_status = is_internet_available()
        
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

    def initialize_app(self):
        # Helper function to chain delayed actions
        def schedule_next_stage(delay, callback):
            QTimer.singleShot(delay, callback)
        
        # Stage 1: Basic initialization (10%)
        def stage1():
            self.loading_screen.set_loading_text("Initializing application...")
            self.loading_screen.set_progress(10)
            schedule_next_stage(0, stage2)  # put 1000 instead of 0 to Wait 1 second before next stage
        
        # Stage 2: UI Setup (15%)
        def stage2():
            self.loading_screen.set_loading_text("Setting up user interface...")
            self.loading_screen.set_progress(15)
            self.initUI()
            schedule_next_stage(0, stage3)
        
        # Stage 3: System tray (20%)
        def stage3():
            self.loading_screen.set_loading_text("Configuring system tray...")
            self.loading_screen.set_progress(20)
            setup_system_tray(self)
            schedule_next_stage(0, stage4)
        
        # Stage 4: Timers (25%)
        def stage4():
            self.loading_screen.set_loading_text("Initializing timers...")
            self.loading_screen.set_progress(25)
            self.setup_timers()
            schedule_next_stage(0, stage5)
        
        # Stage 5: Start Data sync (30%)
        def stage5():
            self.loading_screen.set_loading_text("Starting data synchronization...")
            self.loading_screen.set_progress(30)
            schedule_next_stage(0, stage6)
        
        # Stage 6: Data sync progress (50%)
        def stage6():
            self.loading_screen.set_loading_text("Syncing data...")
            self.loading_screen.set_progress(50)
            self.sync_data()
            schedule_next_stage(0, stage7)
        
        # Stage 7: Data sync completion (70%)
        def stage7():
            self.loading_screen.set_loading_text("Completing data synchronization...")
            self.loading_screen.set_progress(70)
            schedule_next_stage(0, stage8)
        
        # Stage 8: Time sync (75%)
        def stage8():
            self.loading_screen.set_loading_text("Updating time...")
            self.loading_screen.set_progress(75)
            self.current_datetime = self.time_sync.sync_with_system_time()
            schedule_next_stage(0, stage9)
        
        # Stage 9: NTP sync (85%)
        def stage9():
            self.loading_signals.status.emit("Preparing NTP sync...")
            self.loading_signals.progress.emit(85)
            
            # Create and configure the NTP sync worker
            self.ntp_worker = NTPSyncWorker(self.time_sync)
            
            # Connect worker signals
            self.ntp_worker.finished.connect(self.handle_ntp_sync_complete)
            self.ntp_worker.progress.connect(lambda v: self.loading_signals.progress.emit(v))
            self.ntp_worker.status.connect(lambda s: self.loading_signals.status.emit(s))
            
            # Start the worker
            self.ntp_worker.start()
        
        # Start the chain of stages
        stage1()

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

    def setup_timers(self):
        # Timer for updating internal clock every second
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_time)
        self.clock_timer.start(1000)  # 1 second

        # Single timer for sync operations
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.periodic_sync_attempt)
        self.sync_timer.setTimerType(Qt.PreciseTimer)
        self.sync_timer.start(self.sync_interval * 1000)

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
            print(f"Time sync successful at {self.current_datetime}")
            
            # Immediately sync data after successful time sync
            if self.data_sync.sync_data(self.current_datetime):
                self.populate_table()  # Refresh the display
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
                
                # Try data sync after successful time sync
                if self.data_sync.sync_data(self.current_datetime):
                    self.populate_table()
            else:
                print(f"Sync failed on retry attempt {self.retries}. Scheduling next retry...")
                QTimer.singleShot(self.retry_interval * 1000, self.periodic_sync_attempt)
        else:
            print(f"Maximum retry attempts ({self.max_retries}) reached. Falling back to system time...")
            self.time_sync.fallback_to_system_time()
            self.current_datetime = self.time_sync.get_current_datetime()

    def check_internet_and_sync(self):
        current_internet_status = is_internet_available()
        if current_internet_status and not self.last_internet_status:
            print("Internet connection restored. Initiating sync...")
            self.periodic_sync_attempt()  # Use the combined sync method
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

            for row, (staff_id, first_name, last_name, sched_in, sched_out, work_in, work_off, hours_worked, day_off, open_schedule) in enumerate(self.staff_data):
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
                    sched_in_display = format_time(sched_in)
                    sched_out_display = format_time(sched_out)
                    work_in_display = format_time(work_in)
                    work_off_display = format_time(work_off)
                    
                    # Scheduled In
                    sched_in_text = "Open" if open_schedule else (sched_in_display if sched_in else "")
                    self.table.setItem(row, 1, create_centered_item(sched_in_text))

                    # Work In
                    if not work_in:
                        self.create_work_in_button(row, staff_id, first_name, last_name, row_height)
                    else:
                        self.table.setItem(row, 2, create_work_time_item(work_in_display, sched_in_display if sched_in and not open_schedule else None))

                    # Scheduled Out
                    sched_out_text = "Open" if open_schedule else (sched_out_display if sched_out else "")
                    self.table.setItem(row, 3, create_centered_item(sched_out_text))

                    # Work Off
                    if work_in and not work_off:
                        self.create_work_off_button(row, staff_id, first_name, last_name, work_in, row_height)
                    elif work_off:
                        self.table.setItem(row, 4, create_work_time_item(work_off_display, sched_out_display if sched_out and not open_schedule else None, is_work_off=True))

                    # Hours
                    if hours_worked is not None:
                        hours_display = f"{hours_worked:.2f}"  # Display with 2 decimal places
                    else:
                        hours_display = ""
                    hours_item = create_centered_item(hours_display)
                    self.table.setItem(row, 5, hours_item)

        except Exception as e:
            self.show_error_message(f"Error populating table: {str(e)}")

    def display_day_off(self, row):
        self.table.setSpan(row, 1, 1, 5)
        day_off_item = QTableWidgetItem("DAY OFF")
        day_off_item.setTextAlignment(Qt.AlignCenter)
        day_off_item.setBackground(Qt.lightGray)
        day_off_item.setFont(bold_font())
        self.table.setItem(row, 1, day_off_item)

    def create_work_in_button(self, row, staff_id, first_name, last_name, row_height):
        work_in_button = QPushButton(f"Work In")
        work_in_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_in_button.setFixedSize(120, int(row_height * 0.8))
        work_in_button.clicked.connect(lambda: self.handle_work_in(row, staff_id))
        self.table.setCellWidget(row, 2, create_centered_widget(work_in_button))

    def create_work_off_button(self, row, staff_id, first_name, last_name, work_in_time, row_height):
        work_off_button = QPushButton(f"Work Off")
        work_off_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_off_button.setFixedSize(120, int(row_height * 0.8))
        work_off_button.clicked.connect(lambda: self.handle_work_off(row, staff_id, work_in_time))
        self.table.setCellWidget(row, 4, create_centered_widget(work_off_button))

    # def create_centered_widget(self, widget):
    #     container = QWidget()
    #     layout = QHBoxLayout(container)
    #     layout.addStretch()
    #     layout.addWidget(widget)
    #     layout.addStretch()
    #     container.setLayout(layout)
    #     return container

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

    def close_application(self):
        self.clock_timer.stop()
        self.sync_timer.stop()
        self.internet_check_timer.stop()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        minimize_to_taskbar(self)
        self.tray_icon.showMessage("Silver Attendance", "Application minimized to taskbar", QSystemTrayIcon.Information, 2000)
