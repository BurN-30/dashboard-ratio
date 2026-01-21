import json
import time
import os
import ftplib
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# --- 1. FORCER LE DOSSIER DE TRAVAIL (Indispensable pour l'automatisation) ---
# Cela permet au script de trouver les JSON même s'il est lancé par Windows
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Charger les variables d'environnement depuis .env
load_dotenv()

# --- CONFIGURATION FTP ---
FTP_HOST = REDACTED"FTP_HOST")
FTP_USER = REDACTED"FTP_USER")
FTP_PASS = REDACTED"FTP_PASS")
FTP_DIR  = REDACTED"FTP_DIR")

# --- CONFIGURATION FICHIER ---
OUTPUT_FILE = "stats.json"
HISTORY_FILE = "history.json"

# --- CONFIGURATION SITES ---
SITES = [
    {
        "name": "Generation-Free",
        "login_url": "https://generation-free.org/login",
        "profile_url": f"https://generation-free.org/users/{REDACTED'GF_USERNAME')}", 
        "username": REDACTED"GF_USER"),
        "password": REDACTED"GF_PASS"),
        "type": "unit3d"
    },
    {
        "name": "TheOldSchool",
        "login_url": "https://theoldschool.cc/login",
        "profile_url": f"https://theoldschool.cc/users/{REDACTED'TOS_USERNAME')}", 
        "username": REDACTED"TOS_USER"),
        "password": REDACTED"TOS_PASS"),
        "type": "unit3d"
    },
    {
        "name": "Sharewood",
        "login_url": "https://sharewood.tv/login",
        "profile_url": f"https://www.sharewood.tv/{REDACTED'SW_USERNAME')}",
        "username": REDACTED"SW_USER"),
        "password": REDACTED"SW_PASS"),
        "type": "sharewood"
    }
]

def clean(text):
    """Nettoie le texte (espaces, retours à la ligne) et convertit les unités"""
    if not text: return "0"
    text = text.replace('\xa0', ' ').replace('\u202f', ' ').strip().replace('\n', ' ')
    
    # Conversion des unités (Anglais -> Français)
    text = text.replace("TiB", "To")
    text = text.replace("GiB", "Go")
    text = text.replace("MiB", "Mo")
    text = text.replace("KiB", "Ko")
    
    # Remplacement de " B" par " o" (seulement si à la fin pour éviter les faux positifs)
    if text.endswith(" B"):
        text = text[:-1] + "o"
        
    return text

def format_duration(text):
    """Formate la durée en français et standardise l'affichage"""
    if not text or text == "0": return "0"
    
    # 1. Ajouter des espaces entre les chiffres et les lettres si absents (ex: 1M2S -> 1M 2S)
    text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
    
    # 1b. Ajouter des espaces entre les lettres et les chiffres (ex: M2 -> M 2)
    text = re.sub(r'([a-zA-Z]+)(\d+)', r'\1 \2', text)
    
    # 2. Nettoyer les espaces multiples
    text = text.replace("  ", " ").strip()
    
    # 3. Remplacements d'unités
    # Années
    text = re.sub(r'\b(\d+)\s*[Yy]\b', r'\1 an(s)', text)
    
    # Mois (M majuscule)
    text = re.sub(r'\b(\d+)\s*M\b', r'\1 mois', text)
    
    # Semaines (W ou S majuscule)
    text = re.sub(r'\b(\d+)\s*[Ww]\b', r'\1 sem', text)
    text = re.sub(r'\b(\d+)\s*S\b', r'\1 sem', text)
    
    # Jours
    text = re.sub(r'\b(\d+)\s*[Dd]\b', r'\1 j', text)
    text = re.sub(r'\b(\d+)\s*[Jj]\b', r'\1 j', text)
    
    # Heures
    text = re.sub(r'\b(\d+)\s*[Hh]\b', r'\1 h', text)
    
    # Minutes (m minuscule)
    text = re.sub(r'\b(\d+)\s*m\b', r'\1 min', text)
    
    # Secondes (s minuscule)
    text = re.sub(r'\b(\d+)\s*s\b', r'\1 s', text)
    
    return text

def get_unit3d_val(page, label, exact=False):
    """Cherche une valeur dans les listes key-value de UNIT3D"""
    # Use normalize-space to handle newlines and extra spaces in labels
    if exact:
        xpath = f'//dt[normalize-space(.)="{label}"]/following-sibling::dd'
    else:
        xpath = f'//dt[contains(normalize-space(.), "{label}")]/following-sibling::dd'
    try:
        # On laisse 1 seconde pour trouver l'élément (suffisant si la page est chargée)
        # au lieu de 30s par défaut qui bloquait tout si le champ était absent
        return clean(page.locator(xpath).first.inner_text(timeout=1000))
    except:
        return "0"

def scrape_sharewood(page):
    data = {}
    try:
        # 1. BARRE DU HAUT
        data['count_download'] = clean(page.inner_text('//span[contains(., "Total downloads")]')).split(':')[-1].strip()
        data['count_seed'] = clean(page.inner_text('//span[contains(., "Total en seed")]')).split(':')[-1].strip()
        data['count_leech'] = clean(page.inner_text('//span[contains(., "Total en leech")]')).split(':')[-1].strip()

        # 2. TABLEAU PRINCIPAL
        data['vol_download'] = clean(page.inner_text('span[data-original-title="Téléchargé"]'))
        
        try:
            up_total = clean(page.inner_text('span[data-original-title="Upload enregistré"]'))
            data['vol_upload'] = up_total 
        except:
            data['vol_upload'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Upload")]]]/td[2]'))

        data['ratio'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Ratio")]]]/td[2]'))
        data['buffer'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Capacité de DL")]]]/td[2]'))
        data['time_seed_total'] = format_duration(clean(page.inner_text('//tr[td[strong[contains(text(), "Temps total de seed")]]]/td[2]')))
        data['time_seed_avg'] = format_duration(clean(page.inner_text('//tr[td[strong[contains(text(), "Temps de seed moyen")]]]/td[2]')))

        # 3. SECTION EXTRA
        data['points_bonus'] = clean(page.inner_text('//strong[contains(., "Bonus")]/following-sibling::span'))
        data['fl_tokens'] = clean(page.inner_text('//strong[contains(., "Jetons FL")]/following-sibling::span'))
        data['hit_and_run'] = clean(page.inner_text('//strong[contains(., "Hit&Run")]/following-sibling::span'))
        
        # Warnings (Sharewood)
        try:
            # "Warnings Avertissements en cours : 0 / 3"
            warnings_text = clean(page.inner_text('//span[contains(., "Avertissements en cours")]'))
            # Extraction de "0 / 3"
            parts = warnings_text.split(":")[-1].strip().split("/")
            data['warnings_active'] = parts[0].strip()
            data['warnings_limit'] = parts[1].strip() if len(parts) > 1 else "3"
        except:
            data['warnings_active'] = "0"
            data['warnings_limit'] = "3"

    except Exception as e:
        print(f"⚠️ Erreur partielle Sharewood: {e}")
    
    return data

def scrape_unit3d(page, site_name):
    data = {}
    
    # AVERTISSEMENTS
    data['warnings_active'] = get_unit3d_val(page, "Avertissements actifs")
    data['hit_and_run'] = get_unit3d_val(page, "Hit and Run Count")
    if data['hit_and_run'] == "0":
         data['hit_and_run'] = get_unit3d_val(page, "Compteur de Hit and Run")
    
    # SEED STATS
    data['seed_time_total'] = format_duration(get_unit3d_val(page, "Durée totale des seeds"))
    if data['seed_time_total'] == "0": 
        data['seed_time_total'] = format_duration(get_unit3d_val(page, "Temps de seed total"))
        
    data['seed_time_avg'] = format_duration(get_unit3d_val(page, "Temps de seed moyen"))
    data['seed_size'] = get_unit3d_val(page, "Seeding Size")
    if data['seed_size'] == "0": data['seed_size'] = get_unit3d_val(page, "Volume de Seed")

    # TORRENT COUNT
    data['count_downloaded'] = get_unit3d_val(page, "Total des téléchargés")
    if data['count_downloaded'] == "0": data['count_downloaded'] = get_unit3d_val(page, "Total complétés")

    data['count_seed'] = get_unit3d_val(page, "Total en seed")
    data['count_leech'] = get_unit3d_val(page, "Total en leech")

    # TRAFFIC
    data['ratio'] = get_unit3d_val(page, "Ratio")
    data['real_ratio'] = get_unit3d_val(page, "Real Ratio")
    data['buffer'] = get_unit3d_val(page, "Tampon")
    
    data['vol_upload'] = get_unit3d_val(page, "Compte Envoyer (Total)")
    if data['vol_upload'] == "0": data['vol_upload'] = get_unit3d_val(page, "Compte Uploader (Total)")

    data['vol_download'] = get_unit3d_val(page, "Compte Télécharger (Total)")
    if data['vol_download'] == "0": data['vol_download'] = get_unit3d_val(page, "Compte Télécharger")

    # TORRENT TRAFFIC DETAILS
    data['torrent_uploader'] = get_unit3d_val(page, "Torrent Envoyer")
    if data['torrent_uploader'] == "0": data['torrent_uploader'] = get_unit3d_val(page, "Torrent Uploader")
    
    data['torrent_uploader_credited'] = get_unit3d_val(page, "Torrent Envoyer (Credité)")
    if data['torrent_uploader_credited'] == "0": data['torrent_uploader_credited'] = get_unit3d_val(page, "Torrent Uploader (Credité)")

    data['torrent_downloader'] = get_unit3d_val(page, "Torrent Télécharger")

    # RECOMPENSES / POINTS
    # Normalisation: on utilise 'points_bonus' pour tout le monde
    data['points_bonus'] = get_unit3d_val(page, "Coupon", exact=True)
    if data['points_bonus'] == "0" or data['points_bonus'] == "":
         data['points_bonus'] = get_unit3d_val(page, "Point Bonus", exact=True)
    
    data['fl_tokens'] = get_unit3d_val(page, "Jetons Freeleech")
    # data['thanks_given'] = get_unit3d_val(page, "Merci donné")
    # data['thanks_received'] = get_unit3d_val(page, "Merci reçu")
    
    # COMMUNITY / EXTRA
    # data['invitations'] = get_unit3d_val(page, "Invitations")
    # data['points_bonus_received'] = get_unit3d_val(page, "Points Bonus reçus")
    
    return data

def clean_history(history):
    """
    Optimise l'historique pour ne pas qu'il grossisse indéfiniment.
    - Moins de 30 jours : On garde TOUTES les entrées.
    - Plus de 30 jours : On ne garde qu'UNE entrée par jour.
    """
    if not history: return []

    now = time.time()
    thirty_days_ago = now - (30 * 24 * 3600)
    
    new_history = []
    seen_days = set()
    
    # On parcourt l'historique (du plus vieux au plus récent généralement)
    for entry in history:
        ts = entry.get('_timestamp')
        if not ts: continue
        
        if ts > thirty_days_ago:
            # C'est récent (moins de 30j) : on garde tout
            new_history.append(entry)
        else:
            # C'est vieux : on ne garde qu'une entrée par jour
            date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            if date_str not in seen_days:
                new_history.append(entry)
                seen_days.add(date_str)
    
    return new_history

def upload_to_ftp(files):
    """Upload une liste de fichiers vers le FTP"""
    print("--- ☁️  Upload FTP ---")
    if not all([FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR]):
        print("⚠️  Configuration FTP manquante dans .env (FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR)")
        return

    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)
            
            for file_name in files:
                if not os.path.exists(file_name):
                    print(f"⚠️  Fichier introuvable pour upload : {file_name}")
                    continue
                    
                print(f"-> Upload de {file_name}...")
                with open(file_name, 'rb') as f:
                    ftp.storbinary(f'STOR {file_name}', f)
                
                # Changer les permissions (lecture publique)
                try:
                    ftp.sendcmd(f'SITE CHMOD 644 {file_name}')
                except:
                    pass # Certains serveurs FTP ne supportent pas CHMOD
                    
            print("✅ Upload terminé avec succès.")
            
    except Exception as e:
        print(f"❌ Erreur FTP: {e}")

def main():
    final_data = {}

    # 1. SCRAPING
    print("--- 🕷️ Démarrage du scraping ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for site in SITES:
            print(f"-> Traitement de : {site['name']}")
            try:
                page.goto(site['login_url'])
                try:
                    if page.locator('input[name="username"]').count() > 0:
                        if not site['username'] or not site['password']:
                            print(f"   ⚠️  Identifiants manquants pour {site['name']} (Vérifiez le fichier .env)")
                        else:
                            page.fill('input[name="username"]', site['username'])
                            page.fill('input[name="password"]', site['password'])
                            page.press('input[name="password"]', 'Enter')
                            page.wait_for_load_state('networkidle')
                except Exception as login_err:
                    print(f"   Info Login: {login_err}")
                
                page.goto(site['profile_url'])
                time.sleep(2) 

                if site['type'] == 'sharewood':
                    final_data[site['name']] = scrape_sharewood(page)
                else:
                    final_data[site['name']] = scrape_unit3d(page, site['name'])
                
                print(f"   ✅ OK")

            except Exception as e:
                print(f"   ❌ Erreur: {e}")

        browser.close()

    # 2. SAUVEGARDE LOCALE
    # Ajout du timestamp
    final_data["_timestamp"] = int(time.time())

    # --- GESTION HISTORIQUE ---
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = [] # Si fichier corrompu
    
    # Ajouter les nouvelles data
    history.append(final_data)
    
    # Nettoyer
    history = clean_history(history)
    
    # Sauvegarder Stats
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
    
    # Sauvegarder Historique
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

    print("✅ Sauvegarde locale effectuée (stats + history).")

    # 3. UPLOAD FTP
    upload_to_ftp([OUTPUT_FILE, HISTORY_FILE])

if __name__ == "__main__":
    main()