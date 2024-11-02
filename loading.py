import sys
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QDesktopWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, pyqtSignal

class LoadingSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout()
        
        # Logo
        logo_label = QLabel()

        # Get correct path whether running as script or exe
        if hasattr(sys, '_MEIPASS'):
            # Running as exe
            logo_path = os.path.join(sys._MEIPASS, 'images', 'logo.png')
        else:
            # Running as script
            logo_path = os.path.join(os.path.dirname(__file__), 'images', 'logo.png')
        
        pixmap = QPixmap(logo_path)
        scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)
        
        # Loading text
        self.loading_label = QLabel("Initializing...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #2196F3; font-size: 14px;")
        layout.addWidget(self.loading_label)
        
        self.setLayout(layout)
        self.center()
        
    def set_loading_text(self, text):
        self.loading_label.setText(text)
        
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def set_progress(self, value):
        self.progress.setValue(value)