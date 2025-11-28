# from can import CanError
# import cantools
import canopen
# import paho.mqtt.client as mqtt
# import json
# from pynput import keyboard
from datetime import datetime
import time
import os
import argparse
import logging
# import threading
# from enum import Enum
# import boto3
# from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import signal
import sys
# from BaseMsgListener import MQTTListener, ListenerFactory, MsgDecoder

# from ThingsboardMqttClient import ThingsBoardClient as tb_client

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def signal_handler(sig, frame):
    logging.info("Ctrl+C pressed. Exiting...")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Peak-MicroMod configuration tool")
    parser.add_argument('--interface', type=str, default='socketcan', help="CAN interface (e.g., pcan, vcan). Default is 'pcan'.")
    parser.add_argument('--channel', type=str, default="canfd1", help="CAN channel. Try auto detection if not set.")
    parser.add_argument('--bitrate', type=int, default=500000, help="CAN bus bitrate. Default is 500000.")
    parser.add_argument('--new_bitrate', type=int, default=500000, help="New CAN bus bitrate after configuration. Default is 500000.")
    parser.add_argument('--dbc', type=str, default='db.dbc', help="Path to the DBC file. Default is 'db.dbc'.")
    parser.add_argument('--eds', type=str, default='PCAN-MicroMod-FD-Analog1_CiA401.eds', help="Path to the EDS file. Default is 'PCAN-MicroMod-FD-Analog1_CiA401.eds'.")
    parser.add_argument('--node_id', type=int, default=None, help="Current node_id to be configured")
    parser.add_argument('--new_node_id', type=int, default=None, help="New node id for the node")

    args = parser.parse_args()

    BASE_PDO1_COB_ID = 0x180
    BASE_PDO2_COB_ID = 0x280
    BASE_PDO3_COB_ID = 0x380
    BASE_PDO4_COB_ID = 0x480
    BASE_PDO5_COB_ID = 0x180
    BASE_PDO6_COB_ID = 0x280
    BASE_PDO7_COB_ID = 0x380
    BASE_PDO8_COB_ID = 0x480
    BASE_PDO9_COB_ID = 0x180
    BASE_PDO10_COB_ID = 0x280
    BASE_PDO11_COB_ID = 0x380
    BASE_PDO12_COB_ID = 0x480
    BASE_PDO13_COB_ID = 0x180

    CYCLIC_PERIOD_MS = 10
    CYCLIC_PERIOD_TEMP_MS = 1000
    step = 0

    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)


    # # Vérification de l'existence du fichier DBC
    # if not os.path.exists(args.dbc):
    #     logging.error(f"Le fichier DBC {args.dbc} n'existe pas.")
    #     exit(1)

    # db = cantools.database.load_file(args.dbc)

    # # Configuration du bus CAN
    # # Find all CAN-bus interface channels
    # itf_chns = [x["channel"] for x in can.detect_available_configs(args.interface)]
    # logging.info(f"Found channels= {itf_chns}")

    # # If no interface channel provided, default to first found
    # if args.channel is None and len(itf_chns) > 0:
    #     args.channel = itf_chns[0]
    # else:
    #     logging.error("Aucun canal d'interface CAN trouvé.")
    #     exit(1)

    
    # CANopen network
    network = canopen.Network()

    node_id_to_reconfigure = args.node_id


    try:
        logging.info(f"Start CAN connection : interface={args.interface}, channel={args.channel}, bitrate={args.bitrate}")
        network.connect(interface=args.interface, bitrate=args.bitrate)

        # Reset network
        network.nmt.state = 'RESET'
        logging.info(f"Reset network...")
        time.sleep(2)

        if node_id_to_reconfigure == None :
            # This will attempt to read an SDO from nodes 1 - 127
            network.scanner.search()
            # We may need to wait a short while here to allow all nodes to respond
            time.sleep(2)
            for node_id in network.scanner.nodes:
                logging.info(f"Found node {node_id} ({hex(node_id)})!")
                # if node_id != 1:
                node_id_to_reconfigure = node_id
        
            # Todo : Display list of node found and wait for user input

            
        if node_id_to_reconfigure == None :
            logging.error(f"No node to configure found!")
            network.disconnect()
            exit(0)
        else:
            user_val = input(f"Confirm node_id_to_reconfigure [{node_id_to_reconfigure}]")
            if user_val == '':
                logging.debug(f"Use auto value {node_id_to_reconfigure}")
            else :
                node_id_to_reconfigure = int(user_val)
            
            logging.info(f"Node to configure = {node_id_to_reconfigure}")

        if(args.new_node_id == None):
            user_val = input("Enter new node_id:")
            if user_val == '':
                new_node_id = node_id_to_reconfigure
                logging.warning(f"No new id to configure, keep the same={new_node_id}")
            else:
                new_node_id = int(user_val)

        else :
            new_node_id = args.new_node_id

        logging.info(f"New node_id to be applied={new_node_id}")




        # Add node to network
        node = network.add_node(node_id_to_reconfigure, args.eds)

        # Configuration steps
        # Change network state to NMT preop
        network.nmt.state = 'PRE-OPERATIONAL'
        node.nmt.wait_for_heartbeat()
        assert node.nmt.state == 'PRE-OPERATIONAL'
        logging.info(f"Node {node_id_to_reconfigure} is in 'PRE-OPERATIONAL' state.")

        for k,v in node.object_dictionary.items():
            logging.info(f"{k}={v}")

        # Device infos
        for idx in [0x1000, 0x1008]:
            logging.info(f" {node.object_dictionary[idx].name} = {node.sdo[idx].raw}")

        # # LSS Identity infos
        # network.lss.send_switch_state_global(network.lss.CONFIGURATION_STATE)
        # ret, list = network.lss.fast_scan()
        # print(f"fast_scan : {ret}\n{list}")

        # lss_addr = network.lss.inquire_lss_address(0)
        # print (f"inquire_lss_address : {lss_addr}")

        # vendorId = node.sdo[0x1018][1].raw
        # productCode = node.sdo[0x1018][2].raw
        # revisionNumber = node.sdo[0x1018][3].raw
        # # serialNumber = node.sdo[0x1018][4].raw

        # logging.info(f"LSS 0x1018 = {node.sdo[0x1018][0].raw}")
        # logging.info(f"vendorId = {node.sdo[0x1018][1].raw}")
        # logging.info(f"productCode = {node.sdo[0x1018][2].raw}")
        # logging.info(f"revisionNumber = {node.sdo[0x1018][3].raw}")
        # # logging.info(f"serialNumber = {node.sdo[0x1018][4].raw}")

        network.lss.send_switch_state_global(network.lss.WAITING_STATE)
        exit(0)

        # Go to LSS configuration mode
        network.lss.send_switch_state_global(network.lss.CONFIGURATION_STATE)
        # slave_ok = network.lss.send_switch_state_selective(vendorId, productCode, revisionNumber, serialNumber)

        if not slave_ok:
            logging.error("No LSS slave available !!!")
            exit(0)

        network.lss.configure_node_id(new_node_id)
        # Change network speed
        bitrates = {250000:3,
                    500000:2}
        if args.new_bitrate in bitrates :
            new_bitrate = args.new_bitrate
            network.lss.configure_bit_timing(bitrates[new_bitrate])
        else:
            logging.warning("New bitrate not available!!! Use same bitrate.")
            new_bitrate = args.bitrate

        network.lss.store_configuration()
        network.lss.send_switch_state_global(network.lss.WAITING_STATE)

        node = network.add_node(new_node_id, args.eds)

        network.nmt.state = 'RESET'
        node.nmt.wait_for_heartbeat()
        node.nmt.state = 'PRE-OPERATIONAL'
        node.nmt.wait_for_heartbeat()
        assert node.nmt.state == 'PRE-OPERATIONAL'
        logging.info(f"Node {node_id_to_reconfigure} has to be switch off")

        network.disconnect()

        user_val = input("When device is switch on, presse a key...")
        #### Change network speed to new speed
        network.connect(interface=args.interface, bitrate=new_bitrate)
        node.nmt.wait_for_heartbeat()
        node.nmt.state = 'OPERATIONAL'
        node.nmt.wait_for_heartbeat()
        assert node.nmt.state == 'OPERATIONAL'

        logging.info(f"End of configuration.\n\tNodeId {node_id_to_reconfigure}, change to {new_node_id}\n\tbitrate {args.bitrate}, change to {new_bitrate}")

    except Exception as e :
        logging.error(f"Error = {e}")


    network.disconnect()
    logging.info(f"End of main()")

if __name__ == "__main__":
    main()
