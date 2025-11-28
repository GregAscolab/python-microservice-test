import canopen
import time
import argparse
import logging
import signal
import sys

# Configuration du logging
# Un format plus détaillé pour les messages de journalisation
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])

def signal_handler(sig, frame):
    """Gère l'interruption par l'utilisateur (Ctrl+C)."""
    logging.info("Ctrl+C détecté. Arrêt du script...")
    sys.exit(0)

def main():
    """Fonction principale du script de configuration de l'IMU."""

    # Initialisation de l'analyseur d'arguments en ligne de commande
    parser = argparse.ArgumentParser(description="Outil de configuration IMU Pepperl+Fuchs")
    parser.add_argument('--interface', type=str, default='socketcan', help="Interface CAN (ex: pcan, vcan). Par défaut : 'pcan'.")
    parser.add_argument('--channel', type=str, default="canfd1", help="Canal CAN. Détection automatique si non défini.")
    parser.add_argument('--bitrate', type=int, default=500000, help="Débit binaire du bus CAN. Par défaut : 500000.")
    parser.add_argument('--new_bitrate', type=int, default=500000, help="Nouveau débit binaire du bus CAN après la configuration. Par défaut : 500000.")
    parser.add_argument('--eds', type=str, default='18-34862A.eds', help="Chemin vers le fichier EDS. Par défaut : '18-34862A.eds'.")
    parser.add_argument('--node_id', type=int, default=None, help="ID de noeud actuel à configurer.")
    parser.add_argument('--new_node_id', type=int, default=None, help="Nouvel ID de noeud pour le module (ex: Turret=16, Boom=20, Jib=24, Bucket=28).")
    
    args = parser.parse_args()

    # Définition des constantes pour les IDs COB (Communication Object)
    BASE_PDO_COB_IDS = {
        'TPDO1': 0x180, 'TPDO2': 0x280, 'TPDO3': 0x380, 'TPDO4': 0x480,
        'TPDO5': 0x180, 'TPDO6': 0x280, 'TPDO7': 0x380, 'TPDO8': 0x480,
        'TPDO9': 0x180, 'TPDO10': 0x280, 'TPDO11': 0x380, 'TPDO12': 0x480,
        'TPDO13': 0x180
    }
    
    CYCLIC_PERIOD_MS = 50
    CYCLIC_PERIOD_TEMP_MS = 1000

    # Gestionnaire de signal pour une sortie propre
    signal.signal(signal.SIGINT, signal_handler)

    network = None
    node = None

    try:
        # Initialisation de la connexion CANopen
        logging.info(f"Démarrage de la connexion CAN : interface='{args.interface}', canal='{args.channel}', débit={args.bitrate}")
        network = canopen.Network()
        network.connect(interface=args.interface, bitrate=args.bitrate, channel=args.channel)
        
        node_id_to_reconfigure = args.node_id

        # Recherche de noeuds si aucun ID n'est spécifié
        if node_id_to_reconfigure is None:
            logging.info("Aucun ID de noeud spécifié. Recherche de noeuds sur le bus...")
            network.scanner.search()
            time.sleep(2) # Attente pour permettre aux noeuds de répondre
            
            found_nodes = list(network.scanner.nodes)
            logging.info(f"noeuds trouvés : {found_nodes}")

            if len(found_nodes) == 0:
                logging.error("Aucun noeud à configurer n'a été trouvé.")
                return
            
            # Sélection du premier noeud non maître (ID != 1)
            for node_id in found_nodes:
                if node_id != 1:
                    node_id_to_reconfigure = node_id
                    break
            
            if node_id_to_reconfigure is None:
                logging.error("Aucun noeud non maître n'a été trouvé pour la configuration.")
                return

            user_val = input(f"Confirmer l'ID du noeud à reconfigurer [{node_id_to_reconfigure}] : ")
            if user_val:
                try:
                    node_id_to_reconfigure = int(user_val)
                except ValueError:
                    logging.warning(f"Entrée invalide '{user_val}'. Utilisation de l'ID de noeud détecté : {node_id_to_reconfigure}")

        logging.info(f"ID du noeud à configurer : {node_id_to_reconfigure}")

        # Détermination du nouvel ID de noeud
        new_node_id = args.new_node_id
        if new_node_id is None:
            print("IDs recommandés canDb-v1 : Turret=16 / Boom=20 / Jib=24 / Bucket=28")
            print("IDs recommandés canDb-v2 : Bucket=16 / Boom=20 / Jib=24 / Turret=28")
            user_val = input("Entrez le nouvel ID de noeud : ")
            if user_val:
                try:
                    new_node_id = int(user_val)
                except ValueError:
                    logging.error(f"Entrée invalide pour le nouvel ID de noeud : '{user_val}'. Le script va s'arrêter.")
                    return
            else:
                logging.warning(f"Aucun nouvel ID spécifié. L'ID de noeud ne sera pas modifié.")
                new_node_id = node_id_to_reconfigure
        
        logging.info(f"Le nouvel ID de noeud à appliquer est : {new_node_id}")

        # Ajout du noeud au réseau CANopen
        try:
            node = network.add_node(node_id_to_reconfigure, args.eds)
        except Exception as e:
            logging.error(f"Impossible d'ajouter le noeud {node_id_to_reconfigure}. Vérifiez l'ID et le fichier EDS.")
            raise e

        # Passage en état pré-opérationnel
        logging.info(f"Passage du noeud {node_id_to_reconfigure} en état 'PRE-OPERATIONAL'...")
        node.nmt.state = 'PRE-OPERATIONAL'
        node.nmt.wait_for_heartbeat()
        if node.nmt.state != 'PRE-OPERATIONAL':
            raise Exception("Le noeud n'a pas pu passer en état PRE-OPERATIONAL.")
        logging.info("Le noeud est maintenant en état 'PRE-OPERATIONAL'.")

        # Affichage des informations de l'appareil
        logging.info("--- Informations sur l'appareil ---")
        try:
            for idx in [0x1000, 0x1008, 0x2201]:
                logging.info(f"Index {hex(idx)} ({node.object_dictionary[idx].name}) : {node.sdo[idx].raw}")
        except Exception as e:
            logging.warning(f"Impossible de lire les informations de l'appareil : {e}")
        
        # Récupération des informations LSS (Layer Setting Services)
        logging.info("--- Informations LSS ---")
        vendorId = node.sdo[0x1018][1].raw
        productCode = node.sdo[0x1018][2].raw
        revisionNumber = node.sdo[0x1018][3].raw
        serialNumber = node.sdo[0x1018][4].raw
        logging.info(f"vendorId = {vendorId}")
        logging.info(f"productCode = {productCode}")
        logging.info(f"revisionNumber = {revisionNumber}")
        logging.info(f"serialNumber = {serialNumber}")

        # Étape 1 : Réinitialisation aux paramètres d'usine
        logging.info("--- Étape 1 : Réinitialisation aux paramètres d'usine ---")
        logging.info("Réinitialisation des paramètres par défaut du noeud...")
        try:
            node.sdo[0x1011][0x01].raw = 0x64616F6C  # 'load'
        except Exception as e:
            logging.error(f"Erreur lors de la réinitialisation des paramètres : {e}")
            raise e
        
        logging.info("Réinitialisation du noeud...")
        node.nmt.state = 'RESET'
        node.nmt.wait_for_heartbeat()
        
        logging.info("Passage en état 'PRE-OPERATIONAL' pour la suite de la configuration...")
        node.nmt.state = 'PRE-OPERATIONAL'
        node.nmt.wait_for_heartbeat()
        if node.nmt.state != 'PRE-OPERATIONAL':
            raise Exception("Le noeud n'a pas pu se réinitialiser et passer en mode PRE-OPERATIONAL.")
        logging.info("Le noeud est de nouveau en état 'PRE-OPERATIONAL'.")

        # Étape 2 : Configuration du Heartbeat
        logging.info("--- Étape 2 : Configuration du Heartbeat ---")
        try:
            node.sdo[0x1017].raw = 200
            logging.info("Période Heartbeat configurée à 200 ms.")
        except Exception as e:
            logging.error(f"Erreur lors de la configuration du Heartbeat : {e}")

        # Étape 3 : Configuration des paramètres spécifiques
        logging.info("--- Étape 3 : Configuration des TPDO ---")

        ASCOREL_EXCAVATOR_SETTINGS = False  # Exemple d'option
        ASCOLAB_ROCKMETER_SETTINGS = True # Exemple d'option
        
        if ASCOREL_EXCAVATOR_SETTINGS:
            logging.info("Utilisation des paramètres ASCOREL_EXCAVATOR.")
            try:
                # Configuration de TPDO10 pour les angles PF
                logging.info("Configuration de TPDO10 (PF Angles)...")
                node.sdo[0x1809][0x01].bits[31] = 1 # Désactivation pour configuration
                node.sdo[0x1809][0x02].raw = 0xFE # Type de transmission (événementiel)
                node.sdo[0x1809][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x1809][0x01].raw = BASE_PDO_COB_IDS['TPDO10'] + new_node_id
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO10 : {e}")

            try:
                # Configuration des paramètres d'angle PF
                logging.info("Configuration des angles PF (0x200C)...")
                node.sdo[0x200C][0x01].raw = 100
                node.sdo[0x200C][0x02].raw = 0
                node.sdo[0x200C][0x03].raw = 2
                node.sdo[0x200C][0x04].raw = 4
            except Exception as e:
                logging.error(f"Erreur lors de la configuration des paramètres d'angle : {e}")

        elif ASCOLAB_ROCKMETER_SETTINGS:
            logging.info("Utilisation des paramètres ASCOLAB_ROCKMETER.")
            try:
                # Configuration de TPDO5 (Accélération)
                logging.info("Configuration de TPDO5 (Accélération)...")
                node.sdo[0x1804][0x01].bits[31] = 1 # Désactivation pour configuration
                node.sdo[0x1804][0x02].raw = 0xFE # Type de transmission
                node.sdo[0x1804][0x03].raw = int(CYCLIC_PERIOD_MS*10) # Période cyclique
                node.sdo[0x1804][0x01].raw = BASE_PDO_COB_IDS['TPDO5'] + new_node_id + 1
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO5 : {e}")

            try:
                # Configuration de TPDO6 (Vitesse de rotation)
                logging.info("Configuration de TPDO6 (Vitesse de rotation)...")
                node.sdo[0x1805][0x01].bits[31] = 1
                node.sdo[0x1805][0x02].raw = 0xFE
                node.sdo[0x1805][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x1805][0x01].raw = BASE_PDO_COB_IDS['TPDO6'] + new_node_id + 1
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO6 : {e}")

            try:
                # Configuration de TPDO7 (Accélération rotationnelle)
                logging.info("Configuration de TPDO7 (Accélération rotationnelle)...")
                node.sdo[0x1806][0x01].bits[31] = 1
                node.sdo[0x1806][0x02].raw = 0xFE
                node.sdo[0x1806][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x1806][0x01].raw = BASE_PDO_COB_IDS['TPDO7'] + new_node_id + 1
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO7 : {e}")
            
            try:
                # Configuration de TPDO8 (Vecteur de gravité)
                logging.info("Configuration de TPDO8 (Vecteur de gravité)...")
                node.sdo[0x1807][0x01].bits[31] = 1
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO8 : {e}")

            try:
                # Configuration de TPDO9 (Accélération linéaire)
                logging.info("Configuration de TPDO9 (Accélération linéaire)...")
                node.sdo[0x1808][0x01].bits[31] = 1
                node.sdo[0x1808][0x02].raw = 0xFE
                node.sdo[0x1808][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x1808][0x01].raw = BASE_PDO_COB_IDS['TPDO9'] + new_node_id + 2
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO9 : {e}")

            try:
                # Configuration de TPDO10 (Angles PF)
                logging.info("Configuration de TPDO10 (Angles PF)...")
                node.sdo[0x1809][0x01].bits[31] = 1
                node.sdo[0x1809][0x02].raw = 0xFE
                node.sdo[0x1809][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x1809][0x01].raw = BASE_PDO_COB_IDS['TPDO10'] + new_node_id + 2
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO10 : {e}")

            try:
                # Configuration de TPDO11 (Angles d'Euler)
                logging.info("Configuration de TPDO11 (Angles d'Euler)...")
                node.sdo[0x180A][0x01].bits[31] = 1
                node.sdo[0x180A][0x02].raw = 0xFE
                node.sdo[0x180A][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x180A][0x01].raw = BASE_PDO_COB_IDS['TPDO11'] + new_node_id + 2
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO11 : {e}")

            try:
                # Configuration de TPDO12 (Quaternion)
                logging.info("Configuration de TPDO12 (Quaternion)...")
                node.sdo[0x180B][0x01].bits[31] = 1
                node.sdo[0x180B][0x02].raw = 0xFE
                node.sdo[0x180B][0x03].raw = int(CYCLIC_PERIOD_MS*10)
                node.sdo[0x180B][0x01].raw = BASE_PDO_COB_IDS['TPDO12'] + new_node_id + 2
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO12 : {e}")

            try:
                # Configuration de TPDO13 (Température)
                logging.info("Configuration de TPDO13 (Température)...")
                node.sdo[0x180C][0x01].bits[31] = 1
                node.sdo[0x180C][0x02].raw = 0xFE
                node.sdo[0x180C][0x03].raw = int(CYCLIC_PERIOD_TEMP_MS*10)
                node.sdo[0x180C][0x01].raw = BASE_PDO_COB_IDS['TPDO13'] + new_node_id + 3
            except Exception as e:
                logging.error(f"Erreur lors de la configuration de TPDO13 : {e}")

            try:
                # Configuration des paramètres d'angle PF
                logging.info("Configuration des angles PF (0x200C)...")
                node.sdo[0x200C][0x01].raw = 100
                node.sdo[0x200C][0x02].raw = 0
                node.sdo[0x200C][0x03].raw = 2
                node.sdo[0x200C][0x04].raw = 4
            except Exception as e:
                logging.error(f"Erreur lors de la configuration des paramètres d'angle : {e}")

            try:
                # Configuration du Quaternion
                logging.info("Configuration du Quaternion (0x200E)...")
                node.sdo[0x200E][0x01].raw = 1000
                node.sdo[0x200E][0x02].raw = 0
            except Exception as e:
                logging.error(f"Erreur lors de la configuration du Quaternion : {e}")

        # Étape 4 : Enregistrement des paramètres dans la mémoire
        logging.info("--- Étape 4 : Enregistrement et changement de l'ID de noeud ---")
        try:
            logging.info("Enregistrement des paramètres en mémoire...")
            node.sdo[0x1010][0x01].raw = 0x65766173  # 'save'
        except Exception as e:
            logging.error(f"Échec de l'enregistrement des paramètres : {e}")
            
        # Démarrage de la configuration LSS
        logging.info("Passage en mode de configuration LSS...")
        network.lss.send_switch_state_selective(vendorId, productCode, revisionNumber, serialNumber)
        
        # Le changement d'ID de noeud est une opération critique
        logging.info(f"Changement de l'ID de noeud de {node_id_to_reconfigure} à {new_node_id}...")
        network.lss.configure_node_id(new_node_id)
        
        # Changement du débit binaire
        bitrates = {250000: 3, 500000: 2}
        if args.new_bitrate in bitrates:
            logging.info(f"Changement du débit binaire de {args.bitrate} à {args.new_bitrate}...")
            network.lss.configure_bit_timing(bitrates[args.new_bitrate])
        else:
            logging.warning("Le nouveau débit binaire n'est pas pris en charge. L'ancien sera conservé.")
            args.new_bitrate = args.bitrate

        network.lss.store_configuration()
        network.lss.send_switch_state_global(network.lss.WAITING_STATE)
        
        # Validation finale
        logging.info("Configuration LSS terminée. Le noeud a été mis à jour.")
        logging.info("Veuillez éteindre et rallumer l'appareil pour appliquer les changements.")
        input("Appuyez sur 'Entrée' une fois que vous avez redémarré le capteur...")

        logging.info(f"Reconnexion au réseau avec le nouveau débit binaire ({args.new_bitrate})...")
        network.disconnect()
        network.connect(interface=args.interface, bitrate=args.new_bitrate, channel=args.channel)
        
        logging.info(f"Attente du noeud avec l'ID {new_node_id}...")
        new_node = network.add_node(new_node_id, args.eds)
        new_node.nmt.wait_for_heartbeat()
        new_node.nmt.state = 'OPERATIONAL'
        new_node.nmt.wait_for_heartbeat()
        if new_node.nmt.state != 'OPERATIONAL':
            raise Exception("Le noeud n'a pas pu passer en mode OPERATIONAL avec le nouveau débit binaire.")
        
        logging.info("Validation réussie :")
        logging.info(f"\tID de noeud: {node_id_to_reconfigure} -> {new_node_id}")
        logging.info(f"\tDébit binaire: {args.bitrate} -> {args.new_bitrate}")
        logging.info("Le capteur fonctionne correctement avec les nouveaux paramètres.")

    except canopen.sdo.SdoCommunicationError as e:
        logging.error(f"Erreur de communication SDO : {e}. Assurez-vous que l'ID du noeud est correct et que le noeud est en mode PRE-OPERATIONAL.")
    except canopen.nmt.NmtError as e:
        logging.error(f"Erreur NMT : {e}. Le noeud ne répond pas au heartbeat.")
    # except canopen.node.NodeError as e:
    #     logging.error(f"Erreur de noeud : {e}. Le fichier EDS peut être manquant ou incorrect.")
    # except canopen.network.CanError as e:
    #     logging.error(f"Erreur CAN : {e}. Vérifiez votre connexion et les paramètres d'interface/canal.")
    except Exception as e:
        # Bloc générique pour toute autre erreur inattendue
        logging.critical(f"Une erreur inattendue s'est produite : {e}")

    finally:
        # S'assure que la connexion est toujours fermée
        if network:
            logging.info("Déconnexion du réseau CAN.")
            network.disconnect()
        logging.info("Fin du script.")

if __name__ == "__main__":
    main()
