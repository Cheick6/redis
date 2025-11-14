import json  # Pour convertir les dictionnaires Python en chaînes JSON et vice-versa
import os  # Pour lire les variables d'environnement (comme l'URL de Redis)
import uuid  # Pour générer des identifiants uniques (UUID) pour les annonces
from dataclasses import dataclass, asdict  # Outils pour créer des classes de données (comme "Announcement")
import redis  # Le client pour se connecter à la base de données Redis

# --- Configuration Principale ---

# Récupère l'URL de connexion à Redis depuis les variables d'environnement.
# Si "REDIS_URL" n'est pas définie, utilise une valeur par défaut (localhost).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- Définition des Canaux de Communication (Le cœur du système Pub/Sub) ---

# Canal "radio" public. Le manager publie les *nouvelles offres* ici.
# TOUS les livreurs écoutent ce canal.
CHANNEL_DELIVERIES = "deliveries"

# Canal public pour annoncer la *décision finale*. 
# Le manager publie "L'offre <id> a été prise par Livreur X" ici.
# (format: "selection:uuid-de-l-annonce")
CHANNEL_SELECTION_FMT = "selection:{announcement_id}"

# Canal de "salle d'enchères". 
# Les livreurs envoient leurs *candidatures* pour une offre spécifique ici.
# Le manager écoute ce canal après avoir publié une offre.
# (format: "responses:uuid-de-l-annonce")
CHANNEL_RESPONSES_FMT = "responses:{announcement_id}"

# Canal "privé". 
# Le manager envoie la *confirmation d'assignation* directement au livreur gagnant ici.
# Chaque livreur écoute son propre canal privé.
# (format: "courier:id-du-livreur")
CHANNEL_COURIER_FMT = "courier:{courier_id}"

# --- Fonctions Utilitaires ---

def get_redis():
    """Crée et retourne un objet de connexion à Redis."""
    # decode_responses=True est crucial :
    # il garantit que Redis retourne des chaînes de caractères (str)
    # au lieu de bytes (b'...').
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)

def publish_json(r: redis.Redis, channel: str, payload: dict):
    """
    Publie un dictionnaire Python (payload) sur un canal Redis.
    Le dictionnaire est d'abord converti en chaîne JSON.
    """
    # r.publish(canal, message_en_chaine)
    r.publish(channel, json.dumps(payload))

def parse_json(message_data: str) -> dict:
    """
    Tente de convertir une chaîne JSON (reçue de Redis) en dictionnaire Python.
    Retourne un dictionnaire vide si le message est invalide (ex: None ou JSON cassé).
    """
    try:
        # Tente de charger la chaîne en dictionnaire
        return json.loads(message_data)
    except Exception:
        # En cas d'erreur (ex: message vide), retourne un dict vide
        return {}

# --- Structures de Données ---

@dataclass  # Un décorateur qui simplifie la création de classes de données
class Announcement:
    """Représente une annonce de course (offre de livraison)."""
    id: str
    pickup: str
    dropoff: str
    reward: float

    @staticmethod
    def new(pickup: str, dropoff: str, reward: float) -> "Announcement":
        """
        Méthode "Usine" pour créer une nouvelle annonce.
        Génère automatiquement un ID unique (UUID) pour celle-ci.
        """
        return Announcement(id=str(uuid.uuid4()), pickup=pickup, dropoff=dropoff, reward=reward)

    def to_dict(self) -> dict:
        """Convertit l'objet Announcement en un dictionnaire."""
        # asdict() est une fonction de dataclasses qui fait cela automatiquement.
        # C'est nécessaire pour la conversion en JSON avant de publier.
        return asdict(self)