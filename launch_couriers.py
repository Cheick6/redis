import argparse  # Pour lire l'argument --csv
import csv  # Pour lire le fichier CSV
import subprocess  # Pour lancer d'autres scripts Python (les 'courier.py')
import sys  # Pour quitter le script en cas d'erreur
import os  # Pour vérifier si le fichier CSV existe

def main():
    """Point d'entrée du lanceur."""
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/couriers.csv", help="CSV avec colonnes: id,name,accept_rate")
    args = parser.parse_args()

    # Vérification de sécurité: le fichier CSV existe-t-il ?
    if not os.path.exists(args.csv):
        print(f"[Launcher] Fichier introuvable: {args.csv}")
        sys.exit(1)  # Arrête le script avec un code d'erreur

    procs = []  # Liste pour garder en mémoire tous les processus que nous lançons
    
    # Ouvre le fichier CSV
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)  # Lit le CSV comme une liste de dictionnaires
        
        # Boucle sur chaque ligne (chaque livreur) du fichier
        for row in reader:
            # Récupère les infos, avec des valeurs par défaut si les colonnes manquent
            cid = (row.get("id") or "").strip()
            name = (row.get("name") or "Livreur").strip() or "Livreur"
            rate = (row.get("accept_rate") or "0.9").strip() or "0.9"
            
            if not cid:
                continue  # Ignore les lignes sans ID
            
            # Construit la commande à exécuter dans le terminal, ex:
            # [ "python", "courier.py", "--id", "c1", "--name", "Bob", "--accept-rate", "0.9" ]
            cmd = [sys.executable, "courier.py", "--id", cid, "--name", name, "--accept-rate", rate]
            
            print("[Launcher] Spawn:", " ".join(cmd))  # Affiche la commande
            
            # LANCE LE PROCESSUS !
            # subprocess.Popen exécute la commande dans un nouveau processus
            # Le script 'launch_couriers.py' continue sans attendre la fin de 'courier.py'
            procs.append(subprocess.Popen(cmd))
    
    print(f"[Launcher] {len(procs)} livreur(s) lancé(s). Appuie sur Ctrl+C pour arrêter.")
    
    try:
        # Le script principal (launcher) se met en pause et attend que
        # tous les processus enfants (les livreurs) se terminent.
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        # Si l'utilisateur appuie sur Ctrl+C dans le terminal du launcher...
        print("\n[Launcher] Arrêt demandé (Ctrl+C). Terminaison des processus livreurs...")
        # ...on envoie un signal d'arrêt (terminate) à tous les processus
        # livreurs qu'on a lancés.
        for p in procs:
            p.terminate()
        print("[Launcher] Tous les livreurs sont arrêtés.")

if __name__ == "__main__":
    main()