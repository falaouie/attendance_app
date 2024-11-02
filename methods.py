import ntplib
from datetime import datetime, timedelta, timezone as dt_timezone
from pytz import timezone
from internet_conn import is_internet_available

class TimeSync:
    def __init__(self):
        self.beirut_tz = timezone('Asia/Beirut')
        self.current_datetime = datetime.now(self.beirut_tz)
        self.time_difference_threshold = timedelta(minutes=5)
        self.ntp_servers = [
            'time.google.com',
            'pool.ntp.org',          # Global NTP pool
            'time.nist.gov',         # NIST's public time server
            'time.cloudflare.com',   # Cloudflare's NTP service
        ]
        
    def get_current_datetime(self):
        return self.current_datetime
    
    def increment_time(self):
        self.current_datetime += timedelta(seconds=1)
        return self.current_datetime
    
    def sync_with_system_time(self):
        system_time = datetime.now(self.beirut_tz)
        self.current_datetime = system_time
        return self.current_datetime

    def sync_with_ntp(self):
        if not is_internet_available():
            print("No internet connection. Cannot sync with NTP server.")
            return None

        last_error = None
        for server in self.ntp_servers:
            try:
                client = ntplib.NTPClient()
                response = client.request(server, version=3, timeout=5)
                ntp_time = datetime.fromtimestamp(response.tx_time, dt_timezone.utc)
                beirut_time = ntp_time.astimezone(self.beirut_tz)
                print(f"Successfully synced time with NTP server {server}. Current time: {beirut_time}")
                self.current_datetime = beirut_time
                return beirut_time
                
            except (ntplib.NTPException, OSError) as e:
                last_error = e
                print(f"Failed to sync with {server}: {str(e)}")
                continue
                
        # If we get here, all servers failed
        print(f"Failed to sync with all NTP servers. Last error: {str(last_error)}")
        return None

    def fallback_to_system_time(self):
        system_time = datetime.now(self.beirut_tz)
        time_difference = abs(system_time - self.current_datetime)

        if time_difference <= self.time_difference_threshold:
            self.current_datetime = system_time
            print(f"Synced with system time. Time difference was within threshold: {time_difference}")
        else:
            print(f"Time difference exceeds threshold. Using App time, Current time might be inaccurate. Difference: {time_difference}")