from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Response
from contextlib import asynccontextmanager
import subprocess
import os
import sys
import threading
import time
from datetime import datetime
import requests
# --- ROUTES API ---
@app.get("/hardware-proxy")
async def hardware_proxy():
    """
    Proxy temps réel vers l'API .NET locale (http://localhost:5056/api/stats)
    Timeout court (2s). Renvoie le JSON tel quel.
    """
    try:
        resp = requests.get("http://localhost:5056/api/stats", timeout=2)
        resp.raise_for_status()
        return Response(content=resp.content, media_type="application/json")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Erreur proxy: {e}")

# --- CONFIGURATION ---
SECRET_TOKEN = os.getenv("TRIGGER_TOKEN", "301101230669")
SCRAPE_INTERVAL_HOURS = 6
is_scraping_running = False

# --- LOGIQUE SCRAPER ---
def run_scraper_logic(source="Auto"):
    global is_scraping_running
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"[{datetime.now()}] 🔒 Verrou activé. Lancement ({source})")
    
    try:
        # Lancement du scraper en sous-processus
        subprocess.run(
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

# --- TÂCHE DE FOND (THREAD) ---
def scheduled_loop():
    print(f"⏰ Planificateur démarré : Scraping toutes les {SCRAPE_INTERVAL_HOURS}h.")
    while True:
        # Attente initiale de 6h pour ne pas bloquer le démarrage
        time.sleep(SCRAPE_INTERVAL_HOURS * 3600)
        if not is_scraping_running:
            run_scraper_logic(source="Timer 6h")

# --- NOUVELLE GESTION DU DÉMARRAGE (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ce code s'exécute au démarrage
    thread = threading.Thread(target=scheduled_loop, daemon=True)
    thread.start()
    yield
    # Ce code s'exécute à l'arrêt (optionnel)
    print("🛑 Arrêt du serveur.")

app = FastAPI(lifespan=lifespan)

# --- ROUTES API ---
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
    # On utilise le port 8888 qui est beaucoup moins capricieux que 8010/8011
    uvicorn.run(app, host="0.0.0.0", port=8888)