import logging #as log
from ctypes import *
from threading import Thread
from queue import Queue
import time
from typing import IO, Tuple
import common.utils as utils
from common.owa_errors import OwaErrors as oe, OwaErrorMgt as oem

libIo=cdll.LoadLibrary("libIOs_Module.so")


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

############## C Structures ################
class input_int_t(Structure):
    _fields_ = [
        ("InputNumber", c_ubyte),
        ("InputValue", c_ubyte),
        ]



@CFUNCTYPE(None, input_int_t)
def callback_din(inputs:input_int_t):
    log.debug("inputs : num=" + str(inputs.InputNumber) + " val=" + str(inputs.InputValue))

    if inputs.InputValue:
        Io.dins = Io.dins | (1 << inputs.InputNumber)
        log.debug("Set Din = " + str(hex(Io.dins)))
    else :
        Io.dins = Io.dins & ~(1 << inputs.InputNumber)
        log.debug("Unset Din = " + str(hex(Io.dins)))

    event = { "ts" : round(time.time(), 3),
              "dins" : Io.dins,
              inputs.InputNumber : inputs.InputValue
            }
    Io.din_it_queue.put_nowait(event)

###########################################
class Io():
    ''' Main IO class wrapper '''
    # TODO: Add Queue counter/limit to avoid full Queue
    # TODO: Use other type of Queue for performance ?
    din_it_queue = Queue()
    dins = 0
    ains = [0] * 4

    def __init__(self) -> None:
        log.debug("init io name=" + __name__)
        self.oem = oem()


    def new_din_it_event(self, num:int, val:int):
        event = { num:val }
        self.din_it_queue.put_nowait(event)


    def initialize(self) -> int:
        res = oe( libIo.IO_Initialize() )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res.value) + " (" +str(res) + ") in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    def start(self) -> int:
        res = oe( libIo.IO_Start() )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    def finalize(self) -> int:
        res = oe( libIo.IO_Finalize() )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    __IO_IsActive = utils.wrap_function(libIo, "IO_IsActive", c_int, [POINTER(c_int)])
    def is_active(self) -> Tuple[int, bool]:
        state = c_int()
        res = oe( self.__IO_IsActive(byref(state)) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res, bool(state.value)


    __DIGIO_Switch_GPS_ON_OFF = utils.wrap_function(libIo, "DIGIO_Switch_GPS_ON_OFF", c_int, [c_ubyte])
    def switch_gps_on_off(self, cde:int) -> int:
        command = c_ubyte(cde)
        res = oe( self.__DIGIO_Switch_GPS_ON_OFF(command) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    __DIGIO_Set_PPS_GPS_Input = utils.wrap_function(libIo, "DIGIO_Set_PPS_GPS_Input", c_int, [])
    def set_pps_gps_input(self):
        res = oe( self.__DIGIO_Set_PPS_GPS_Input() )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    __DIGIO_Enable_Can = utils.wrap_function(libIo, "DIGIO_Enable_Can", c_int, [c_char])
    def enable_can(self) -> int:
        res = oe( self.__DIGIO_Enable_Can( c_char(1) ) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    __DIGIO_Get_DIN = utils.wrap_function(libIo, "DIGIO_Get_DIN", c_int, [c_int, POINTER(c_int)])
    def get_din(self, dinNum:int)->Tuple[int, int]:
        res = c_int()
        din = c_int()
        dinNumber = c_int(dinNum)
        res = oe( self.__DIGIO_Get_DIN(dinNumber, byref(din)) )

        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)

        log.debug("DIN" + str(dinNum) + " : " + str(din.value) )

        return res, int(din.value)

    __DIGIO_Get_All_DIN = utils.wrap_function(libIo, "DIGIO_Get_All_DIN", c_int, [POINTER(c_ushort)])
    def get_all_din(self) -> Tuple[int, int]:
        dins = c_ushort()
        res = oe( self.__DIGIO_Get_All_DIN(byref(dins)) )

        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)

        log.debug("DINs : " + str(dins.value) )

        self.dins = dins.value
        return res, dins.value


    __DIGIO_Set_ADC_RANGE = utils.wrap_function(libIo, "DIGIO_Set_ADC_RANGE", c_int, [c_ubyte, c_ubyte])
    def set_adc_range(self, input_num:int, range_enum:int) -> int:
        '''
        Set any of the possible analog voltage ranges to the analog inputs, which are read with function ANAGIO_GetAnalogIn()

        Parameters
        ----------
        input_num	Analog input. 0 -> AD0, 1 -> AD1, 2 -> AD2, 3 -> AD3
        range_enum	Range. 0 -> 0V to 5.12V, 1 -> 0V to 30.72V (default range: 0 to 5.12V)

        Returns
        -------
        NO_ERROR if success. Specific error number if fails.
        '''
        res = oe( self.__DIGIO_Set_ADC_RANGE(c_ubyte(input_num), c_ubyte(range_enum)) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res


    __ANAGIO_GetAnalogIn = utils.wrap_function(libIo, "ANAGIO_GetAnalogIn", c_int, [c_int, POINTER(c_int)])
    def get_ain(self, ainNum:int)->Tuple[int, int]:
        res = c_int()
        ain = c_int()
        ainNumber = c_int(ainNum)
        res = oe( self.__ANAGIO_GetAnalogIn(ainNumber, byref(ain)) )

        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)

        log.debug("AIN" + str(ainNum) + " : " + str(ain.value) )

        self.ains[ainNum] = ain.value
        return res, ain.value


    __DIGIO_ConfigureInterruptService = utils.wrap_function(libIo, "DIGIO_ConfigureInterruptService", c_int, [c_ubyte, c_ubyte, CFUNCTYPE(None, input_int_t), c_ushort])
    def configure_interrupt_service(self, input:int, edge:int, handler:CFUNCTYPE=callback_din, num_ints:int=1) -> int:
        ''' Set interruption callback and behavior.

        Parameters
        ----------
        input = Inputs that can interrupt are DIGITAL_INPUT_[0..9] and PWR_FAIL
        edge = Edge to interrupt: 0 for falling edge, 1 for rising edge, 2 for both
        handler = 	Function handler that will be executed on each interruption (CFUNCTYPE)
        num_ints = number of interruption to be raised before handler is call. Eg. :
            1 = Handler is call at every interrupt
            5 = Handler is calls each 5 interrupts
            ...

        Returns
        -------
        NO_ERROR if success. Specific error number if fails.

        Warning
        -------
        for changing interrupt configuration, first remove the interrupt service and then configure the interrupt service again.
        '''
        res = oe( self.__DIGIO_ConfigureInterruptService(c_ubyte(input), c_ubyte(edge), handler, c_ushort(num_ints)) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)

        return res

    __DIGIO_RemoveInterruptService = utils.wrap_function(libIo, "DIGIO_RemoveInterruptService", c_int, [c_ubyte])
    def remove_interrupt_service(self, input:int) -> int:
        res = oe( self.__DIGIO_RemoveInterruptService(c_ubyte(input)) )
        if res != oe.NO_ERROR:
            if res == oe.ERROR_OWA3X_INT_NOT_ENABLED:
                log.info(f"Interrupt on DIN {input} not yet enable (" + self.__class__.__name__ + "." + utils.current_method_name() + ")" )
            else:
                error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
                self.oem.error_action(error_msg)

        return res

    __DIGIO_GetNumberOfInterrupts = utils.wrap_function(libIo, "DIGIO_GetNumberOfInterrupts", c_int, [c_ubyte, POINTER(c_ulong)])
    def get_number_of_interrupts(self, input_num:int) -> Tuple[int, int]:
        val = c_ulong()
        res = oe( self.__DIGIO_GetNumberOfInterrupts(c_ubyte(input_num), byref(val)) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)

        return res, int(val.value)


    __DIGIO_Set_DOUT = utils.wrap_function(libIo, "DIGIO_Set_DOUT", c_int, [c_ubyte, c_ubyte])
    def set_dout(self, output_num:int, value:bool) -> int:
        res = oe( self.__DIGIO_Set_DOUT(c_ubyte(output_num), c_ubyte(value)) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res

    __DIGIO_Get_PWR_FAIL = utils.wrap_function(libIo, "DIGIO_Get_PWR_FAIL", c_int, [POINTER(c_ubyte)])
    def get_power_fail(self) -> Tuple[int, int]:
        isPwrFail= c_ubyte()
        res = oe( self.__DIGIO_Get_PWR_FAIL(byref(isPwrFail)) )
        if res != oe.NO_ERROR:
            error_msg = "Error " + str(res) + " in " + self.__class__.__name__ + "." + utils.current_method_name()
            self.oem.error_action(error_msg)
        return res, int(isPwrFail.value)


if __name__ == "__main__":

    running = True

    io = Io()
    io.initialize()
    res, val = io.is_active()

    # Configure interrupt callback
    io.configure_interrupt_service(1, 2)
    io.configure_interrupt_service(2, 2)

    # Configure AIN ADC
    io.set_adc_range(0,0)

    while running:
        # Get all dins
        res, dins = io.get_all_din()
        res, ains = io.get_ain(1)


    res= nb_int = io.get_number_of_interrupts(1)
    print("Nb Int =" + str(nb_int))

    io.remove_interrupt_service(2)


    io.finalize()
    io.is_active()
