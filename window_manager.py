import os
import sys
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QTableWidget, QHeaderView, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
from utilities import resource_path

class WindowManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.table = None  # Will be initialized during setup
        self.tray_icon = None
        
    def setup_window(self):
        """Set up the main window properties and layout"""
        self.setup_window_properties()
        main_layout = self.create_layout()
        self.main_window.setLayout(main_layout)
        
    def setup_window_properties(self):
        """Set up window title, icon, and flags"""
        self.main_window.setWindowTitle("Silver Attendance")
        self.set_window_icon()
        self.main_window.setWindowFlags(
            self.main_window.windowFlags() | 
            Qt.WindowMinimizeButtonHint | 
            Qt.WindowMaximizeButtonHint
        )
        
    def set_window_icon(self):
        """Set the window icon"""
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'images', 'sys_icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'images', 'sys_icon.ico')
        self.main_window.setWindowIcon(QIcon(icon_path))
        
    def create_layout(self):
        """Create and return the main window layout"""
        main_layout = QVBoxLayout()
        
        # Add logo
        logo_label = self.create_logo_label()
        main_layout.addWidget(logo_label)
        
        # Add datetime label
        self.main_window.datetime_label = QLabel()
        self.main_window.datetime_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.main_window.datetime_label)
        
        # Create and add table
        self.table = self.create_table()
        main_layout.addWidget(self.table)
        
        return main_layout
        
    def create_logo_label(self):
        """Create and return the logo label"""
        logo_label = QLabel(self.main_window)
        pixmap = QPixmap(resource_path("images/logo.png"))
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        return logo_label
        
    def create_table(self):
        """Create and set up the table widget"""
        table = QTableWidget(self.main_window)
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Name", "Scheduled In", "Work In", 
            "Scheduled Out", "Work Off", "Hours"
        ])
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        return table

    def setup_system_tray(self):
        """Set up the system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self.main_window)
        
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
        quit_action.triggered.connect(self.main_window.close_application)
        
        # Set the menu for the tray icon
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show the tray icon
        self.tray_icon.show()

    def show_window(self):
        """Show and maximize the main window"""
        # Refresh window icon
        self.set_window_icon()
        
        self.main_window.showNormal()  # Restore the window if it was minimized
        self.main_window.showMaximized()  # Maximize the window
        self.main_window.activateWindow()  # Bring the window to the foreground
        self.main_window.raise_()  # Raise the window to the top of the window stack

    def minimize_to_taskbar(self):
        """Minimize the window to taskbar and system tray"""
        self.main_window.setWindowState(self.main_window.windowState() | Qt.WindowMinimized)
        self.main_window.hide()  # This hides from taskbar but keeps in system tray

    def show_tray_message(self, title, message, icon=QSystemTrayIcon.Information, duration=2000):
        """Show a system tray message"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, duration)

    def closeEvent(self, event):
        """Handle window close event"""
        event.ignore()
        self.main_window.minimize_to_taskbar()
        self.main_window.show_tray_message(
            "Silver Attendance",
            "Application minimized to taskbar"
        )