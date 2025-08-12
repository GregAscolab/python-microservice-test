import logging #as log
from ctypes import *
from typing import Tuple
import common.utils as utils
from common.owa_errors import OwaErrors as oe, OwaErrorMgt as oem

libRtu=cdll.LoadLibrary("libRTU_Module.so")


######## Logger config ##########
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

streamLog = logging.StreamHandler()
streamLog.setFormatter(formatter)
log.addHandler(streamLog)

logFile = logging.FileHandler(__name__ + '.log')
logFile.setFormatter(formatter)
log.addHandler(logFile)

############## C Structures ################




###########################################
class Rtu():
    ''' Main RTU class wrapper '''

    def __init__(self) -> None:
        log.debug("Init RTU name=" + __name__)
        self.oem = oem()

    def initialize(self) -> int:
        res = oe( libRtu.RTUControl_Initialize() )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res

    def start(self) -> int:
        res = oe( libRtu.RTUControl_Start() )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res

    def finalize(self) -> int:
        res = oe( libRtu.RTUControl_Finalize() )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res

    def is_active(self) -> Tuple[int, bool]:
        __RTU_IsActive = utils.wrap_function(libRtu, "RTUControl_IsActive", c_int, [POINTER(c_int)])
        state = c_int()
        res = oe( __RTU_IsActive(byref(state)) )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res, bool(state.value)

    def getVin(self) -> Tuple[int, float]:
        _RTU_GetAD_V_IN = utils.wrap_function(libRtu, "RTUGetAD_V_IN", c_int, [POINTER(c_float)])
        # Get the Voltage of main external power input
        f = c_float()
        res = oe( _RTU_GetAD_V_IN(byref(f)) )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res, float(f.value)

    def getVbat(self) -> Tuple[int, float]:
        _RTU_GetAD_VBAT_MAIN = utils.wrap_function(libRtu, "RTUGetAD_VBAT_MAIN", c_int, [POINTER(c_float)])
        f = c_float()
        res = oe( _RTU_GetAD_VBAT_MAIN(byref(f)) )
        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res, float(f.value)

    def getBatteryState(self):
        _RTU_GetBatteryState = utils.wrap_function(libRtu, "RTUGetBatteryState", c_int, [POINTER(c_ubyte)])
        '''Battery state = 0: Precharge in progress 1: Charge done 2: Fast charge in progress 3: Charge suspended'''
        res = c_int()
        state = c_ubyte()
        res = oe( _RTU_GetBatteryState(byref(state)) )

        if res != oe.NO_ERROR:
            error_msg = f"Error {res.name} ({res.value}) in {self.__class__.__name__}.{utils.current_method_name()}"
            self.oem.error_action(error_msg)
        return res, int(state.value)
