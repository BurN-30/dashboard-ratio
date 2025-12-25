import json
import time
import ftplib
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# --- 1. FORCER LE DOSSIER DE TRAVAIL (Indispensable pour l'automatisation) ---
# Cela permet au script de trouver les JSON même s'il est lancé par Windows
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Charger les variables d'environnement depuis .env
load_dotenv()

# --- CONFIGURATION FICHIER ---
OUTPUT_FILE = "stats.json"
HISTORY_FILE = "history.json"

# --- CONFIGURATION FTP O2SWITCH ---
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_DIR  = os.getenv("FTP_DIR")

# --- CONFIGURATION SITES ---
SITES = [
    {
        "name": "Generation-Free",
        "login_url": "https://generation-free.org/login",
        "profile_url": "https://generation-free.org/users/REDACTED_USER", 
        "username": os.getenv("GF_USER"),
        "password": os.getenv("GF_PASS"),
        "type": "unit3d"
    },
    {
        "name": "TheOldSchool",
        "login_url": "https://theoldschool.cc/login",
        "profile_url": "https://theoldschool.cc/users/REDACTED_USER", 
        "username": os.getenv("TOS_USER"),
        "password": os.getenv("TOS_PASS"),
        "type": "unit3d"
    },
    {
        "name": "Sharewood",
        "login_url": "https://sharewood.tv/login",
        "profile_url": "https://www.sharewood.tv/REDACTED_USER.97438",
        "username": os.getenv("SW_USER"),
        "password": os.getenv("SW_PASS"),
        "type": "sharewood"
    }
]

def clean(text):
    """Nettoie le texte (espaces, retours à la ligne)"""
    if not text: return "0"
    return text.replace('\xa0', ' ').replace('\u202f', ' ').strip().replace('\n', ' ')

def get_unit3d_val(page, label):
    """Cherche une valeur dans les listes key-value de UNIT3D"""
    # Use normalize-space to handle newlines and extra spaces in labels
    xpath = f'//dt[contains(normalize-space(.), "{label}")]/following-sibling::dd'
    try:
        return clean(page.inner_text(xpath))
    except:
        return "0"

def scrape_sharewood(page):
    data = {}
    try:
        # 1. BARRE DU HAUT
        data['count_upload'] = clean(page.inner_text('//span[contains(., "Total uploads")]')).split(':')[-1].strip()
        data['count_download'] = clean(page.inner_text('//span[contains(., "Total downloads")]')).split(':')[-1].strip()
        data['count_seed'] = clean(page.inner_text('//span[contains(., "Total en seed")]')).split(':')[-1].strip()
        data['count_leech'] = clean(page.inner_text('//span[contains(., "Total en leech")]')).split(':')[-1].strip()

        # 2. TABLEAU PRINCIPAL
        data['vol_download'] = clean(page.inner_text('span[data-original-title="Téléchargé"]'))
        
        try:
            up_vrai = clean(page.inner_text('span[data-original-title="Vrai upload"]'))
            up_bonus = clean(page.inner_text('span[data-original-title="Upload échangé contre Bonus"]'))
            up_total = clean(page.inner_text('span[data-original-title="Upload enregistré"]'))
            data['vol_upload_detail'] = f"{up_vrai} + {up_bonus} = {up_total}"
            data['vol_upload'] = up_total 
        except:
            data['vol_upload'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Upload")]]]/td[2]'))

        data['ratio'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Ratio")]]]/td[2]'))
        data['buffer'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Capacité de DL")]]]/td[2]'))
        data['freeleech_pool'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Don Freeleech Pool")]]]/td[2]'))
        data['time_seed_total'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Temps total de seed")]]]/td[2]'))
        data['time_seed_avg'] = clean(page.inner_text('//tr[td[strong[contains(text(), "Temps de seed moyen")]]]/td[2]'))

        # 3. SECTION EXTRA
        data['points_bonus'] = clean(page.inner_text('//strong[contains(., "Bonus")]/following-sibling::span'))
        data['fl_tokens'] = clean(page.inner_text('//strong[contains(., "Jetons FL")]/following-sibling::span'))
        data['thanks_received'] = clean(page.inner_text('//strong[contains(., "Remerciements reçus")]/following-sibling::span'))
        data['thanks_given'] = clean(page.inner_text('//strong[contains(., "Remerciements donnés")]/following-sibling::span'))
        data['hit_and_run'] = clean(page.inner_text('//strong[contains(., "Hit&Run")]/following-sibling::span'))
        
        # Warnings (Sharewood)
        try:
            # "Warnings Avertissements en cours : 0 / 3"
            # On cherche le texte qui contient "Avertissements en cours"
            # Correction: C'est dans un span/strong, pas un li
            warnings_text = clean(page.inner_text('//span[contains(., "Avertissements en cours")]'))
            # On extrait juste "0 / 3" ou tout le texte
            data['warnings'] = warnings_text.replace("Warnings", "").strip()
        except:
            data['warnings'] = "0 / 3"

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
    data['seed_time_total'] = get_unit3d_val(page, "Durée totale des seeds")
    if data['seed_time_total'] == "0": 
        data['seed_time_total'] = get_unit3d_val(page, "Temps de seed total")
        
    data['seed_time_avg'] = get_unit3d_val(page, "Temps de seed moyen")
    data['seed_size'] = get_unit3d_val(page, "Seeding Size")
    if data['seed_size'] == "0": data['seed_size'] = get_unit3d_val(page, "Volume de Seed")

    # TORRENT COUNT
    data['count_up_non_anon'] = get_unit3d_val(page, "Uploads au total (Non-Anonyme)")
    data['count_up_anon'] = get_unit3d_val(page, "Uploads au total (Anonyme)")
    if data['count_up_non_anon'] == "0" and data['count_up_anon'] == "0":
        data['count_up_total'] = get_unit3d_val(page, "Total uploadés")

    data['count_downloaded'] = get_unit3d_val(page, "Total des téléchargés")
    if data['count_downloaded'] == "0": data['count_downloaded'] = get_unit3d_val(page, "Total complétés")

    data['count_seed'] = get_unit3d_val(page, "Total en seed")
    data['count_leech'] = get_unit3d_val(page, "Total en leech")
    data['count_inactive'] = get_unit3d_val(page, "Total Inactive Peers")

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
    data['torrent_downloader_credited'] = get_unit3d_val(page, "Torrent Télécharger (Credité)")
    data['torrent_downloader_refunded'] = get_unit3d_val(page, "Torrent Télécharger (Refunded)")
    if data['torrent_downloader_refunded'] == "0": data['torrent_downloader_refunded'] = get_unit3d_val(page, "Torrent Télécharger (Remboursé)")

    # RECOMPENSES / POINTS
    # Normalisation: on utilise 'points_bonus' pour tout le monde
    data['points_bonus'] = get_unit3d_val(page, "Coupon")
    if data['points_bonus'] == "0" or data['points_bonus'] == "":
         data['points_bonus'] = get_unit3d_val(page, "Point Bonus")
    
    data['fl_tokens'] = get_unit3d_val(page, "Jetons Freeleech")
    data['thanks_given'] = get_unit3d_val(page, "Merci donné")
    data['thanks_received'] = get_unit3d_val(page, "Merci reçu")
    
    # COMMUNITY / EXTRA
    data['invitations'] = get_unit3d_val(page, "Invitations")
    data['points_bonus_received'] = get_unit3d_val(page, "Points Bonus reçus")
    data['points_bonus_given'] = get_unit3d_val(page, "Points Bonus donnés")
    data['primes_received'] = get_unit3d_val(page, "Primes reçues")
    data['primes_given'] = get_unit3d_val(page, "Primes données")
    data['conseils_received'] = get_unit3d_val(page, "Conseils reçus")
    data['conseils_given'] = get_unit3d_val(page, "Conseils donnés")

    return data

def upload_to_ftp():
    """Envoie le fichier JSON sur le serveur O2Switch"""
    print(f"--- 📤 Envoi FTP vers {FTP_HOST} ({FTP_DIR}) ---")
    try:
        session = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS)
        # session.set_debuglevel(1) 
        
        # Navigation vers le dossier
        try:
            session.cwd(FTP_DIR)
        except:
            print(f"⚠️ Le dossier {FTP_DIR} n'existe pas. Tentative de création...")
            try:
                session.mkd(FTP_DIR)
                session.cwd(FTP_DIR)
            except Exception as e:
                print(f"❌ Impossible de créer/accéder au dossier {FTP_DIR}: {e}")
                session.quit()
                return

        # Upload stats.json
        with open(OUTPUT_FILE, 'rb') as file:
            session.storbinary(f'STOR {OUTPUT_FILE}', file)
            
        # Upload history.json
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'rb') as file:
                session.storbinary(f'STOR {HISTORY_FILE}', file)
        
        session.quit()
        print(f"✅ SUCCÈS : Données accessibles sur https://dash.example.com/stats.json")
    except Exception as e:
        print(f"❌ Erreur FTP critique : {e}")

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

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
    print(f"\n💾 Fichier {OUTPUT_FILE} généré en local.")

    # Gestion de l'historique
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            print("⚠️ Erreur lecture historique, création d'un nouveau.")
    
    history.append(final_data)
    
    # Garder les 720 dernières entrées (30 jours si 1h)
    if len(history) > 720:
        history = history[-720:]

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
    print(f"💾 Fichier {HISTORY_FILE} mis à jour ({len(history)} entrées).")

    # 3. ENVOI FTP
    upload_to_ftp()

if __name__ == "__main__":
    main()