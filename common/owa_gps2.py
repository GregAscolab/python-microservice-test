import logging #as log
from ctypes import *
from threading import Thread
from queue import Queue
import time
from typing import IO, Tuple
import common.utils as utils
from common.owa_errors import OwaErrors as oe, OwaErrorMgt as oem

from math import modf
from datetime import datetime, timezone

from common.messaging import MessagingClient
import json

from enum import IntEnum

libGps=cdll.LoadLibrary("libGPS2_Module.so")

######## Logger config ##########
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

streamLog = logging.StreamHandler()
streamLog.setFormatter(formatter)
log.addHandler(streamLog)

logFile = logging.FileHandler(__name__ + '.log')
logFile.setFormatter(formatter)
log.addHandler(logFile)

############# GPS ###########

class OwaComPort(IntEnum):
    COM1 = 0
    COM2 = 1
    COM3 = 2
    COM4 = 3
    COM5 = 4
    COM6 = 5

class OwaGpsDynamicModel(IntEnum):
    PORTABLE = 0
    STATIONARY = 2
    PEDESTRIAN = 3
    AUTOMOTIVE = 4
    SEA = 5
    AIRBORNE_1G = 6
    AIRBORNE_2G = 7
    AIRBORNE_4G = 8

# GPS struct config wrapper
class GPS_Configuration(Structure):
    max_receiver_name = 20 #c_int.in_dll(libGps, "MAX_RECEIVER_NAME")
    max_protocol_name = 10 #c_int.in_dll(libGps, "MAX_PROTOCOL_NAME")

    _fields_ = [ ("DeviceReceiverName", c_char * max_receiver_name ),
                ("ParamBaud", c_uint),
                ("ParamParity", c_int),
                ("ParamLength", c_ubyte),
                ("ProtocolName", c_char * max_protocol_name),
                ("GPSPort", c_ubyte)]

    def __repr__(self) -> str:
        return f"DeviceReceiverName={self.DeviceReceiverName}\nParamBaud={self.ParamBaud}\nParamParity={self.ParamParity}\nParamLength={self.ParamLength}\nProtocolName={self.ProtocolName}\nGPSPort={self.GPSPort}"


# GPS Coord structure wrapper
class GPS_Coord(Structure):
    _fields_ = [ ("Degrees", c_ushort),
                 ("Minutes", c_ubyte),
                 ("Seconds", c_double),
                 ("Dir", c_char)]

# GPS position data structure wrapper
class GPS_PositionData(Structure):
    _fields_ = [ ("PosValid", c_ubyte),
                 ("OldValue", c_ubyte),
                 ("Latitude", GPS_Coord),
                 ("Longitude", GPS_Coord),
                 ("Altitude", c_double),
                 ("NavStatus", c_char * 3),
                 ("HorizAccu", c_double),
                 ("VertiAccu", c_double),
                 ("Speed", c_double),
                 ("Course", c_double),
                 ("HDOP", c_double),
                 ("VDOP", c_double),
                 ("TDOP", c_double),
                 ("numSvs", c_ubyte),
                 ("LatDecimal", c_double),
                 ("LonDecimal", c_double)]
    def __repr__(self) -> str:
        return "PosValid=" + str(self.PosValid) +" (" + str(self.LatDecimal) + "," + str(self.LonDecimal) + "," + str(self.Altitude) + ") Speed=" + str(self.Speed) + " Course=" + str(self.Course) + " HDOP=" + str(self.HDOP)

class UTC_DateTime(Structure):
    _fields_ = [ ("Hours", c_ubyte),
                 ("Minutes", c_ubyte),
                 ("Seconds", c_float),
                 ("Day", c_ubyte),
                 ("Month", c_ubyte),
                 ("Year", c_int)]

    def __repr__(self) -> str:
        return str(self.Year) + ":" + str(self.Month) + ":" + str(self.Day) + " " + str(self.Hours) + ":" + str(self.Minutes) + ":" + str(self.Seconds)

class SV_Data(Structure):
    _fields_ = [ ("SV_Id", c_ubyte),
                 ("SV_Elevation", c_ubyte),
                 ("SV_Azimuth", c_int16),
                 ("SV_SNR", c_ubyte)
                ]

class GSV_Data(Structure):
    _fields_ = [
        ("SV_InView", c_byte),
        ("SV", SV_Data * 64)
    ]

# Main GPS class wrapper
class Gps():

    def __init__(self, nats:MessagingClient|None=None) -> None:
        self.lastCoord = GPS_PositionData()
        self.x = 0
        self.NumOld = 0
        self.startupTimestamp = 0
        self.gps_time_ok = False
        self.gps_pos_ok = False
        self.oem = oem()

        self.nats=nats

    def setConfig(self, staticThreshold, measRate):
        # Set static threshold
        gps_SetStaticThreshold = utils.wrap_function(libGps, "GPS_SetStaticThreshold", c_int, [c_char])
        res = gps_SetStaticThreshold(c_char(staticThreshold))
        if res != 0:
            log.error("Error " + str(res) + " in GPS_SetStaticThreshold()")
            return res

        # Set measurement rate
        gps_SetMeasurementRate = utils.wrap_function(libGps, "GPS_SetMeasurementRate", c_int, [c_char])
        res = gps_SetMeasurementRate(c_char(measRate))
        if res != 0:
            log.error("Error " + str(res) + " in GPS_SetMeasurementRate()")
            return res

    def setNormalConfig(self):
        return self.setConfig(15, 1)

    def setActiveConfig(self):
        return self.setConfig(0, 4)

    def getUTCDateTime(self):
        utcStruct = UTC_DateTime()
        gps_GetUTCDateTime = utils.wrap_function(libGps, "GPS_GetUTCDateTime", c_int, [POINTER(UTC_DateTime)])
        res = gps_GetUTCDateTime( byref(utcStruct) )
        if res != 0:
            self.gps_time_ok = False
            dt = None
            log.error("Error " + str(res) + " in getUTCDateTime()")
        else:
            log.debug("GPS time struct = %s (res=%s)", str(utcStruct), str(res))
            if(utcStruct.Year!=0 and utcStruct.Month!=0 and utcStruct.Day!=0):
                (ms, sec)=modf(utcStruct.Seconds)
                dt = datetime(utcStruct.Year, utcStruct.Month, utcStruct.Day, utcStruct.Hours, utcStruct.Minutes, second=int(sec), microsecond=int(ms*100), tzinfo=timezone.utc )
            else:
                self.gps_time_ok = False
                dt=None
                res=1

        if isinstance(dt, datetime) :
            log.debug("GPS UTC datetime is : " + str(dt) )
            log.debug("GPS UTC timestamp is : " + str(int(datetime.timestamp(dt))) )

        return (dt, res)

    def updateStartupTimestamp(self):
        (dt,res) = self.getUTCDateTime()
        if res != 0:
            log.error("Error " + str(res) + " in GPS_GetUTCDateTime()")
        else:
            self.startupTimestamp = int(datetime.timestamp(dt))
            self.gps_time_ok = True
            log.debug("GPS UTC startup timestamp is :" + str(self.startupTimestamp) )
        return res

    # def getGPSStatus(self):
        # int GPS_IsActive (int *wActive)
        # int 	GPS_GetVersion (unsigned char *wVersion)
        # int 	GPS_GetStatusAntenna (tANTENNA_NEW_STATUS *pStatus)
        # int 	GPS_GetSV_inView (tGSV_Data *pData)
        # int 	GPS_Get_Software_Version (char *pData)
        # int 	GPS_GetFixConfig (short int *pMask, unsigned int *pHAccu)
        # int 	GPS_GetStatusJamming (char *pStatus)
        # int 	GPS_Get_Model (char *pBuffer)
        # int GPS_GetDOP_FixMode ( tGNSS_DOP_SV * pDOP_SV )



    def GPS_Get_Model(self):
        __GPS_Get_Model = utils.wrap_function(libGps, "GPS_Get_Model", c_int, [POINTER(c_char)])
        buffer = create_string_buffer(20)
        res = oe( __GPS_Get_Model( buffer ) )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res, str(buffer.value)

    def GPS_GetSV_inView (self):
        __GPS_GetSV_inView = utils.wrap_function(libGps, "GPS_GetSV_inView", c_int, [POINTER(GSV_Data)])
        gsv_data = GSV_Data()
        res = oe( __GPS_GetSV_inView( byref(gsv_data) ) )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res, gsv_data

    def __repr__(self):
        positionString ="GPS infos :\n"
        positionString += ("CYCLES({})PosValid({})OLD POS({})TOTAL({}),NAV STATUS({})\n".format(
            self.x, self.lastCoord.PosValid, self.lastCoord.OldValue, self.NumOld, self.lastCoord.NavStatus) )
        positionString +=("LATITUDE  --> {} deg {} min {} sec {} ({})\n".format(
                self.lastCoord.Latitude.Degrees, self.lastCoord.Latitude.Minutes,
                self.lastCoord.Latitude.Seconds, self.lastCoord.Latitude.Dir, self.lastCoord.LatDecimal) )
        positionString +=("LONGITUDE  --> {} deg {} min {} sec {} ({})\n".format(
                self.lastCoord.Longitude.Degrees, self.lastCoord.Longitude.Minutes,
                self.lastCoord.Longitude.Seconds, self.lastCoord.Longitude.Dir, self.lastCoord.LonDecimal) )
        positionString +=("ALTITUDE {}, hAcc {}, vAcc {}, speed {}, course {}\n".format(
                self.lastCoord.Altitude, self.lastCoord.HorizAccu, self.lastCoord.VertiAccu, self.lastCoord.Speed, self.lastCoord.Course) )
        positionString +=("HDOP({}),VDOP({}), TDOP({}), numSvs({})".format(
                self.lastCoord.HDOP, self.lastCoord.VDOP,.
