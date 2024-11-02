import sys
import os
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from ui_components import MainWindow
from db_manager import init_db


if __name__ == '__main__':
    try:
        init_db()  # Initialize the database
        app = QApplication(sys.argv)
        app.setApplicationName("Silver Attendance")
        
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
        
        # window.show()

        # Start the application
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred while starting the application: {str(e)}")
        sys.exit(1)
