from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtCore import Qt
from db_functions import fetch_all_staff
from utilities import format_time
from ui_builders import bold_font, create_centered_item, create_work_time_item, create_centered_widget

class TableManager:
    def __init__(self, table_widget, current_datetime, beirut_tz):
        self.table = table_widget
        self.current_datetime = current_datetime
        self.beirut_tz = beirut_tz
        self.staff_data = None
        self.last_refresh_date = None
        # Store callbacks
        self.handle_work_in_callback = None
        self.handle_work_off_callback = None
        self.show_error_callback = None

    def set_callbacks(self, handle_work_in_callback, handle_work_off_callback, show_error_callback):
        """Set the callbacks for table interactions"""
        self.handle_work_in_callback = handle_work_in_callback
        self.handle_work_off_callback = handle_work_off_callback
        self.show_error_callback = show_error_callback

    def refresh(self, force=False):
        """
        Refresh the table data and display.
        Args:
            force (bool): If True, refreshes regardless of whether data has changed
        """
        if not all([self.handle_work_in_callback, self.handle_work_off_callback, self.show_error_callback]):
            print("Error: Callbacks not set for TableManager")
            return False

        current_date = self.current_datetime.date()
        
        try:
            # Only refresh if date has changed or force=True
            if force or self.last_refresh_date != current_date:
                new_data = fetch_all_staff(current_date.strftime("%Y-%m-%d"))
                
                # Check if data has actually changed
                if force or self._has_data_changed(new_data):
                    self.staff_data = new_data
                    self._rebuild_table()
                    self.last_refresh_date = current_date
                    return True
                    
        except Exception as e:
            self.show_error_callback(f"Error refreshing table: {str(e)}")
            return False
                
        return False

    def _has_data_changed(self, new_data):
        """Check if the new data is different from current data."""
        if self.staff_data is None:
            return True
            
        if len(self.staff_data) != len(new_data):
            return True
            
        # Compare each row's key data
        for old_row, new_row in zip(self.staff_data, new_data):
            if (old_row[2:8] != new_row[2:8]):  # Compare relevant fields
                return True
                
        return False

    def _rebuild_table(self):
        """Rebuild the entire table with current data"""
        self.table.setRowCount(0)
        row_height = 60

        for row, (staff_id, first_name, last_name, sched_in, sched_out, 
                 work_in, work_off, hours_worked, day_off, open_schedule) in enumerate(self.staff_data):
                     
            self.table.insertRow(row)
            self.table.setRowHeight(row, row_height)

            # Build name column
            self._build_name_column(row, first_name, last_name)

            if day_off:
                self._display_day_off(row)
            else:
                self._build_schedule_columns(row, sched_in, sched_out, work_in, 
                                          work_off, hours_worked, staff_id, row_height,
                                          open_schedule)

    def _build_name_column(self, row, first_name, last_name):
        """Build the name column"""
        display_name = f"{first_name} {last_name[0]}."
        name_item = QTableWidgetItem(display_name)
        name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, 0, name_item)

    def _build_schedule_columns(self, row, sched_in, sched_out, work_in, 
                              work_off, hours_worked, staff_id, row_height, open_schedule):
        """Build all schedule-related columns"""
        # Convert times to AM/PM for display
        sched_in_display = format_time(sched_in)
        sched_out_display = format_time(sched_out)
        work_in_display = format_time(work_in)
        work_off_display = format_time(work_off)
        
        # Scheduled In
        sched_in_text = "Open" if open_schedule else (sched_in_display if sched_in else "")
        self.table.setItem(row, 1, create_centered_item(sched_in_text))

        # Work In
        if not work_in:
            self._create_work_in_button(row, staff_id, row_height)
        else:
            self.table.setItem(row, 2, create_work_time_item(work_in_display, 
                             sched_in_display if sched_in and not open_schedule else None))

        # Scheduled Out
        sched_out_text = "Open" if open_schedule else (sched_out_display if sched_out else "")
        self.table.setItem(row, 3, create_centered_item(sched_out_text))

        # Work Off
        if work_in and not work_off:
            self._create_work_off_button(row, staff_id, work_in, row_height)
        elif work_off:
            self.table.setItem(row, 4, create_work_time_item(work_off_display, 
                             sched_out_display if sched_out and not open_schedule else None, 
                             is_work_off=True))

        # Hours
        hours_display = f"{hours_worked:.2f}" if hours_worked is not None else ""
        self.table.setItem(row, 5, create_centered_item(hours_display))

    def _display_day_off(self, row):
        self.table.setSpan(row, 1, 1, 5)
        day_off_item = QTableWidgetItem("DAY OFF")
        day_off_item.setTextAlignment(Qt.AlignCenter)
        day_off_item.setBackground(Qt.lightGray)
        day_off_item.setFont(bold_font())
        self.table.setItem(row, 1, day_off_item)

    def _create_work_in_button(self, row, staff_id, row_height):
        work_in_button = QPushButton("Work In")
        work_in_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_in_button.setFixedSize(120, int(row_height * 0.8))
        work_in_button.clicked.connect(lambda: self.handle_work_in_callback(row, staff_id))
        self.table.setCellWidget(row, 2, create_centered_widget(work_in_button))

    def _create_work_off_button(self, row, staff_id, work_in_time, row_height):
        work_off_button = QPushButton("Work Off")
        work_off_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_off_button.setFixedSize(120, int(row_height * 0.8))
        work_off_button.clicked.connect(lambda: self.handle_work_off_callback(row, staff_id, work_in_time))
        self.table.setCellWidget(row, 4, create_centered_widget(work_off_button))

    def update_current_datetime(self, current_datetime):
        """Update the current datetime used by the manager"""
        self.current_datetime = current_datetime