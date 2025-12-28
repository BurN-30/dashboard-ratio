from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
import subprocess
import os
import sys
import threading
import time
from datetime import datetime

app = FastAPI()

# --- CONFIGURATION ---
SECRET_TOKEN = os.getenv("TRIGGER_TOKEN", "301101230669")
SCRAPE_INTERVAL_HOURS = 6  # Fréquence automatique

# Verrou global
is_scraping_running = False

def run_scraper_logic(source="Auto"):
    global is_scraping_running
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "scraper.py")
    
    print(f"[{datetime.now()}] 🔒 Verrou activé. Lancement ({source}) : {script_path}")
    
    try:
        # Force l'UTF-8 pour éviter les crashs émojis
        result = subprocess.run(
            [sys.executable, "scraper.py"], 
            cwd=base_dir,
            capture_output=True, 
            text=True, 
            check=True,
            encoding="utf-8",
            errors="replace"
        )
        print("✅ Scraper terminé avec succès.")
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
    finally:
        is_scraping_running = False
        print("🔓 Verrou libéré.")

# --- TÂCHE DE FOND : BOUCLE 6 HEURES ---
def scheduled_loop():
    print(f"⏰ Planificateur démarré : Scraping toutes les {SCRAPE_INTERVAL_HOURS}h.")
    while True:
        # On attend 6h (en secondes)
        time.sleep(SCRAPE_INTERVAL_HOURS * 3600)
        if not is_scraping_running:
            run_scraper_logic(source="Timer 6h")

# Lancement du thread parallèle au démarrage
@app.on_event("startup")
def start_schedule():
    thread = threading.Thread(target=scheduled_loop, daemon=True)
    thread.start()

# --- API VERCEL ---
@app.post("/run-scraper")
async def trigger_scraper(background_tasks: BackgroundTasks, x_token: str = Header(None)):
    global is_scraping_running
    if x_token != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Token invalide")
    if is_scraping_running:
        return {"status": "busy", "message": "Déjà en cours."}

    is_scraping_running = True
    background_tasks.add_task(run_scraper_logic, source="Vercel")
    return {"status": "launched", "message": "Scraper lancé."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)