# functions.py
import socket

def is_internet_available():
    hosts = [
            ("8.8.8.8", 53),        # Google DNS
            ("1.1.1.1", 53),        # Cloudflare DNS
            ("208.67.222.222", 53), # OpenDNS
        ]
        
    for host, port in hosts:
        try:
            socket.create_connection((host, port), timeout=2)
            return True
        except OSError:
            continue
            
    try:
        # As a final fallback, try to resolve a reliable domain
        socket.gethostbyname("google.com")
        return True
    except OSError:
        return False