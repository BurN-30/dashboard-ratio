#!/usr/bin/env python3
"""
Test script pour vérifier que l'architecture complète fonctionne
"""

import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime

# Couleurs pour la console
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name, passed, details=""):
    symbol = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
    print(f"{symbol} {name}")
    if details:
        print(f"   {BLUE}→{RESET} {details}")

def test_local_files():
    """Vérifier que les fichiers JSON locaux existent et sont valides"""
    print(f"\n{YELLOW}--- Test 1: Fichiers locaux ---{RESET}")
    
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Vérifier stats.json
    stats_ok = False
    if os.path.exists("stats.json"):
        try:
            with open("stats.json", "r", encoding="utf-8") as f:
                stats = json.load(f)
                stats_ok = len(stats) > 0
                print_test("stats.json existe et est valide", stats_ok, 
                          f"{len(stats)} trackers trouvés")
        except:
            print_test("stats.json valide", False, "Erreur de parsing JSON")
    else:
        print_test("stats.json existe", False, "Fichier non trouvé")
    
    # Vérifier history.json
    history_ok = False
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r", encoding="utf-8") as f:
                history = json.load(f)
                history_ok = isinstance(history, list) and len(history) > 0
                print_test("history.json existe et est valide", history_ok,
                          f"{len(history)} entrées trouvées")
        except:
            print_test("history.json valide", False, "Erreur de parsing JSON")
    else:
        print_test("history.json existe", False, "Fichier non trouvé")
    
    return stats_ok and history_ok

def test_env_file():
    """Vérifier que le fichier .env contient les bonnes variables"""
    print(f"\n{YELLOW}--- Test 2: Configuration .env ---{RESET}")
    
    required_vars = [
        "FTP_HOST",
        "FTP_USER", 
        "FTP_PASS",
        "FTP_DIR",
        "GF_USER",
        "GF_PASS",
        "TOS_USER",
        "TOS_PASS",
        "SW_USER",
        "SW_PASS"
    ]
    
    from dotenv import load_dotenv
    load_dotenv()
    
    all_ok = True
    for var in required_vars:
        val = REDACTEDvar)
        ok = val is not None and len(val) > 0
        all_ok = all_ok and ok
        status = f"'{val[:20]}...'" if ok else "MANQUANT"
        print_test(f"{var}", ok, status)
    
    return all_ok

def test_ftp_connection():
    """Tester la connexion FTP"""
    print(f"\n{YELLOW}--- Test 3: Connexion FTP ---{RESET}")
    
    from dotenv import load_dotenv
    import ftplib
    
    load_dotenv()
    
    try:
        ftp = ftplib.FTP(REDACTED"FTP_HOST"), REDACTED"FTP_USER"), REDACTED"FTP_PASS"))
        ftp_ok = True
        ftp.quit()
        print_test("Connexion FTP", True, f"Serveur: {REDACTED'FTP_HOST')}")
        
        # Vérifier le dossier
        try:
            ftp = ftplib.FTP(REDACTED"FTP_HOST"), REDACTED"FTP_USER"), REDACTED"FTP_PASS"))
            ftp.cwd(REDACTED"FTP_DIR"))
            print_test(f"Dossier FTP: {REDACTED'FTP_DIR')}", True)
            ftp.quit()
        except:
            print_test(f"Dossier FTP: {REDACTED'FTP_DIR')}", False, "Non accessible")
            ftp_ok = False
            
        return ftp_ok
    except Exception as e:
        print_test("Connexion FTP", False, str(e))
        return False

def test_web_files():
    """Vérifier que les fichiers sont accessibles en HTTP"""
    print(f"\n{YELLOW}--- Test 4: Accès web aux fichiers ---{RESET}")
    
    urls = [
        "https://dash.example.com/stats.json",
        "https://dash.example.com/history.json"
    ]
    
    all_ok = True
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            ok = response.status_code == 200
            all_ok = all_ok and ok
            
            if ok:
                try:
                    data = response.json()
                    print_test(url, True, f"✓ Accessible ({len(str(data))} bytes)")
                except:
                    print_test(url, False, "Pas du JSON valide")
                    all_ok = False
            else:
                print_test(url, False, f"HTTP {response.status_code}")
        except Exception as e:
            print_test(url, False, str(e))
            all_ok = False
    
    return all_ok

def test_next_js_api():
    """Tester que le site Next.js peut récupérer les données"""
    print(f"\n{YELLOW}--- Test 5: API Next.js ---{RESET}")
    
    urls = [
        "https://dash.example.com/api/stats",
        "https://dash.example.com/api/history"
    ]
    
    all_ok = True
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            ok = response.status_code == 200
            all_ok = all_ok and ok
            
            if ok:
                try:
                    data = response.json()
                    print_test(url, True, "✓ Proxy fonctionne")
                except:
                    print_test(url, False, "Pas du JSON valide")
                    all_ok = False
            else:
                print_test(url, False, f"HTTP {response.status_code}")
        except Exception as e:
            print_test(url, False, str(e))
            all_ok = False
    
    return all_ok

def main():
    print(f"\n{BLUE}{'='*60}")
    print(f"🔍 DIAGNOSTIC - Torrent Dashboard")
    print(f"{'='*60}{RESET}\n")
    
    results = {
        "Fichiers locaux": test_local_files(),
        "Configuration .env": test_env_file(),
        "Connexion FTP": test_ftp_connection(),
        "Accès web aux fichiers": test_web_files(),
        "API Next.js": test_next_js_api(),
    }
    
    print(f"\n{BLUE}{'='*60}")
    print(f"📊 RÉSUMÉ")
    print(f"{'='*60}{RESET}\n")
    
    for name, ok in results.items():
        symbol = f"{GREEN}✅{RESET}" if ok else f"{RED}❌{RESET}"
        print(f"{symbol} {name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n{BLUE}{'='*60}")
    print(f"Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print(f"{GREEN}✅ Tous les tests sont passés! L'architecture fonctionne.{RESET}")
    elif passed >= 3:
        print(f"{YELLOW}⚠️  Certains tests ont échoué. Vérifiez les détails ci-dessus.{RESET}")
    else:
        print(f"{RED}❌ Trop de tests échoués. Vérifiez votre configuration.{RESET}")
    
    print(f"{'='*60}\n")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{RED}❌ Erreur fatale:{RESET} {e}")
        sys.exit(1)
