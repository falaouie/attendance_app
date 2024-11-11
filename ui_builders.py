
from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from utilities import compare_times

def create_centered_item(text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

def create_work_time_item(work_time, scheduled_time, is_work_off=False):
        item = create_centered_item(work_time)
        if work_time and scheduled_time:
            time_difference = compare_times(work_time, scheduled_time)
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
        item.setFont(bold_font())
        return item

def create_centered_widget(widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        container.setLayout(layout)
        return container

def bold_font():
        font = QFont()
        font.setBold(True)
        return font