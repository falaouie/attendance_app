import sys
import os
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget
from ui_components import MainWindow
from db_manager import init_db
from internet_conn import is_internet_available

def check_database_exists():
    """Check if the SQLite database file exists"""
    db_path = "attendance.db"
    return os.path.exists(db_path)

def show_first_time_setup_error(parent):
    """Show error message when no internet on first run"""
    QMessageBox.critical(
        parent,
        "No Internet Connection",
        # "This is the first time running the application.\n"
        "Internet connection is required for first time setup.\n"
        "Please connect to the internet and restart the application.",
        QMessageBox.Ok
    )

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Silver Attendance")
        
        # Create a dummy widget for showing messages
        dummy = QWidget()
        
        # Check database before initialization
        if not check_database_exists():
            # On first run, check internet connection first
            if not is_internet_available():
                show_first_time_setup_error(dummy)
                sys.exit(1)
            # If we have internet, continue without warning
            
        # Only initialize database if checks pass
        init_db()  # Initialize the database
        
        # Create absolute path to icon
        if hasattr(sys, '_MEIPASS'):
            # Running as exe
            icon_path = os.path.join(sys._MEIPASS, 'images', 'sys_icon.ico')
        else:
            # Running as script
            icon_path = os.path.join(os.path.dirname(__file__), 'images', 'sys_icon.ico')
            
        # Set application icon
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        
        # Create the main window instance
        window = MainWindow()
        
        # Set window icon explicitly
        window.setWindowIcon(app_icon)
        
        # Start the application
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred while starting the application: {str(e)}")
        sys.exit(1)