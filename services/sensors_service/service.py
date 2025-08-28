import asyncio
import json
from datetime import datetime
import sys
import os
import canopen

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.microservice import Microservice

class SensorsService(Microservice):
    def __init__(self):
        # Call the parent constructor with the official service name
        super().__init__("sensors_service")

    async def _start_logic(self):
        """This is called when the service starts."""
        self.logger.info("Sensors service starting up...")
        self.logger.info("Waiting for settings...")
        await self.get_settings()
        self.logger.info(f"My settings: {self.settings}")

        if self._shutdown_event.is_set(): return

        self.logger.info("Initializing...")

        # CANopen network
        self.network = canopen.Network()

        try:
            interface = self.all_settings["can_bus_service"].get("interface", "virtual")
            bitrate = self.all_settings["can_bus_service"].get("bitrate", "500000")
            channel = self.all_settings["can_bus_service"].get("channel", "vcan0")
            if channel == "" : channel=None
        except KeyError:
            self.logger.error(f"Error retreiving can_bus_service configuration for {self.service_name} service")

        try:
            self.logger.info(f"Start CAN connection : interface={interface}, channel={channel}, bitrate={bitrate}")
            self.network.connect(channel=channel, interface=interface, bitrate=bitrate)
        except Exception as e:
            self.logger.error(f"Error initializing CANopen bus: {e}", exc_info=True)
            return

        # 1. Register the command
        self.command_handler.register_command("scan_sensors", self._handle_scan_sensors)
        # 2. Subscribe to the command subject
        await self._subscribe_to_commands()


    async def _stop_logic(self):
        """This is called when the service is shutting down."""
        self.logger.info("Sensors service shutting down...")
        self.network.disconnect()

    async def _get_lss_addr(self, node):
        """LSS Identity infos"""
        try:
            vendorId = node.sdo[0x1018][1].raw
            productCode = node.sdo[0x1018][2].raw
            revisionNumber = node.sdo[0x1018][3].raw
            serialNumber = node.sdo[0x1018][4].raw
            return vendorId, productCode, revisionNumber, serialNumber
        except Exception as e:
            self.logger.warning(f"LSS addr is not accessible ({e})")
            return None
        

    async def _handle_scan_sensors(self):
        scanned_sensors = {}
        self.logger.info("Scan sensor command received!")

        # WIP
        
        # Get list of sensor to be parametrize :
        parts_sensors_mapping = self.settings.get("parts_sensors_mapping","")
        if parts_sensors_mapping == "" :
            self.logger.error(f"No parts_sensors_mapping parameter in settings !")
            return
        

        # Reset network
        self.logger.info(f"Reset network...")
        self.network.nmt.state = 'RESET'
        await asyncio.sleep(5)


        if False :
            # ret_bool, lss_id_list = self.network.lss.fast_scan()
            # self.logger.info(f"LSS FastScan: {ret_bool} / {lss_id_list}")

            self.network.lss.send_switch_state_global(self.network.lss.CONFIGURATION_STATE)
            node_id = self.network.lss.inquire_node_id()
            # if node_id:
            cmdId = 100
            while( node_id ) :
                self.logger.info(f"LSS inquire_node_id: {node_id}")
                lss_addr = self.network.lss.inquire_lss_address(cmdId+1)
                for part, sensor_config in parts_sensors_mapping.items():
                    if node_id != sensor_config["id"]:
                        continue
                    else:
                        if lss_addr == sensor_config["lss_addr"] :
                            self.logger.info(f"Ok. Sensor {node_id} is the same : {lss_addr}")
                        else :
                            self.logger.info(f"Ko. Sensor {node_id} as changed : From {sensor_config["lss_addr"]} => {lss_addr}")
                            sensor_config["lss_addr"] = lss_addr
                            command = {
                                "command": "update_setting",
                                "group": self.service_name,
                                "key": "parts_sensors_mapping",
                                "value": parts_sensors_mapping
                            }

                            await self.messaging_client.publish(
                                "commands.settings_service",
                                json.dumps(command).encode()
                            )
                        break

                # Add node to network
                node = self.network.add_node(node_id, object_dictionary="config/SimpleInfos.eds")
                # lss = await self._get_lss_addr(node)
                # ret = self.network.lss.send_switch_state_selective(vendorId, productCode, revisionNumber, serialNumber)
                
                node_id = self.network.lss.inquire_node_id()

            return




        # This will attempt to read an SDO from nodes 1 - 127
        self.network.scanner.search()
        # We may need to wait a short while here to allow all nodes to respond
        await asyncio.sleep(5)
        msg = "Found nodes : "
        for node_id in self.network.scanner.nodes:
            msg = msg + f", {node_id} ({hex(node_id)})"
            # Add node to network
            self.network.add_node(node_id, object_dictionary="config/SimpleInfos.eds")

        self.logger.info(f"{msg}")

        # Send info to UI
        payload = {
            "nodes_id": list(self.network),
            "timestamp": datetime.now().isoformat()
        }
        # Publish the data to a unique NATS subject
        await self.messaging_client.publish(
            "sensors.data",
            json.dumps(payload).encode()
        )
        self.logger.info(f"Published message: {payload}")



        # Configuration steps
        # Change network state to NMT preop
        self.network.nmt.state = 'PRE-OPERATIONAL'
        for id, node in self.network.nodes.items():
            self.logger.info(f"Node {id} infos:")
            try:
                node.nmt.wait_for_heartbeat(1)
                assert node.nmt.state == 'PRE-OPERATIONAL'
                self.logger.info(f"Node {id} is in 'PRE-OPERATIONAL' state.")
            except canopen.nmt.NmtError as e:
                self.logger.error(f"{e}")
                continue


            # for k,v in node.object_dictionary.items():
            #     self.logger.info(f"{k}={v}")

            # Device infos
            device_infos = {}
            try:
                deviceType = node.sdo[0x1000].raw
                device_infos["deviceType"] = deviceType
                self.logger.info(f"deviceType = {deviceType}")
            except Exception as e:
                self.logger.warning(f"deviceType is not accessible ({e})")

            # LSS Identity infos
            try:
                vendorId = node.sdo[0x1018][1].raw
                device_infos["vendorId"] = vendorId
                self.logger.info(f"vendorId = {vendorId}")

                if (device_infos["vendorId"] == 0xAD) :
                    # Pepper+Fucks
                    try:
                        serialNumber = node.sdo[0x1018][4].raw
                        device_infos["serialNumber"] = serialNumber
                        self.logger.info(f"serialNumber = {serialNumber}")    
                    except Exception as e:
                        self.logger.warning(f"serialNumber is not accessible ({e})")

                    try:
                        PFserialNumber = node.sdo[0x2201].raw
                        device_infos["PFserialNumber"] = PFserialNumber
                        self.logger.info(f"PFserialNumber = {PFserialNumber}")    
                    except Exception as e:
                        self.logger.warning(f"PFserialNumber is not accessible ({e})")
                        
            except Exception as e:
                self.logger.warning(f"vendorId is not accessible ({e})")

            try:
                productCode = node.sdo[0x1018][2].raw
                device_infos["productCode"] = productCode
                self.logger.info(f"productCode = {productCode}")    
            except Exception as e:
                self.logger.warning(f"productCode is not accessible ({e})")

            try:
                revisionNumber = node.sdo[0x1018][3].raw
                device_infos["revisionNumber"] = revisionNumber
                self.logger.info(f"revisionNumber = {revisionNumber}")    
            except Exception as e:
                self.logger.warning(f"revisionNumber is not accessible ({e})")

            

            scanned_sensors[id] = device_infos


        # Send info to UI
        payload = {
            "scanned_sensors": scanned_sensors,
            "timestamp": datetime.now().isoformat()
        }
        # Publish the data to a unique NATS subject
        await self.messaging_client.publish(
            "sensors.data",
            json.dumps(payload).encode()
        )
        self.logger.info(f"Published message: {payload}")

        # It's good practice to return a confirmation
        # return {"status": "ok", "message": "Start scanning sensors"}




        # Change network state to NMT OPERATIONAL
        self.network.nmt.state = 'OPERATIONAL'
        # for id, node in self.network.nodes.items():
        #     node.nmt.wait_for_heartbeat()
        #     assert node.nmt.state == 'OPERATIONAL'
        #     self.logger.info(f"Node {id} is in 'OPERATIONAL' state.")

        # Remove nodes from network : for next scanner...
        self.network.nodes.clear()
        for id, node in self.network.nodes.items():
            self.logger.info(f"Still node in network = {id}")
    

    async def _publish_counter(self):
        # Use the setting we defined, with a default fallback value
        update_interval = self.settings.get("update_interval", 5)
        while True:
            try:
                await asyncio.sleep(update_interval)
                self.counter += 1
                payload = {
                    "message": "Hello from the Sensors service!",
                    "count": self.counter,
                    "timestamp": datetime.now().isoformat()
                }
                # Publish the data to a unique NATS subject
                await self.messaging_client.publish(
                    "sensors.data",
                    json.dumps(payload).encode()
                )
                self.logger.info(f"Published message: {payload}")
            except asyncio.CancelledError:
                self.logger.info("Publisher task was cancelled.")
                break
