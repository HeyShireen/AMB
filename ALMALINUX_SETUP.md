# 🚀 SSH Connection pour AlmaLinux VPS

## Connexion SSH avec IPv6

Depuis **PowerShell Windows**:

```powershell
# Syntaxe IPv6: [ipv6_address]
ssh root@[2001:19f0:5400:2e28:5400:05ff:fed8:6dc8]

# Ou:
ssh root@2001:19f0:5400:2e28:5400:05ff:fed8:6dc8
```

**Ou si tu as une IPv4**, regarde dans Vultr Dashboard (il devrait y avoir une IPv4 aussi).

---

## Une fois connecté au VPS

### Étape 1: Vérifier le système
```bash
cat /etc/os-release
# Doit afficher: NAME="AlmaLinux" VERSION="8"
```

### Étape 2: Cloner le repo (tu peux choisir)

**Option A: Via GitHub (recommandé)**
```bash
git clone https://github.com/ton_username/AMB.git /opt/amb-bot
cd /opt/amb-bot
```

**Option B: Sans GitHub (uploader manuellement)**
```bash
mkdir -p /opt/amb-bot
cd /opt/amb-bot
```

### Étape 3: Télécharger et lancer le script de deploy
```bash
# Télécharger le script
curl -o deploy.sh https://raw.githubusercontent.com/ton_username/AMB/main/deploy.sh

# Ou depuis GitHub raw (si pas d'URL):
wget https://raw.githubusercontent.com/ton_username/AMB/main/deploy.sh

# Ou copier-coller le contenu et faire:
nano deploy.sh
# Puis coller le contenu et Ctrl+X → Y → Enter
```

### Étape 4: Lancer le déploiement
```bash
chmod +x deploy.sh
bash deploy.sh
```

Le script va automatiquement:
- ✅ Détecter AlmaLinux 8
- ✅ Installer Python 3.11 avec `dnf`
- ✅ Installer Poetry
- ✅ Cloner le repo
- ✅ Configurer Cron
- ✅ Créer `.env` template

---

## Si GitHub ne fonctionne pas

### Méthode 1: Upload via SCP (depuis ton PC)

```powershell
# Windows PowerShell - upload un fichier
scp -r "C:\Users\AlbanMichaud\OneDrive - DEC\Documents\ECOTEC\Logiciels\AMB\*" root@[2001:19f0:5400:2e28:5400:05ff:fed8:6dc8]:/opt/amb-bot/

# OU avec IPv4 (plus simple):
scp -r "C:\Users\AlbanMichaud\OneDrive - DEC\Documents\ECOTEC\Logiciels\AMB\*" root@your_ipv4:/opt/amb-bot/
```

### Méthode 2: Upload via SFTP
```bash
# SSH dans le VPS, puis:
sftp root@[2001:19f0:5400:2e28:5400:05ff:fed8:6dc8]
put -r /path/to/local/files /opt/amb-bot/
```

---

## Checklist

- [ ] SSH connecté au VPS (root@...)
- [ ] `cat /etc/os-release` affiche AlmaLinux 8
- [ ] Code uploadé dans `/opt/amb-bot` (repo cloné OU fichiers copiés)
- [ ] `bash deploy.sh` lancé et complété ✅
- [ ] `.env` créé dans `/opt/amb-bot/.env`

---

## Prochaine étape

Après deploy.sh:
```bash
# 1. Edit .env
nano /opt/amb-bot/.env

# 2. Test du bot
cd /opt/amb-bot
source venv/bin/activate
python -m amb_bot.main once

# 3. Vérifier cron
crontab -l
```

---

**Tu veux que je prépare un script simplifié pour AlmaLinux?** Je peux aussi te dire les commandes exactes si upload manuel. Dis-moi! 🚀
