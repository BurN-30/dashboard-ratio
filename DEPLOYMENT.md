# 🚀 DÉPLOYEMENT RAPIDE - Next Steps

## ✅ Status actuel

Votre architecture est **complète et fonctionnelle**:
- ✅ Scraper générant les JSON
- ✅ FTP uploadant les fichiers
- ✅ Données accessibles sur `https://dash.example.com/`
- ❌ Site Next.js pas encore visible

---

## 🎯 SEULE ÉTAPE RESTANTE: Déployer le site

Choisir **UNE** des 3 options:

---

## Option 1️⃣: **VERCEL** (Recommandé - Plus simple - GRATUIT)

### Avantages
- ✅ Déploiement en 5 minutes
- ✅ Gratuit (plan Hobby)
- ✅ Auto-deployment depuis Git
- ✅ Pas de configuration serveur
- ✅ Performance optimale

### Étapes

1. **Créer compte Vercel**
   ```
   https://vercel.com/signup
   → Connexion avec GitHub
   ```

2. **Importer le projet**
   ```
   https://vercel.com/new
   → Sélectionner repository: dashboard-ratio
   → Configurer:
      Root Directory: torrent-dashboard
   ```

3. **Configurer le domaine**
   ```
   Dashboard Vercel → Settings → Domains
   → Ajouter: dash.example.com
   → Suivre les instructions DNS
   ```

4. **C'est déployé!** 🎉
   ```
   https://dash.example.com/
   ```

**Temps:** ~5 min  
**Coût:** Gratuit

---

## Option 2️⃣: **O2SWITCH** (Ton serveur existant)

### Avantages
- ✅ Sur ton infrastructure
- ✅ Contrôle total
- ✅ Pas de dépendance externe

### Étapes

1. **Builder localement**
   ```bash
   cd torrent-dashboard
   npm install
   npm run build
   ```

2. **Uploader sur O2Switch**
   ```
   Via FTP:
   Envoyer le dossier .next/ complet
   Envoyer package.json + package-lock.json
   Envoyer public/
   ```

3. **Configuration serveur O2Switch**
   ```
   Demander au support O2Switch d'installer Node.js v18+
   Créer application Node.js pointant vers le dossier
   Exposer sur: https://dash.example.com
   ```

4. **Lancer l'app**
   ```
   npm install
   npm run start
   ```

**Temps:** ~30 min  
**Coût:** Compris dans ton offre O2Switch  
**Complexité:** Moyenne

---

## Option 3️⃣: **VPS Personnel** (AWS, DigitalOcean, Linode)

### Avantages
- ✅ Contrôle total du serveur
- ✅ Scalable
- ✅ Personnalisable

### Étapes (exemple DigitalOcean)

```bash
# SSH vers le VPS
ssh root@your-vps-ip

# Installer Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Cloner le repo
git clone https://github.com/BurN-30/dashboard-ratio.git
cd dashboard-ratio/torrent-dashboard

# Installer et builder
npm install
npm run build

# Lancer avec PM2 (process manager)
npm install -g pm2
pm2 start npm --name "dashboard" -- start
pm2 startup
pm2 save

# Configurer le domaine (DNS)
# Pointer dash.example.com → IP du VPS
```

**Temps:** ~1h  
**Coût:** ~5-10€/mois  
**Complexité:** Élevée

---

## 🏆 RECOMMANDATION

### 👉 **Utiliser VERCEL**

Pourquoi:
1. **Zéro configuration** - Vercel gère tout
2. **Gratuit** - Pas de coût supplémentaire
3. **Rapide** - 5 minutes pour un déploiement complet
4. **Fiable** - Infrastructure mondiale
5. **Auto-update** - Chaque `git push` = déploiement automatique

### Instructions courtes:

```
1. https://vercel.com/signup (avec GitHub)
2. https://vercel.com/new → Sélectionner dashboard-ratio
3. Root Directory: torrent-dashboard
4. Déployer
5. Configurer domaine dash.example.com
6. ✅ Done!
```

---

## ✅ Checklist avant de déployer

- [ ] Vérifier que le scraper génère bien `stats.json` et `history.json`
- [ ] Vérifier que les fichiers sont accessibles: `https://dash.example.com/stats.json`
- [ ] Code Git commité: `git status` = clean
- [ ] Frontend se lance en local: `cd torrent-dashboard && npm run dev`
- [ ] Pas d'erreurs dans la console

---

## 📊 Après le déploiement

### Vérifier que ça fonctionne

```bash
# Réexécuter le diagnostic
python test_architecture.py
```

Devrait montrer:
```
Score: 5/5 tests réussis ✅
```

### Accéder au dashboard

```
https://dash.example.com
Login: utiliser tes credentials
→ Voir tes stats en direct!
```

---

## 🔄 Workflow de mise à jour

Une fois déployé:

```
1. Faire des changements en local
2. git add . && git commit -m "..."
3. git push

→ Vercel/O2Switch déploie automatiquement
→ Site mis à jour en 30 secondes
```

---

## 🛠️ Troubleshooting

### "Le site est en 404"
→ Vérifier que le déploiement est terminé  
→ Attendre quelques minutes après le push

### "Les données ne s'affichent pas"
→ Vérifier que `/api/stats` retourne du JSON:  
```
https://dash.example.com/api/stats
```

### "Erreur de déploiement"
→ Vérifier les logs de Vercel/serveur  
→ Vérifier que le build fonctionne localement:  
```bash
npm run build
npm run start
```

---

## 📞 Besoin d'aide?

Ressources:
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation complète
- [DIAGNOSTIC.md](DIAGNOSTIC.md) - Vérifier l'architecture
- [README.md](README.md) - Documentation

---

**Courage! C'est la dernière étape avant d'avoir votre dashboard en production!** 🚀

Choisissez votre option et lancez le déploiement! ✨
