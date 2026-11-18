// ==UserScript==
// @name         TrackBoard : dépôt de la session C411
// @namespace    trackboard
// @version      1.0.0
// @description  Après une connexion à C411 ouverte avec #trackboard, dépose la session dans TrackBoard.
// @match        https://c411.org/*
// @run-at       document-idle
// @noframes
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// @grant        GM_registerMenuCommand
// @grant        GM_xmlhttpRequest
// @grant        GM_cookie
// @grant        window.close
// @connect      ts.net
// @connect      localhost
// ==/UserScript==

/*
 * Installation
 * 1. Installer Tampermonkey (Firefox, Zen, Chrome). Sous Chrome, activer « Autoriser les
 *    scripts utilisateur » (ou le mode développeur) dans la fiche de l'extension.
 * 2. Tableau de bord de Tampermonkey, « Créer un nouveau script », coller ce fichier, enregistrer.
 * 3. Ouvrir https://c411.org/login#trackboard (lien des alertes Discord de TrackBoard). Sans
 *    le fragment #trackboard, le script ne fait rien.
 * 4. Premier usage : le bandeau demande l'adresse de TrackBoard (la racine du site, sans
 *    chemin) et la clé de dépôt (variable SESSION_DEPOT_CLE du serveur). Elles restent dans le
 *    stockage de Tampermonkey ; la commande de menu « TrackBoard : effacer l'adresse et la
 *    clé » les supprime.
 * 5. Se connecter comme d'habitude : identifiant et mot de passe par le gestionnaire de mots
 *    de passe, captcha coché à la main. Le script envoie le formulaire une fois ces trois
 *    éléments présents, attend la connexion, dépose le cookie de session puis ferme l'onglet.
 *
 * Le script ne remplit aucun champ et ne touche pas au captcha. L'adresse de TrackBoard doit
 * être en ts.net ou localhost (directives @connect ci-dessus) ; pour un autre domaine,
 * ajouter une ligne @connect ou accepter la demande d'autorisation de Tampermonkey.
 */

(function () {
  'use strict';

  if (window.top !== window.self) return;

  const TRACKER = 'C411';
  const COOKIE = '__Host-c411_session';
  const FRAGMENT = '#trackboard';
  // Route du backend, servie à la racine du site TrackBoard (pas de préfixe /api).
  const ROUTE = '/scrapers/session/' + TRACKER;
  const SONDE = '/api/auth/me';
  const CHAMP_CAPTCHA = 'input[name="cf-turnstile-response"]';
  const CLE_MODE = 'trackboard_c411';
  const REGLAGE_URL = 'trackboard_url';
  const REGLAGE_CLE = 'trackboard_cle';
  const DELAI_MAX = 3 * 60 * 1000;
  const PAS_SONDE = 2500;
  const PAS_FORMULAIRE = 500;
  const DELAI_ENVOI = 180000;
  const COULEURS = { info: '#5b9bd5', ok: '#4caf50', erreur: '#e05252' };

  let actif = false;
  let mode = null;
  let minuterieFormulaire = null;
  let bandeau = null;
  let ligneEtat = null;
  let zoneActions = null;
  let dernierTexte = '';

  // --- mode mémorisé le temps de la connexion (la page de connexion redirige) ---

  function lireMode() {
    try {
      const brut = JSON.parse(sessionStorage.getItem(CLE_MODE) || 'null');
      return brut && typeof brut.debut === 'number' ? { debut: brut.debut, soumis: brut.soumis === true } : null;
    } catch (e) {
      return null;
    }
  }

  function ecrireMode() {
    try {
      sessionStorage.setItem(CLE_MODE, JSON.stringify(mode));
    } catch (e) { /* stockage indisponible : le mode vit le temps de la page */ }
  }

  function effacerMode() {
    try {
      sessionStorage.removeItem(CLE_MODE);
    } catch (e) { /* rien à effacer */ }
  }

  // --- bandeau ---

  function element(balise, styles, texte) {
    const e = document.createElement(balise);
    // Styles posés par le CSSOM : une politique CSP du site ne les bloque pas.
    Object.assign(e.style, styles || {});
    if (texte) e.textContent = texte;
    return e;
  }

  function creerBandeau() {
    if (bandeau) return;
    bandeau = element('div', {
      all: 'initial', display: 'block', position: 'fixed', right: '12px', bottom: '12px', zIndex: '2147483647',
      maxWidth: '340px', boxSizing: 'border-box', padding: '8px 10px', borderRadius: '6px',
      background: '#1f2430', color: '#e6e6e6', font: '12px/1.4 system-ui, sans-serif',
      boxShadow: '0 2px 10px rgba(0, 0, 0, 0.4)', borderLeft: '3px solid ' + COULEURS.info,
    });
    const tete = element('div', { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' });
    tete.appendChild(element('strong', { font: 'inherit', fontWeight: '600', color: 'inherit' }, 'TrackBoard'));
    const fermer = element('button', {
      all: 'initial', cursor: 'pointer', color: '#9aa3b2', font: '14px/1 system-ui, sans-serif', padding: '0 2px',
    }, '×');
    fermer.type = 'button';
    fermer.title = 'Arrêter le dépôt de session';
    fermer.addEventListener('click', arreter);
    tete.appendChild(fermer);
    ligneEtat = element('div', { marginTop: '4px', font: 'inherit', color: 'inherit', overflowWrap: 'anywhere' });
    ligneEtat.setAttribute('role', 'status');
    zoneActions = element('div', { font: 'inherit', color: 'inherit' });
    bandeau.appendChild(tete);
    bandeau.appendChild(ligneEtat);
    bandeau.appendChild(zoneActions);
    document.documentElement.appendChild(bandeau);
  }

  function etat(texte, type) {
    if (!bandeau || texte === dernierTexte) return;
    dernierTexte = texte;
    ligneEtat.textContent = texte;
    bandeau.style.borderLeftColor = COULEURS[type || 'info'];
  }

  function viderActions() {
    if (zoneActions) zoneActions.replaceChildren();
  }

  function bouton(texte, action) {
    const b = element('button', {
      all: 'initial', cursor: 'pointer', marginTop: '6px', marginRight: '6px', padding: '3px 8px',
      borderRadius: '4px', background: '#3a4256', color: '#e6e6e6', font: '12px/1.4 system-ui, sans-serif',
    }, texte);
    b.type = 'button';
    b.addEventListener('click', action);
    zoneActions.appendChild(b);
    return b;
  }

  function arreter() {
    actif = false;
    clearInterval(minuterieFormulaire);
    effacerMode();
    if (bandeau) bandeau.remove();
    bandeau = null;
    dernierTexte = '';
  }

  // --- réglages (adresse de TrackBoard et clé de dépôt), jamais écrits dans ce fichier ---

  function reglagesComplets() {
    return Boolean(GM_getValue(REGLAGE_URL, '') && GM_getValue(REGLAGE_CLE, ''));
  }

  function normaliserAdresse(saisie) {
    let u;
    try {
      u = new URL(String(saisie).trim());
    } catch (e) {
      return { erreur: 'Adresse invalide (exemple : https://machine.exemple.ts.net).' };
    }
    const hote = u.hostname.toLowerCase();
    const prive = hote === 'localhost' || hote === 'ts.net' || hote.endsWith('.ts.net');
    if (u.protocol !== 'https:' && !(u.protocol === 'http:' && prive)) {
      return { erreur: 'Adresse en https obligatoire (http accepté pour ts.net et localhost seulement).' };
    }
    return { adresse: u.origin + u.pathname.replace(/\/+$/, ''), prive: prive };
  }

  function demanderReglages() {
    return new Promise(function (resolve) {
      viderActions();
      const styleChamp = {
        all: 'initial', display: 'block', boxSizing: 'border-box', width: '300px', maxWidth: '100%',
        marginTop: '6px', padding: '4px 6px', borderRadius: '4px', background: '#2b3140',
        color: '#e6e6e6', font: '12px/1.4 system-ui, sans-serif', border: '1px solid #4a5268',
      };
      const formulaire = element('form', { all: 'initial', display: 'block', font: 'inherit', color: 'inherit' });
      const champAdresse = element('input', styleChamp);
      champAdresse.type = 'url';
      champAdresse.placeholder = 'Adresse de TrackBoard (https://...)';
      champAdresse.autocomplete = 'off';
      champAdresse.value = GM_getValue(REGLAGE_URL, '');
      const champCle = element('input', styleChamp);
      champCle.type = 'password';
      champCle.placeholder = 'Clé de dépôt (SESSION_DEPOT_CLE)';
      champCle.autocomplete = 'off';
      const note = element('div', { marginTop: '4px', font: 'inherit', color: '#e8a0a0' });
      formulaire.appendChild(champAdresse);
      formulaire.appendChild(champCle);
      formulaire.appendChild(note);
      zoneActions.appendChild(formulaire);
      const valider = bouton('Enregistrer', function () {
        const resultat = normaliserAdresse(champAdresse.value);
        const cle = champCle.value.trim();
        if (resultat.erreur) {
          note.textContent = resultat.erreur;
          return;
        }
        if (!cle) {
          note.textContent = 'Clé de dépôt manquante.';
          return;
        }
        GM_setValue(REGLAGE_URL, resultat.adresse);
        GM_setValue(REGLAGE_CLE, cle);
        viderActions();
        resolve();
      });
      // Bouton d'envoi du formulaire : la touche Entrée dans un champ déclenche son clic.
      valider.type = 'submit';
      formulaire.appendChild(valider);
      formulaire.addEventListener('submit', function (evenement) { evenement.preventDefault(); });
    });
  }

  GM_registerMenuCommand("TrackBoard : effacer l'adresse et la clé", function () {
    GM_deleteValue(REGLAGE_URL);
    GM_deleteValue(REGLAGE_CLE);
    if (bandeau) etat("Adresse et clé effacées : rouvrir le lien de reconnexion pour les saisir à nouveau.");
  });

  // --- connexion : rien n'est rempli, le captcha n'est pas touché ---

  function pause(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  async function estConnecte() {
    try {
      const reponse = await fetch(SONDE, {
        credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' },
      });
      if (!reponse.ok) return false;
      const donnees = await reponse.json();
      return Boolean(donnees) && donnees.authenticated === true;
    } catch (e) {
      return false;
    }
  }

  async function attendreConnexion() {
    while (actif && Date.now() - mode.debut < DELAI_MAX) {
      await pause(PAS_SONDE);
      if (actif && await estConnecte()) return true;
    }
    return false;
  }

  function formulaireDeConnexion() {
    // Le champ « clé de dépôt » du bandeau est lui aussi de type password : il est écarté.
    const motDePasse = Array.from(document.querySelectorAll('input[type="password"]'))
      .find(function (champ) { return !bandeau || !bandeau.contains(champ); });
    const formulaire = motDePasse && motDePasse.form;
    if (!formulaire) return null;
    const captcha = formulaire.querySelector(CHAMP_CAPTCHA) || document.querySelector(CHAMP_CAPTCHA);
    const identifiant = Array.from(formulaire.elements).find(function (champ) {
      const type = (champ.getAttribute('type') || 'text').toLowerCase();
      return champ.tagName === 'INPUT' && champ.name !== 'cf-turnstile-response'
        && (type === 'text' || type === 'email');
    });
    return {
      formulaire: formulaire,
      pret: Boolean(captcha && captcha.value && motDePasse.value && identifiant && identifiant.value),
    };
  }

  function surveillerFormulaire() {
    let pretAuTourPrecedent = false;
    minuterieFormulaire = setInterval(function () {
      const trouve = formulaireDeConnexion();
      if (!trouve) {
        pretAuTourPrecedent = false;
        return;
      }
      if (mode.soumis) {
        etat('Formulaire déjà envoyé une fois : en cas de refus du site, corriger puis valider à la main.');
        return;
      }
      if (!trouve.pret) {
        pretAuTourPrecedent = false;
        etat("En attente : identifiant, mot de passe et captcha coché. L'envoi se fait ensuite tout seul.");
        return;
      }
      // Deux passages de suite : le gestionnaire de mots de passe a fini de remplir.
      if (!pretAuTourPrecedent) {
        pretAuTourPrecedent = true;
        return;
      }
      mode.soumis = true;
      ecrireMode();
      if (typeof trouve.formulaire.requestSubmit === 'function') {
        etat('Formulaire envoyé, attente de la connexion.');
        trouve.formulaire.requestSubmit();
      } else {
        etat('Tout est rempli : valider le formulaire à la main.');
      }
    }, PAS_FORMULAIRE);
  }

  // --- cookie de session ---

  function cookieParDocument() {
    const morceaux = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < morceaux.length; i += 1) {
      const egal = morceaux[i].indexOf('=');
      if (egal > 0 && morceaux[i].slice(0, egal).trim() === COOKIE) return morceaux[i].slice(egal + 1).trim();
    }
    return '';
  }

  function cookieParTampermonkey() {
    return new Promise(function (resolve) {
      if (typeof GM_cookie === 'undefined' || !GM_cookie || typeof GM_cookie.list !== 'function') {
        resolve('');
        return;
      }
      const garde = setTimeout(function () { resolve(''); }, 5000);
      try {
        GM_cookie.list({ url: location.origin + '/', name: COOKIE }, function (cookies, erreur) {
          clearTimeout(garde);
          const trouve = !erreur && Array.isArray(cookies)
            ? cookies.find(function (c) { return c && c.name === COOKIE; })
            : null;
          resolve(trouve && trouve.value ? String(trouve.value) : '');
        });
      } catch (e) {
        clearTimeout(garde);
        resolve('');
      }
    });
  }

  // --- dépôt dans TrackBoard ---

  function echec(texte, valeur, dejaConnecte, options) {
    etat(texte, 'erreur');
    viderActions();
    if (options && options.reessayer) {
      bouton('Réessayer', function () { envoyer(valeur, dejaConnecte); });
    }
    if (options && options.reglages) {
      bouton("Modifier l'adresse et la clé", function () {
        demanderReglages().then(function () { envoyer(valeur, dejaConnecte); });
      });
    }
  }

  function succes(message, dejaConnecte) {
    effacerMode();
    viderActions();
    const precision = dejaConnecte
      ? " C'est la session déjà ouverte dans ce navigateur qui a été déposée : son échéance peut être plus proche que 7 jours."
      : '';
    etat('Session déposée dans TrackBoard (' + message + ').' + precision + " Fermeture de l'onglet dans 3 s.", 'ok');
    setTimeout(function () {
      window.close();
      setTimeout(function () {
        etat('Session déposée dans TrackBoard (' + message + ').' + precision + ' Cet onglet peut être fermé.', 'ok');
      }, 800);
    }, 3000);
  }

  function verdict(reponse, valeur, dejaConnecte) {
    let corps = null;
    try {
      corps = JSON.parse(reponse.responseText);
    } catch (e) { /* réponse non JSON : traitée plus bas */ }
    const message = corps && typeof corps.message === 'string' ? corps.message.slice(0, 200) : '';
    const tout = { reessayer: true, reglages: true };
    switch (reponse.status) {
      case 200:
        if (corps && corps.status === 'ok') {
          succes(message || 'session acceptée', dejaConnecte);
        } else if (corps && corps.status === 'refusee') {
          echec('TrackBoard a reçu la session mais le site la refuse : ' + (message || 'raison inconnue') + '.',
            valeur, dejaConnecte, { reessayer: true });
        } else {
          echec("Réponse inattendue : vérifier l'adresse de TrackBoard.", valeur, dejaConnecte, tout);
        }
        break;
      case 400:
        echec('TrackBoard refuse la valeur du cookie (vide ou mal formée). Repli : bouton « Reconnecter » de TrackBoard.',
          valeur, dejaConnecte, { reessayer: true });
        break;
      case 401:
      case 403:
        echec('Clé de dépôt refusée par TrackBoard (ou dépôt par clé désactivé sur le serveur).',
          valeur, dejaConnecte, tout);
        break;
      case 404:
        echec("Route de dépôt introuvable : adresse de TrackBoard incorrecte, ou tracker " + TRACKER + ' non configuré.',
          valeur, dejaConnecte, tout);
        break;
      case 409:
        echec('Un relevé est en cours dans TrackBoard : réessayer dans une minute.', valeur, dejaConnecte, { reessayer: true });
        break;
      default:
        echec('Erreur de TrackBoard (HTTP ' + reponse.status + ').', valeur, dejaConnecte, tout);
    }
  }

  function envoyer(valeur, dejaConnecte) {
    viderActions();
    const adresse = GM_getValue(REGLAGE_URL, '');
    const cle = GM_getValue(REGLAGE_CLE, '');
    if (!adresse || !cle) {
      etat("Adresse de TrackBoard ou clé de dépôt manquante.", 'erreur');
      demanderReglages().then(function () { envoyer(valeur, dejaConnecte); });
      return;
    }
    etat("Envoi à TrackBoard et relevé de contrôle en cours (jusqu'à une minute).");
    const injoignable = { reessayer: true, reglages: true };
    GM_xmlhttpRequest({
      method: 'POST',
      url: adresse + ROUTE,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Depot-Cle': cle },
      data: JSON.stringify({ valeur: valeur }),
      anonymous: true,
      timeout: DELAI_ENVOI,
      onload: function (reponse) { verdict(reponse, valeur, dejaConnecte); },
      onerror: function () {
        echec('TrackBoard injoignable (réseau, Tailscale, ou domaine non autorisé dans Tampermonkey).',
          valeur, dejaConnecte, injoignable);
      },
      ontimeout: function () {
        echec("TrackBoard n'a pas répondu à temps.", valeur, dejaConnecte, injoignable);
      },
      onabort: function () {
        echec('Envoi annulé.', valeur, dejaConnecte, injoignable);
      },
    });
  }

  async function deposer(dejaConnecte) {
    etat('Connexion détectée, lecture du cookie de session.');
    const valeur = cookieParDocument() || await cookieParTampermonkey();
    if (!actif) return;
    if (!valeur) {
      effacerMode();
      actif = false;
      etat('Cookie de session illisible depuis ce script (cookie HttpOnly, et accès aux cookies de Tampermonkey '
        + 'indisponible ou refusé). Repli : copier la valeur de ' + COOKIE + ' (F12, Stockage ou Application, '
        + 'Cookies) et la coller dans TrackBoard, carte ' + TRACKER + ', bouton « Reconnecter ».', 'erreur');
      return;
    }
    envoyer(valeur, dejaConnecte);
  }

  // --- déroulé ---

  async function lancer() {
    creerBandeau();
    etat('Dépôt de session actif : vérification de la connexion.');
    const reglages = reglagesComplets() ? Promise.resolve() : demanderReglages();
    const dejaConnecte = await estConnecte();
    let connecte = dejaConnecte;
    if (!connecte) {
      etat('Dépôt de session actif : en attente de la connexion.');
      surveillerFormulaire();
      connecte = await attendreConnexion();
      clearInterval(minuterieFormulaire);
    }
    if (!actif) return;
    if (!connecte) {
      effacerMode();
      actif = false;
      etat('Délai de 3 min dépassé sans connexion : rouvrir le lien de reconnexion pour recommencer.', 'erreur');
      return;
    }
    if (!reglagesComplets()) etat("Connexion détectée : saisir l'adresse de TrackBoard et la clé de dépôt.");
    await reglages;
    if (!actif) return;
    await deposer(dejaConnecte);
  }

  function activer() {
    if (actif) return;
    mode = lireMode();
    if (mode && Date.now() - mode.debut > DELAI_MAX) {
      effacerMode();
      mode = null;
    }
    if (!mode) {
      if (location.hash !== FRAGMENT) return;
      mode = { debut: Date.now(), soumis: false };
      ecrireMode();
    }
    actif = true;
    lancer();
  }

  activer();
  window.addEventListener('hashchange', activer);
})();
