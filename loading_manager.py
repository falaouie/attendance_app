from PyQt5.QtCore import QTimer
from Classes import NTPSyncWorker 

class LoadingManager:
    def __init__(self, loading_screen, main_window):
        self.loading_screen = loading_screen
        self.main_window = main_window
        
    def update_progress(self, value):
        """Update loading progress bar"""
        if self.loading_screen:
            self.loading_screen.set_progress(value)

    def update_status(self, text):
        """Update loading status text"""
        if self.loading_screen:
            self.loading_screen.set_loading_text(text)

    def schedule_next_stage(self, delay, callback):
        """Helper function to chain delayed actions"""
        QTimer.singleShot(delay, callback)

    def start_loading_sequence(self):
        """Start the chain of loading stages"""
        self.stage1()

    def stage1(self):
        """Basic initialization (10%)"""
        self.update_status("Initializing application...")
        self.update_progress(10)
        self.schedule_next_stage(0, self.stage2)

    def stage2(self):
        """UI Setup (15%)"""
        self.update_status("Setting up user interface...")
        self.update_progress(15)
        self.main_window.initUI()
        self.schedule_next_stage(0, self.stage3)

    def stage3(self):
        """System tray (20%)"""
        self.update_status("Configuring system tray...")
        self.update_progress(20)
        self.main_window.setup_system_tray()
        self.schedule_next_stage(0, self.stage4)

    def stage4(self):
        """Application services (25%)"""
        self.update_status("Initializing application services...")
        self.update_progress(25)
        self.schedule_next_stage(0, self.stage5)

    def stage5(self):
        """Start Data sync (30%)"""
        self.update_status("Starting data synchronization...")
        self.update_progress(30)
        self.schedule_next_stage(0, self.stage6)

    def stage6(self):
        """Data sync progress (50%)"""
        self.update_status("Syncing data...")
        self.update_progress(50)
        self.main_window.sync_data()
        self.schedule_next_stage(0, self.stage7)

    def stage7(self):
        """Data sync completion (70%)"""
        self.update_status("Completing data synchronization...")
        self.update_progress(70)
        self.schedule_next_stage(0, self.stage8)

    def stage8(self):
        """Time sync (75%)"""
        self.update_status("Updating time...")
        self.update_progress(75)
        self.main_window.current_datetime = self.main_window.time_sync.sync_with_system_time()
        self.main_window.sync_manager.update_current_datetime(self.main_window.current_datetime)
        self.schedule_next_stage(0, self.stage9)

    def stage9(self):
        """NTP sync (85%)"""
        self.main_window.loading_signals.status.emit("Preparing NTP sync...")
        self.main_window.loading_signals.progress.emit(85)
        
        # Create and configure the NTP sync worker - fixed reference
        self.main_window.ntp_worker = NTPSyncWorker(self.main_window.time_sync)
        
        # Connect worker signals
        self.main_window.ntp_worker.finished.connect(self.main_window.handle_ntp_sync_complete)
        self.main_window.ntp_worker.progress.connect(
            lambda v: self.main_window.loading_signals.progress.emit(v)
        )
        self.main_window.ntp_worker.status.connect(
            lambda s: self.main_window.loading_signals.status.emit(s)
        )
        
        # Start the worker
        self.main_window.ntp_worker.start()

    def finish_loading(self):
        """Clean up loading screen"""
        try:
            if self.loading_screen:
                self.loading_screen.hide()
                self.loading_screen.deleteLater()
                self.loading_screen = None
            self.main_window.show_window()
        except Exception as e:
            print(f"Error during finish loading: {str(e)}")
            self.main_window.show_window()