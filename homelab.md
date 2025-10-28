# SOC HomeLab — Mode d'emploi 

> **Objectif :** démarrer la stack, exécuter des attaques simples depuis l'attaquant et visualiser les détections dans Splunk.

---

## Pré-requis

* Docker & Docker Compose installés.
* Avoir créé un token HEC dans Splunk Web (Settings → Data Inputs → HTTP Event Collector).
* Copier `.env.example` → `.env` et remplir `SPLUNK_HOST`, `HEC_TOKEN`, `HEC_INDEX`. **Ne pas committer `.env`.**

---

## 1 - Démarrer Splunk (docker)

Si Splunk n'est pas déjà en service, lancez-le rapidement (lab uniquement) :

```bash
docker run -d --name splunk \
  --memory=3g --memory-swap=3g --cpus=2 \
  -p 8000:8000 -p 8088:8088 \
  -e SPLUNK_START_ARGS="--accept-license" \
  -e SPLUNK_PASSWORD="changeme" \
  splunk/splunk:latest
```

Accédez à Splunk Web : `http://<SPLUNK_HOST>:8000` et créez/activez un token HEC. Remplissez `.env` avec ce token.

---

## 2 - Construire et lancer les containers (compose)

Le `docker-compose.yml` contient les services : `victim_web` (Flask), `victim_ssh` (SSH) et optionnellement d'autres. Depuis la racine du projet :

```bash
# build & run (reconstruit victim_web si modifié)
docker compose up -d --build
```

Vérifiez :

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
# doit afficher : victim_web (8081), victim_ssh (2222), et éventuellement splunk si géré ici
```

---

## 3 - Ouvrir un shell dans le container web et lancer le forwarder

Pour voir les erreurs et sorties en direct, exécutez le forwarder à l'intérieur du container en shell interactif :

```bash
# accéder au shell du container Flask
docker exec -it victim_web bash

# une fois dans le shell du container, vérifier le log et lancer le forwarder
ls -l /var/log/app.log
tail -n 50 /var/log/app.log

# lancer le forwarder en mode interactif (vous verrez les erreurs/sorties)
python /log_forwarder.py
```

Si `requests` manque : dans le shell du container exécutez `pip install requests` (puis relancez le forwarder).

Le forwarder envoie les lignes à Splunk HEC. Lancer en mode interactif permet de lire les exceptions et de déboguer immédiatement.

---

## 4 - Attaques de test (à lancer depuis Kali / machine attaquante)

Toujours exécuter ces commandes dans un lab isolé.

### A - Rafale HTTP (simulateur de scan/crawler)

```bash
# envoi N requêtes GET rapides
for i in $(seq 1 200); do curl -s "http://192.168.1.173:8081/?p=$i" >/dev/null & sleep 0.01; done; wait
```

**But :** générer beaucoup d’URI différentes pour provoquer des traces dans les logs applicatifs.

### B - Payload malveillant (POST)

```bash
curl -X POST -d '<?php system($_GET["cmd"]); ?>' "http://192.168.1.173:8081/upload"
```

**But :** simuler une tentative d’upload / webshell.

### C - Scan de ports rapide (nmap)

```bash
nmap -sS -p1-1000 -T4 192.168.1.173
```

**But :** détection réseau (Suricata / firewall) plutôt qu’app logs.

### D - Brute force SSH (lab only, petite wordlist)

```bash
# exemple simple avec sshpass (installer sshpass sur Kali)
sshpass -p 'password' ssh -o StrictHostKeyChecking=no -p 2222 root@192.168.1.173 'echo ok'
```

**But :** génère des tentatives d’authentification à vérifier dans les logs SSH / IDS.

---

## 5 - Recherches SPL utiles (à coller et exécuter dans Splunk Search)

### Recherche simple des logs applicatifs

```spl
index=main sourcetype="homelab:app_log"
| spath input=_raw
| table _time event_type src_ip path data
```

### Détection : upload suspect (PHP, system, shell_exec, base64)

```spl
index=main sourcetype="homelab:app_log" event_type="file_upload"
| spath input=_raw path=data output=data
| search data="*<?php*" OR data="*system(*" OR data="*shell_exec*" OR data="*base64_decode*"
| table _time src_ip data
```

### Détection : scan HTTP (many unique URIs in 1 minute)

```spl
index=main sourcetype="homelab:app_log" event_type="http_request"
| spath input=_raw path=path output=uri
| bin _time span=1m
| stats dc(uri) as unique_uris, count as total_requests by src_ip, _time
| where unique_uris > 20
| sort -_time
```

---

## 6 - Vérifications & dépannage rapides

Si aucun événement n’apparaît dans Splunk : vérifier que le forwarder est en cours d’exécution (dans le shell interactif) et que `.env` contient la bonne adresse et token HEC.

Pour tester HEC sans forwarder (sur l’hôte) :

```bash
curl -k -H "Authorization: Splunk <HEC_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"event":"hec_test"}' \
     https://<SPLUNK_HOST>:8088/services/collector/event
```

Vérifier le fichier de logs de l’app dans le container :

```bash
docker exec victim_web tail -n 50 /var/log/app.log
```

---

## 7 - Notes

* Sauvegardez les recherches SPL comme Saved Search / Alert et ajoutez un panneau au dashboard pour la démonstration.
