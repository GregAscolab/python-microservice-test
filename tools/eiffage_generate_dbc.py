import copy
import can

import asammdf
import can.logconvert
import pyarrow as pa
import pyarrow.parquet as pq

from cantools import database
from cantools.database import Database, Message, Signal
from cantools.database.conversion import BaseConversion

from collections import defaultdict

import pandas as pd
from matplotlib import pyplot as plt

import os
from pyarrow import fs, parquet
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


FULL_EXPORT = True

# LOG_FILE = "log.mf4"
LOG_FILE_BASENAME = "can_log_20250416_114348"
LOG_FILE_EXT = ".log"
LOG_FILE = LOG_FILE_BASENAME + LOG_FILE_EXT

#####################################################################################################

# Convert Analog RAW values to Pressure in bars
# y = ax + b
# a = (400 / 26110)
a = 400 / ((4.98*32768/5)-(0.996*32768/5))
b = -a * (0.996*32768/5)
print(f"a={a} / b={b}")
#####################################################################################################


# Define signals
db_pcan_tpdo1_signals = [
    Signal(name="DIN0_3", start=0,  length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False)
]

db_pcan_tpdo2_signals = [
    Signal(name="A1_BOOM_HP_b", start=0,  length=16, conversion=BaseConversion.factory(scale=a, offset=b), is_signed=True),
    Signal(name="A2_BOOM_BP_b", start=16, length=16, conversion=BaseConversion.factory(scale=a, offset=b), is_signed=True),
    Signal(name="A3_JIB_HP_b", start=32, length=16, conversion=BaseConversion.factory(scale=a, offset=b), is_signed=True),
    Signal(name="A4_JIB_BP_b", start=48, length=16, conversion=BaseConversion.factory(scale=a, offset=b), is_signed=True)
]

db_pcan_tpdo3_signals = [
    Signal(name="A5_BUCKET_HP_b", start=0,  length=16, conversion=BaseConversion.factory(scale=a, offset=b), is_signed=True),
    Signal(name="A6_BUCKET_BP_b", start=16, length=16, conversion=BaseConversion.factory(scale=a, offset=b), is_signed=True),
    Signal(name="A7", start=32, length=16, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=True),
    Signal(name="A8", start=48, length=16, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=True)
]

db_pcan_tpdo4_signals = [
    Signal(name="A9" , start=0,  length=16, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False),
    Signal(name="A10", start=16, length=16, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False),
    Signal(name="A11", start=32, length=16, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False),
    Signal(name="A12", start=48, length=16, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False)
]

################ Pepperl+Fuchs IMU ##################
INCL_FACTOR = 100
db_PF_tpdo1_signals = [
    Signal(name="Temp", start=0, length=16, conversion=None, is_signed=True),
    Signal(name="InclX", start=16,  length=16, conversion=BaseConversion.factory(scale=1/INCL_FACTOR, offset=0), is_signed=True),
    Signal(name="InclY", start=32, length=16, conversion=BaseConversion.factory(scale=1/INCL_FACTOR, offset=0), is_signed=True)
]

ACC_FACTOR = 1000
db_PF_tpdo5_signals = [
    Signal(name="AccX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/ACC_FACTOR, offset=0), is_signed=True),
    Signal(name="AccY", start=16, length=16, conversion=BaseConversion.factory(scale=1/ACC_FACTOR, offset=0), is_signed=True),
    Signal(name="AccZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/ACC_FACTOR, offset=0), is_signed=True),
    Signal(name="AccAF", start=48, length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False)
]

ROTE_RATE_FACTOR = 100
db_PF_tpdo6_signals = [
    Signal(name="RotRateX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/ROTE_RATE_FACTOR, offset=0), is_signed=True),
    Signal(name="RotRateY", start=16, length=16, conversion=BaseConversion.factory(scale=1/ROTE_RATE_FACTOR, offset=0), is_signed=True),
    Signal(name="RotRateZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/ROTE_RATE_FACTOR, offset=0), is_signed=True),
    Signal(name="RotRateAF", start=48, length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False)
]

ACC_ROTE_RATE_FACTOR = 1
db_PF_tpdo7_signals = [
    Signal(name="AccRotRateX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/ACC_ROTE_RATE_FACTOR, offset=0), is_signed=True),
    Signal(name="AccRotRateY", start=16, length=16, conversion=BaseConversion.factory(scale=1/ACC_ROTE_RATE_FACTOR, offset=0), is_signed=True),
    Signal(name="AccRotRateZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/ACC_ROTE_RATE_FACTOR, offset=0), is_signed=True)
]

GRAVITY_FACTOR = 1000
db_PF_tpdo8_signals = [
    Signal(name="GravityX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/GRAVITY_FACTOR, offset=0), is_signed=True),
    Signal(name="GravityY", start=16, length=16, conversion=BaseConversion.factory(scale=1/GRAVITY_FACTOR, offset=0), is_signed=True),
    Signal(name="GravityZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/GRAVITY_FACTOR, offset=0), is_signed=True)
]

LIN_ACC_FACTOR = 1000
db_PF_tpdo9_signals = [
    Signal(name="LinAccX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/LIN_ACC_FACTOR, offset=0), is_signed=True),
    Signal(name="LinAccY", start=16, length=16, conversion=BaseConversion.factory(scale=1/LIN_ACC_FACTOR, offset=0), is_signed=True),
    Signal(name="LinAccZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/LIN_ACC_FACTOR, offset=0), is_signed=True)
]

PF_ANGLE_FACTOR = 100
db_PF_tpdo10_signals = [
    Signal(name="PFAngX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/PF_ANGLE_FACTOR, offset=0), is_signed=False),
    Signal(name="PFAngY", start=16, length=16, conversion=BaseConversion.factory(scale=1/PF_ANGLE_FACTOR, offset=0), is_signed=False),
    Signal(name="PFAngZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/PF_ANGLE_FACTOR, offset=0), is_signed=False),
    Signal(name="PFAngAF", start=48, length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False),
    Signal(name="PFAngGF", start=56, length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False)
]

EULER_ANGLE_FACTOR = 100
db_PF_tpdo11_signals = [
    Signal(name="EulerX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/EULER_ANGLE_FACTOR, offset=0), is_signed=True),
    Signal(name="EulerY", start=16, length=16, conversion=BaseConversion.factory(scale=1/EULER_ANGLE_FACTOR, offset=0), is_signed=True),
    Signal(name="EulerZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/EULER_ANGLE_FACTOR, offset=0), is_signed=True),
    Signal(name="EulerAF", start=48, length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False),
    Signal(name="EulerGF", start=56, length=8, conversion=BaseConversion.factory(scale=1, offset=0), is_signed=False)
]

QUAT_ANGLE_FACTOR = 1000
db_PF_tpdo12_signals = [
    Signal(name="QuatX", start=0,  length=16, conversion=BaseConversion.factory(scale=1/QUAT_ANGLE_FACTOR, offset=0), is_signed=True),
    Signal(name="QuatY", start=16, length=16, conversion=BaseConversion.factory(scale=1/QUAT_ANGLE_FACTOR, offset=0), is_signed=True),
    Signal(name="QuatZ", start=32, length=16, conversion=BaseConversion.factory(scale=1/QUAT_ANGLE_FACTOR, offset=0), is_signed=True),
    Signal(name="QuatW", start=48, length=16, conversion=BaseConversion.factory(scale=1/QUAT_ANGLE_FACTOR, offset=0), is_signed=True)
]

TEMP_FACTOR = 10
db_PF_tpdo13_signals = [
    Signal(name="TempMems", start=0,  length=16, conversion=BaseConversion.factory(scale=1/TEMP_FACTOR, offset=0), is_signed=True),
    Signal(name="TempMain", start=16, length=16, conversion=BaseConversion.factory(scale=1/TEMP_FACTOR, offset=0), is_signed=True)
]

pf_sensor_node_id_map = {
    "PF_TURRET" : 28,
    "PF_BOOM" : 20,
    "PF_JIB" : 24,
    "PF_BUCKET" : 16
}

NODE_ID_ACQ = 10


# Define messages
db_msgs = [
    Message(name="DIN0_3",  is_extended_frame=False, frame_id=0x180 + NODE_ID_ACQ, length=8, signals=db_pcan_tpdo1_signals),
    Message(name="AIN1_4",  is_extended_frame=False, frame_id=0x280 + NODE_ID_ACQ, length=8, signals=db_pcan_tpdo2_signals),
    Message(name="AIN5_8",  is_extended_frame=False, frame_id=0x380 + NODE_ID_ACQ, length=8, signals=db_pcan_tpdo3_signals),
    # Message(name="AIN9_12", is_extended_frame=False, frame_id=0x480 + NODE_ID_ACQ, length=8, signals=db_pcan_tpdo4_signals),

    # Message(name="PFAngle_11", is_extended_frame=False, frame_id=0x293, length=6, signals=db_PF_tpdo10_signals)
]

for sensor_name, node_id in pf_sensor_node_id_map.items() :
    if FULL_EXPORT:
        tmp_signals=[]
        for s in db_PF_tpdo1_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_Incl",       is_extended_frame=False, frame_id=0x180+node_id,   length=6, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo5_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_Acc",        is_extended_frame=False, frame_id=0x180+node_id+1, length=8, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo6_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_RotRate",    is_extended_frame=False, frame_id=0x280+node_id+1, length=8, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo7_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_AccRotRate", is_extended_frame=False, frame_id=0x380+node_id+1, length=6, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo8_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_Gravity",    is_extended_frame=False, frame_id=0x480+node_id+1, length=6, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo9_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_LinAcc",     is_extended_frame=False, frame_id=0x180+node_id+2, length=6, signals=tmp_signals) )

    tmp_signals=[]
    for s in db_PF_tpdo10_signals:
        sc = copy.copy(s)
        sc.name = sensor_name +'_'+ s.name
        tmp_signals.append(sc)
    db_msgs.append( Message(name=sensor_name+"_PFAng",      is_extended_frame=False, frame_id=0x280+node_id+2, length=8, signals=tmp_signals) )

    if FULL_EXPORT:
        tmp_signals=[]
        for s in db_PF_tpdo11_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_Euler",      is_extended_frame=False, frame_id=0x380+node_id+2, length=8, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo12_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_Quat",       is_extended_frame=False, frame_id=0x480+node_id+2, length=8, signals=tmp_signals) )

        tmp_signals=[]
        for s in db_PF_tpdo13_signals:
            sc = copy.copy(s)
            sc.name = sensor_name +'_'+ s.name
            tmp_signals.append(sc)
        db_msgs.append( Message(name=sensor_name+"_Temp",       is_extended_frame=False, frame_id=0x180+node_id+3, length=4, signals=tmp_signals) )


# Define database
db = Database(messages=db_msgs)

print(f"Database =\n{db}")

# Dump database to disk
if FULL_EXPORT:
    database.dump_file(db, "db-full-v3.dbc")
else:
    database.dump_file(db, "db-light-v2.dbc")

