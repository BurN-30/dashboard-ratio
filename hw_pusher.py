import json
import time
import ftplib
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# --- CONFIGURATION ---
# Force working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_DIR  = os.getenv("FTP_DIR")
# Token pour l'API locale (doit correspondre à celui défini dans start_server.bat)
HWMONITOR_TOKEN = os.getenv("HWMONITOR_TOKEN")

LOCAL_API_URL = "http://localhost:5056/api/stats"
OUTPUT_FILE = "hardware.json"
UPLOAD_INTERVAL = 2 # seconds

def fetch_local_stats():
    try:
        headers = {}
        if HWMONITOR_TOKEN:
            headers["X-Api-Key"] = HWMONITOR_TOKEN
            
        response = requests.get(LOCAL_API_URL, headers=headers, timeout=1)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error fetching local stats: {e}")
    return None

def upload_to_ftp(data):
    try:
        # Save to local file first
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(data, f)

        # Upload to FTP
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)
            with open(OUTPUT_FILE, 'rb') as f:
                ftp.storbinary(f'STOR {OUTPUT_FILE}', f)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Uploaded {OUTPUT_FILE}")
    except Exception as e:
        print(f"FTP Error: {e}")

def main():
    print("Starting Hardware Monitor Pusher...")
    print(f"Monitoring: {LOCAL_API_URL}")
    print(f"Target: FTP {FTP_HOST}/{FTP_DIR}/{OUTPUT_FILE}")
    
    while True:
        stats = fetch_local_stats()
        if stats:
            upload_to_ftp(stats)
        else:
            print("No data from hwMonitor. Is it running?")
        
        time.sleep(UPLOAD_INTERVAL)

if __name__ == "__main__":
    main()
