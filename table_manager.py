# table_manager.py
# from datetime import datetime
from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from PyQt5.QtCore import Qt
from db_functions import fetch_all_staff
from utilities import format_time
from ui_builders import bold_font, create_centered_item, create_work_time_item, create_centered_widget

class TablePopulator:
    def __init__(self, table_widget, current_datetime, beirut_tz):
        self.table = table_widget
        self.current_datetime = current_datetime
        self.beirut_tz = beirut_tz
        self.staff_data = None

    def populate_table(self, handle_work_in_callback, handle_work_off_callback, show_error_callback):
        try:
            self.staff_data = fetch_all_staff(self.current_datetime.date().strftime("%Y-%m-%d"))
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
                    self._display_day_off(row)
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
                        self._create_work_in_button(row, staff_id, first_name, last_name, row_height, handle_work_in_callback)
                    else:
                        self.table.setItem(row, 2, create_work_time_item(work_in_display, sched_in_display if sched_in and not open_schedule else None))

                    # Scheduled Out
                    sched_out_text = "Open" if open_schedule else (sched_out_display if sched_out else "")
                    self.table.setItem(row, 3, create_centered_item(sched_out_text))

                    # Work Off
                    if work_in and not work_off:
                        self._create_work_off_button(row, staff_id, first_name, last_name, work_in, row_height, handle_work_off_callback)
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
            show_error_callback(f"Error populating table: {str(e)}")

    def _display_day_off(self, row):
        self.table.setSpan(row, 1, 1, 5)
        day_off_item = QTableWidgetItem("DAY OFF")
        day_off_item.setTextAlignment(Qt.AlignCenter)
        day_off_item.setBackground(Qt.lightGray)
        day_off_item.setFont(bold_font())
        self.table.setItem(row, 1, day_off_item)

    def _create_work_in_button(self, row, staff_id, first_name, last_name, row_height, callback):
        work_in_button = QPushButton(f"Work In")
        work_in_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_in_button.setFixedSize(120, int(row_height * 0.8))
        work_in_button.clicked.connect(lambda: callback(row, staff_id))
        self.table.setCellWidget(row, 2, create_centered_widget(work_in_button))

    def _create_work_off_button(self, row, staff_id, first_name, last_name, work_in_time, row_height, callback):
        work_off_button = QPushButton(f"Work Off")
        work_off_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        work_off_button.setFixedSize(120, int(row_height * 0.8))
        work_off_button.clicked.connect(lambda: callback(row, staff_id, work_in_time))
        self.table.setCellWidget(row, 4, create_centered_widget(work_off_button))