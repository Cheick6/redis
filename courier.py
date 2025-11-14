import argparse  # Pour lire les arguments (ex: --id "c1")
import random  # Pour simuler la décision d'accepter ou non une offre
import time  # Pour ajouter une petite pause dans la boucle

# Importe les fonctions et classes partagées depuis common.py
from common import (
    get_redis, publish_json, parse_json,
    CHANNEL_DELIVERIES, CHANNEL_RESPONSES_FMT, CHANNEL_COURIER_FMT
)

def main():
    """Point d'entrée principal du script Livreur."""
    
    # Arguments spécifiques au livreur
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Identifiant du livreur (unique)")
    parser.add_argument("--name", default="Livreur")
    parser.add_argument("--accept-rate", type=float, default=0.9, help="proba d'accepter une annonce (0-1)")
    args = parser.parse_args()

    r = get_redis()  # Connexion à Redis

    # --- Configuration de l'écoute (Abonnements) ---
    pubsub = r.pubsub()
    
    # 1. S'abonne au canal public 'deliveries' pour entendre les NOUVELLES OFFRES
    pubsub.subscribe(CHANNEL_DELIVERIES)
    
    # 2. S'abonne à son canal privé 'courier:<id>' pour entendre les ASSIGNATIONS (si on gagne)
    pubsub.subscribe(CHANNEL_COURIER_FMT.format(courier_id=args.id))
    
    print(f"[Courier {args.id}] Abonné à '{CHANNEL_DELIVERIES}' et canal direct 'courier:{args.id}'.") 

    # --- Boucle d'écoute principale ---
    # Le livreur écoute en permanence
    while True:
        # Vérifie s'il y a un message sur *un des canaux* auxquels il est abonné
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if not message:
            continue  # Pas de message, on recommence la boucle

        # Un message a été reçu !
        data = parse_json(message.get("data", ""))
        channel = message.get("channel", "") # De quel canal vient-il ?

        # --- Logique de décision ---

        # CAS 1: Le message vient de notre CANAL PRIVÉ ("courier:<id>")
        if channel == CHANNEL_COURIER_FMT.format(courier_id=args.id) and data:
            # C'est une assignation ! On a gagné une offre.
            print(f"[Courier {args.id}] ✅ Assignation reçue: {data}")
            continue  # On a traité le message, on retourne écouter

        # CAS 2: Le message vient du CANAL PUBLIC ("deliveries")
        if channel == CHANNEL_DELIVERIES and data and data.get("type") == "announcement":
            # C'est une nouvelle annonce (offre)
            ann = data
            ann_id = ann.get("id")
            print(f"[Courier {args.id}] Nouvelle annonce: {ann}")

            # DÉCISION: Est-ce que je postule ?
            # Simulation simple: on "lance un dé" (random)
            if random.random() <= args.accept_rate:
                # OUI, je postule !
                
                # 1. Définir le canal de réponse (la "salle d'enchères")
                response_chan = CHANNEL_RESPONSES_FMT.format(announcement_id=ann_id)
                
                # 2. Préparer la candidature (le payload)
                payload = {
                    "announcement_id": ann_id,
                    "courier_id": args.id,
                    "courier_name": args.name,
                    # On pourrait ajouter de vraies métriques ici (ex: distance, ETA)
                    "eta_minutes": random.randint(5, 20)  # Simulation d'un ETA
                }
                
                # 3. Envoyer la candidature
                publish_json(r, response_chan, payload)
                print(f"[Courier {args.id}] Candidature envoyée sur '{response_chan}': {payload}")
            else:
                # NON, je ne postule pas.
                print(f"[Courier {args.id}] Je passe mon tour pour cette annonce.")

        # Petite pause pour éviter de surcharger le CPU
        time.sleep(0.1)

if __name__ == "__main__":
    main()