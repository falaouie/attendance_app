class SignalHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        
    def setup_signals(self):
        """Set up all signal connections"""
        # Connect loading signals
        self.main_window.loading_signals.finished.connect(self.main_window.finish_loading)
        self.main_window.loading_signals.progress.connect(
            lambda v: self.main_window.loading_manager.update_progress(v)
        )
        self.main_window.loading_signals.status.connect(
            lambda s: self.main_window.loading_manager.update_status(s)
        )
        
        # Connect sync manager signals
        self.main_window.sync_manager.sync_complete.connect(self.handle_sync_complete)
        self.main_window.sync_manager.time_updated.connect(self.handle_time_update)
        self.main_window.sync_manager.time_incremented.connect(self.handle_time_increment)

    def handle_sync_complete(self, success):
        """Handle completion of sync operation"""
        if success:
            self.main_window.table_manager.refresh(force=True)
        else:
            # Handle sync failure
            if not self.main_window.is_internet_available():
                print("Sync failed: No internet connection")
            else:
                print("Sync failed: Unknown error")
    
    def handle_time_update(self, new_datetime):
        """Handle time update from sync"""
        self.main_window.current_datetime = new_datetime
        self.main_window.work_time_manager.update_current_datetime(new_datetime)
        self.update_datetime_display()
    
    def handle_time_increment(self, new_datetime):
        """Handle regular clock updates"""
        self.main_window.current_datetime = new_datetime
        self.main_window.work_time_manager.update_current_datetime(new_datetime)
        self.update_datetime_display()

        # Check for date change
        if self.main_window.current_datetime.date() != self.main_window.current_date:
            self.main_window.current_date = self.main_window.current_datetime.date()
            self.main_window.table_manager.refresh()

    def handle_ntp_sync_complete(self, ntp_time):
        """Handler for NTP sync completion"""
        if ntp_time:
            self.main_window.current_datetime = ntp_time
            print(f"NTP sync successful: {self.main_window.current_datetime}")
        else:
            print("NTP sync failed, using system time")
        
        # Clean up the worker
        if hasattr(self.main_window, 'ntp_worker'):
            self.main_window.ntp_worker.deleteLater()
        
        # Signal that loading is complete
        self.main_window.loading_signals.finished.emit()

    def update_datetime_display(self):
        """Update the datetime display in the UI"""
        if hasattr(self.main_window, 'datetime_label'):
            date_str = self.main_window.current_datetime.strftime("%A %d/%m/%Y")
            time_str = self.main_window.current_datetime.strftime("%I:%M:%S %p")
            self.main_window.datetime_label.setText(f"{date_str}\n{time_str}")