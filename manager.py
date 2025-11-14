import time  # Pour gérer les délais d'attente (deadlines)
import argparse  # Pour lire les arguments de la ligne de commande (ex: --pickup "Resto A")
from typing import Optional  # Pour les annotations de type (ex: peut retourner un dict ou None)

# Importe les fonctions et classes partagées depuis common.py
from common import (
    get_redis, publish_json, parse_json,
    Announcement, CHANNEL_DELIVERIES,
    CHANNEL_RESPONSES_FMT, CHANNEL_SELECTION_FMT, CHANNEL_COURIER_FMT
)

def wait_for_responses(r, ann_id: str, wait_seconds: float = 6.0) -> Optional[dict]:
    """
    Attend des réponses de livreurs sur un canal spécifique (responses:<ann_id>)
    pendant un temps donné (wait_seconds).
    Retourne la *première* réponse reçue, ou None si personne n'a répondu.
    """
    # Définit le canal de réponse spécifique pour CETTE annonce
    chan = CHANNEL_RESPONSES_FMT.format(announcement_id=ann_id)
    
    # Crée un objet PubSub pour écouter
    pubsub = r.pubsub()
    pubsub.subscribe(chan)  # S'abonne au canal
    print(f"[Manager] En attente de réponses sur '{chan}' pendant {wait_seconds}s ...")

    # Calcule l'heure de fin (la "deadline")
    deadline = time.time() + wait_seconds
    chosen = None
    
    # Boucle tant que l'heure actuelle est avant la deadline
    while time.time() < deadline:
        # Vérifie s'il y a un message, avec un timeout court pour ne pas bloquer
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if not message:
            continue  # Pas de message, on recommence la boucle

        # Un message a été reçu !
        data = parse_json(message.get("data", ""))
        if data:
            print(f"[Manager] Réponse reçue: {data}")
            chosen = data  # On garde cette réponse
            break  # STRATÉGIE: On prend le premier qui répond. On arrête d'attendre.
    
    pubsub.unsubscribe(chan)  # Nettoyage: on arrête d'écouter ce canal
    return chosen

def publish_selection(r, ann_id: str, courier_id: str, courier_name: str):
    """
    Annonce publiquement et en privé qui a remporté l'offre.
    """
    selection_payload = {
        "announcement_id": ann_id,
        "courier_id": courier_id,
        "courier_name": courier_name,
        "status": "assigned",
    }
    
    # 1. Annonce publique (sur "selection:<id>")
    #    (Utile si d'autres systèmes voulaient savoir que l'offre est prise)
    selection_chan = CHANNEL_SELECTION_FMT.format(announcement_id=ann_id)
    publish_json(r, selection_chan, selection_payload)
    
    # 2. Notification directe (sur "courier:<id_livreur>")
    #    Informe le livreur gagnant qu'il a le job.
    courier_chan = CHANNEL_COURIER_FMT.format(courier_id=courier_id)
    publish_json(r, courier_chan, selection_payload)
    
    print(f"[Manager] Assignation publiée sur '{selection_chan}' et '{courier_chan}'.")

def process_one(r, ann: Announcement, wait_seconds: float):
    """
    Orchestre le processus complet pour *une* annonce.
    """
    print(f"[Manager] Annonce créée: {ann.to_dict()}")
    
    # 1. PUBLIER L'OFFRE
    #    Publie sur le canal public 'deliveries' que tous les livreurs écoutent.
    publish_json(r, CHANNEL_DELIVERIES, {"type":"announcement", **ann.to_dict()})
    print(f"[Manager] Annonce publiée sur '{CHANNEL_DELIVERIES}'.") 
    
    # 2. ATTENDRE LES RÉPONSES
    #    Passe en mode "écoute" sur le canal 'responses:<id_annonce>'
    chosen = wait_for_responses(r, ann.id, wait_seconds)
    
    # 3. TRAITER LE RÉSULTAT
    if not chosen:
        # Cas 1: Personne n'a répondu
        print("[Manager] Aucun livreur n'a répondu dans le délai imparti.")
        return False
    
    # Cas 2: Un livreur a été choisi
    print(f"[Manager] Livreur choisi: {chosen}")
    
    # 4. ANNONCER LE GAGNANT
    publish_selection(r, ann.id, chosen["courier_id"], chosen.get("courier_name","?"))
    return True

def main():
    """Point d'entrée principal du script Manager."""
    
    # Définit les arguments qu'on peut passer au script
    # ex: python manager.py --pickup "Pizzeria" --reward 10
    parser = argparse.ArgumentParser()
    parser.add_argument("--pickup", default="Restaurant A")
    parser.add_argument("--dropoff", default="Client Z")
    parser.add_argument("--reward", type=float, default=6.5)
    parser.add_argument("--wait", type=float, default=6.0, help="délai d'attente des réponses (s)")
    parser.add_argument("--csv", type=str, help="Chemin d'un CSV d'annonces (pickup,dropoff,reward)")
    parser.add_argument("--interval", type=float, default=1.5, help="pause entre annonces CSV (s)")
    args = parser.parse_args()

    r = get_redis()  # Connexion à Redis

    # --- Logique de publication ---

    # Mode 1: Publier une série d'annonces depuis un fichier CSV
    if args.csv:
        import csv
        with open(args.csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Lecture des infos du CSV, avec valeurs par défaut
                pickup = (row.get("pickup") or args.pickup).strip()
                dropoff = (row.get("dropoff") or args.dropoff).strip()
                reward_str = (row.get("reward") or str(args.reward)).strip()
                try:
                    # Gère les récompenses avec des virgules (ex: 5,5)
                    reward = float(reward_str.replace(",", "."))
                except ValueError:
                    reward = float(args.reward)
                
                # Crée et traite l'annonce
                ann = Announcement.new(pickup, dropoff, reward)
                process_one(r, ann, args.wait)
                time.sleep(args.interval)  # Pause entre chaque annonce
        return  # Fin du script si on était en mode CSV

    # Mode 2: Publier une seule annonce (mode par défaut)
    ann = Announcement.new(args.pickup, args.dropoff, args.reward)
    process_one(r, ann, args.wait)

if __name__ == "__main__":
    main()