import pandas as pd
import numpy as np
import json
import os
import glob
import sys
sys.path.append('../services/')

try:
    import cantools
    import pyarrow.parquet as pq
    import can
    from digital_twin_service.excavator_model import Excavator
except ImportError as e:
    print(f"Veuillez installer les librairies requises: pip install cantools pyarrow python-can. {e}")
    exit()

def process_logs(app_log_dir_path, can_log_dir_path, dbc_dir_path):
    """
    Traite tous les fichiers de log JSON et leurs fichiers BLF associés dans un répertoire spécifié.
    Charge la base de données DBC pour décoder les messages CAN.

    Args:
        log_dir_path (str): Le chemin du répertoire contenant les fichiers de log.
        root_path (str): Le chemin de la racine du projet pour construire les chemins de fichiers.

    Returns:
        pd.DataFrame: Un DataFrame unique contenant tous les signaux décodés.
                      Retourne None si aucun fichier de log n'est trouvé ou si un échec se produit.
    """
    all_dataframes = []
    
    # Utiliser glob pour trouver tous les fichiers JSON dans le répertoire
    json_files = glob.glob(os.path.join(app_log_dir_path, '*.json'))
    
    if not json_files:
        print(f"Aucun fichier JSON trouvé dans le répertoire '{app_log_dir_path}'.")
        return None

    for json_file_path in json_files:
        try:
            # Charger le fichier JSON de la session
            with open(json_file_path, 'r') as f:
                session_data = json.load(f)
            print(f"Fichier JSON {json_file_path} de session lu avec succès.")

            # Extraire le fichier DBC et d'autres données de session
            dbc_file_path_split = os.path.split(session_data.get('settings').get('can_bus_service').get('dbc_file'))
            dbc_filename = dbc_file_path_split[1]
            if not dbc_filename:
                print(f"Erreur: Le chemin du fichier DBC n'est pas spécifié dans le fichier JSON. ({dbc_file_path_split})")
                continue
            
            # Construire le chemin absolu du fichier DBC
            dbc_full_path = os.path.join(dbc_dir_path, dbc_filename)
            if not os.path.exists(dbc_full_path):
                print(f"Erreur: Le chemin du fichier DBC '{dbc_full_path}' est invalide ou introuvable.")
                continue

            # Charger la base de données DBC pour le décodage
            db = cantools.database.load_file(dbc_full_path)
            print("Fichier DBC chargé avec succès.")

            all_data = []
            blf_files_relative = session_data.get('canBusLogs', [])
            
            # Récupérer les données de session pertinentes
            # gps_data = session_data.get('startPosition', {}).get('properties', {}).get('lastCoord', {})
            session_id = session_data.get('startDate')
            hardness = float(session_data.get('hardness'))
            test_name = session_data.get('testName')

            print(f"{test_name} at {hardness}")

            for blf_file_relative in blf_files_relative:
                # Construire le chemin absolu du fichier BLF
                blf_full_path = os.path.join(can_log_dir_path, os.path.basename(blf_file_relative))
                print(f"Décodage du fichier BLF: {blf_full_path}")
                
                if not os.path.exists(blf_full_path):
                    print(f"\tAttention: Le fichier {blf_full_path} n'existe pas. Ignoré.")
                    continue

                # Utiliser python-can pour lire les messages du fichier BLF
                try:
                    reader = can.LogReader(blf_full_path)
                    decoded_messages = []
                    for msg in reader:
                        try:
                            decoded = db.decode_message(msg.arbitration_id, msg.data)
                            # Ajout d'un préfixe pour différencier les signaux
                            # prefixed_decoded = {f"signal_{k}": v for k, v in decoded.items()}
                            prefixed_decoded = decoded
                            prefixed_decoded['timestamp'] = msg.timestamp
                            # prefixed_decoded['timestamp'] = round(msg.timestamp, 3)
                            # print(f"Msg ts = {round(msg.timestamp, 3)}")
                            decoded_messages.append(prefixed_decoded)
                        except Exception as e:
                            # Ignorer les messages qui ne peuvent pas être décodés
                            continue
                    reader.stop()

                    if decoded_messages:
                        df_decoded = pd.DataFrame(decoded_messages).set_index('timestamp')
                        # df_decoded["timestamp"] = pd.to_datetime(df_decoded["timestamp"])
                        all_data.append(df_decoded)
                    else:
                        print(f"Aucun message décodable trouvé dans '{blf_full_path}'.")
                except Exception as e:
                    print(f"\tErreur lors de la lecture du fichier BLF {blf_full_path} avec python-can: {e}")
                    continue

            if not all_data:
                print("Aucun message décodé. Retour d'un DataFrame vide.")
                continue
            
            # Concaténer tous les DataFrames décodés
            df = pd.concat(all_data).sort_index()
            print("Tous les fichiers BLF ont été décodés et concaténés.")
            
            # Ajouter les données de session pertinentes
            # df['start_lat'] = gps_data.get('LatDecimal')
            # df['start_lon'] = gps_data.get('LonDecimal')
            # df['start_speed'] = gps_data.get('Speed')
            df['session_id'] = session_id
            df['hardness'] = hardness
            df['test_name'] = test_name
            
            all_dataframes.append(df)
            
            ###################################### EXCAVATOR ####################################
            my_excavator = Excavator(session_data.get('settings').get('digital_twin_service').get('excavator'), session_data.get('settings').get('digital_twin_service').get('signal_mapping'))

            # Load DBC file to initialize sensor state
            sensor_state = {}
            if dbc_full_path:
                try:
                    print(f"Loading DBC file from {dbc_full_path}...")
                    db = cantools.db.load_file(dbc_full_path)
                    for message in db.messages:
                        for signal in message.signals:
                            sensor_state[signal.name] = 0
                            # if signal.name == "PF_BOOM_PFAngGF":
                            #     self.logger.info(f"PF_BOOM_PFAngGF exist <<<<<<")
                    print(f"Initialized sensor state with {len(sensor_state)} signals.")
                except FileNotFoundError:
                    print(f"DBC file not found at {dbc_full_path}")
            else:
                print("No dbc_file configured for digital_twin_service.")

        except FileNotFoundError as e:
            print(f"Erreur: Fichier introuvable. Veuillez vérifier le chemin: {e}")
            continue
        except cantools.errors.DbcError as e:
            print(f"Erreur: Le fichier DBC est invalide: {e}")
            continue
        except Exception as e:
            print(f"Une erreur inattendue est survenue lors du traitement: {e}")
            continue


    if all_dataframes:
        return pd.concat(all_dataframes), my_excavator, sensor_state
    else:
        print("Aucun signal n'a pu être décodé à partir des fichiers traités.")
        # return None
        return pd.DataFrame(), my_excavator, sensor_state

if __name__ == '__main__':
    # Exemple d'utilisation du script en mode autonome
    root_path = os.path.join(os.path.dirname(__file__), '..')
    app_log_dir_path = os.path.join(root_path, 'app_logs')
    output_parquet_path = os.path.join(root_path, 'analysis', 'decoded_signals.parquet')
    
    df_full = process_logs(app_log_dir_path, root_path)
    
    if df_full is not None and not df_full.empty:
        df_full.to_parquet(output_parquet_path)
        print(f"Données combinées sauvegardées dans '{output_parquet_path}'.")
        print("\nAperçu des 5 premières lignes du DataFrame final :")
        print(df_full.head())
        print("\nInformations sur le DataFrame final :")
        df_full.info()
    else:
        print("Échec du traitement des fichiers ou le DataFrame est vide.")

