
# UberEats-like Platform — Redis Pub/Sub POC (Python)

Ce POC illustre la communication **Manager ⇄ Livreurs** avec **Redis Pub/Sub**.
Il supporte maintenant le **chargement depuis des fichiers CSV** pour :
- publier plusieurs **annonces** d'affilée ;
- lancer automatiquement plusieurs **livreurs**.

##  Prérequis
- Python 3.10+
- Redis en local (via Docker ou service installé)
- `pip install -r requirements.txt`

### Démarrer Redis (Docker)
```bash
docker run --name redis-poc -p 6379:6379 -d redis:7-alpine
```

### Observer l'activité sur le serveur redis
```bash
docker exec -it redis-poc redis-cli MONITOR
```
##  Installation
```bash
pip install -r requirements.txt
```

## ▶ Lancer la démo classique (3 terminaux)
**Terminal 1 — Manager**
```bash
python manager.py
```

**Terminal 2 — Livreur A**
```bash
python courier.py --id A --name "Livreur A"
```

**Terminal 3 — Livreur B**
```bash
python courier.py --id B --name "Livreur B"
```

---

##  Utiliser des fichiers CSV

### 1) Annonces depuis un CSV
Un fichier `data/announcements.csv` est fourni (colonnes: `pickup,dropoff,reward`).  
Publier plusieurs annonces séquentiellement :
```bash
python manager.py --csv data/announcements.csv --wait 8 --interval 2
```
Utilisation du fichier kaggle modifier
```bash
python manager.py --csv data/adapted_announcements.csv --interval 2
```
### 2) Lancer plusieurs livreurs depuis un CSV
Un fichier `data/couriers.csv` est fourni (colonnes: `id,name,accept_rate`).  
Lancer automatiquement chaque livreur dans un processus séparé :
```bash
python launch_couriers.py --csv data/couriers.csv
```

> Les scripts restent compatibles avec les arguments CLI classiques.

##  Structure
```
ubereats-redis-poc/
├─ manager.py
├─ courier.py
├─ launch_couriers.py
├─ common.py
├─ requirements.txt
├─ data/
│  ├─ announcements.csv
│  └─ couriers.csv
└─ README.md
```

##  Notes
- Pub/Sub est **volatile** : si un livreur n'est pas abonné au moment de la publication, il peut **rater** l'annonce.
- Politique d'assignation : **premier répondant** (modifiable).
# redis
