from common.owa_rtu import Rtu
from common.owa_io import Io
from common.owa_gps2 import Gps
# from ctypes import *
# from PubSubClient import NatsClient

import asyncio

import time
import signal
import logging as log

running = True

# Configuration du logging
log.basicConfig(level=log.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def signal_handler(sig, frame):
    global running
    log.info("Ctrl+C pressed. Stop running...")
    running = False

# Set up signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

MODEM_TYPE = "owa5x"

async def main():
    # io = Io()
    # rtu = Rtu()
    gps = Gps()

    # NATS connection initialisation
    #nats_client = NatsClient()
    # nats_client.register_callback('startRecording', self.start_recording)
    #await nats_client.connect()
    #await nats_client.subscribe('commands')
    #js = nats_client.jetstream()


    # io.initialize()
    # io.start()
    # rtu.initialize()
    # rtu.start()
    # io.switch_gps_on_off(1)
    gps.gps_init(modem_type=MODEM_TYPE)


    while running:
        gps.getFullGPSPosition()
        print(f"GPS={gps.lastCoord}")
        #await nats_client.publish("can_data", json.dumps(p).encode())
        await asyncio.sleep(2)


    gps.finalize()
    # io.finalize()
    # rtu.finalize()



if __name__ == '__main__':
    asyncio.run(main())
