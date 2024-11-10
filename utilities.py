# utilities.py
import os
import sys
from datetime import datetime

def format_time(time_str):
        if not time_str:
            return ""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M:%S")
            return time_obj.strftime("%I:%M %p")  # AM/PM format
        except ValueError:
            return time_str
        
def compare_times(time_str1, time_str2):
        try:
            time1 = datetime.strptime(time_str1, "%I:%M %p")
            time2 = datetime.strptime(time_str2, "%I:%M %p")
            return (time1 - time2).total_seconds()
        except ValueError:
            print(f"Error comparing times: {time_str1} and {time_str2}")
            return 0

def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)