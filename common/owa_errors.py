from enum import IntEnum
import logging #as log


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

###############################################################

class OwaErrors(IntEnum):
    NO_ERROR                                   = 0
    ERROR_NOT_IMPLEMENTED                      = 1
    ERROR_IN_PARAMETERS                        = 2
    #************    RTU Section
    RTUCONTROL_ERROR_BASE                      = 3
    ERROR_OPENING_PORT                         = RTUCONTROL_ERROR_BASE + 0
    ERROR_CLOSING_PORT                         = RTUCONTROL_ERROR_BASE + 1
    ERROR_CREATING_NODE                        = RTUCONTROL_ERROR_BASE + 2
    ERROR_UNDEFINED_NODE_STATUS                = RTUCONTROL_ERROR_BASE + 3
    ERROR_INVALID_NODE                         = RTUCONTROL_ERROR_BASE + 4
    ERROR_PORT_ALREADY_JOINED                  = RTUCONTROL_ERROR_BASE + 5
    ERROR_INSERTING_NODE                       = RTUCONTROL_ERROR_BASE + 6
    ERROR_PORT_NOT_JOINED                      = RTUCONTROL_ERROR_BASE + 7
    ERROR_PORT_NOT_YET_CLOSED                  = RTUCONTROL_ERROR_BASE + 8
    ERROR_RTUCONTROL_RESERVED                  = RTUCONTROL_ERROR_BASE + 9
    ERROR_SELECT_ALREADY_RUNNING               = RTUCONTROL_ERROR_BASE + 10
    ERROR_SELECT_NOT_RUNNING                   = RTUCONTROL_ERROR_BASE + 11
    ERROR_SELECT_LOOP_THREAD_CREATING          = RTUCONTROL_ERROR_BASE + 12
    ERROR_SELECT_CLOSING_TIMEOUT               = RTUCONTROL_ERROR_BASE + 13
    ERROR_SELECT_LOOP_THREAD_CLOSING           = RTUCONTROL_ERROR_BASE + 14
    ERROR_PORT_NOT_OPEN                        = RTUCONTROL_ERROR_BASE + 15
    ERROR_INVALID_FILE_DESCRIPTOR              = RTUCONTROL_ERROR_BASE + 16
    ERROR_INSUFICIENT_MEMORY                   = RTUCONTROL_ERROR_BASE + 17
    ERROR_LAST_FREE_SIGNAL                     = RTUCONTROL_ERROR_BASE + 18
    ERROR_NO_FREE_SIGNALS_AVAILABLE            = RTUCONTROL_ERROR_BASE + 19
    ERROR_RTUCONTROL_ALREADY_INITALIZED        = RTUCONTROL_ERROR_BASE + 20
    ERROR_RTUCONTROL_NOT_INITALIZED            = RTUCONTROL_ERROR_BASE + 21
    ERROR_RTUCONTROL_ALREADY_STARTED           = RTUCONTROL_ERROR_BASE + 22
    ERROR_RTUCONTROL_NOT_STARTED               = RTUCONTROL_ERROR_BASE + 23
    ERROR_OWA22XM_DRIVER_OPENING               = RTUCONTROL_ERROR_BASE + 24
    ERROR_OWA22XM_DRIVER_CLOSING               = RTUCONTROL_ERROR_BASE + 25
    ERROR_OWA22XM_DRIVER_ALREADY_OPENED        = RTUCONTROL_ERROR_BASE + 26
    ERROR_OWA22XM_DRIVER_NOT_OPENED            = RTUCONTROL_ERROR_BASE + 27
    ERROR_IN_COMMAND_CALL                      = RTUCONTROL_ERROR_BASE + 28
    ERROR_PARTITION_NAME                       = RTUCONTROL_ERROR_BASE + 29
    ERROR_FILE_NAME                            = RTUCONTROL_ERROR_BASE + 30
    ERROR_BOOT_HEADER                          = RTUCONTROL_ERROR_BASE + 31
    ERROR_OPENING_RTU_DRIVER                   = RTUCONTROL_ERROR_BASE + 32
    ERROR_CLOSING_RTU_DRIVER                   = RTUCONTROL_ERROR_BASE + 33
    ERROR_CALLING_RTU_DRIVER                   = RTUCONTROL_ERROR_BASE + 34
    ERROR_USECSLEEP_NOT_EXECUTED               = RTUCONTROL_ERROR_BASE + 35
    ERROR_OWA3X_FD_DRIVER_OPENING              = RTUCONTROL_ERROR_BASE + 36
    ERROR_OWA3X_FD_DRIVER_CLOSING              = RTUCONTROL_ERROR_BASE + 37
    ERROR_OWA3X_FD_DRIVER_ALREADY_OPENED       = RTUCONTROL_ERROR_BASE + 38
    ERROR_OWA3X_FD_DRIVER_NOT_OPENED           = RTUCONTROL_ERROR_BASE + 39
    ERROR_POWER_MANAGEMENT_NOT_WORKING         = RTUCONTROL_ERROR_BASE + 40
    ERROR_POWER_MANAGEMENT_NOT_ANSWER          = RTUCONTROL_ERROR_BASE + 41
    ERROR_OWA3X_PM_DRIVER_NOT_OPENED           = RTUCONTROL_ERROR_BASE + 42
    ERROR_OWA3X_DIGITAL_INPUT                  = RTUCONTROL_ERROR_BASE + 43
    ERROR_OWA3X_DIGITAL_OUTPUT                 = RTUCONTROL_ERROR_BASE + 44
    ERROR_OWA3X_CFG_INPUT_INT                  = RTUCONTROL_ERROR_BASE + 45
    ERROR_OWA3X_BAD_INPUT_NUM                  = RTUCONTROL_ERROR_BASE + 46
    ERROR_OWA3X_BAD_OUTPUT_NUM                 = RTUCONTROL_ERROR_BASE + 47
    ERROR_OWA3X_ALREADY_CFG                    = RTUCONTROL_ERROR_BASE + 48
    ERROR_OWA3X_INT_NOT_ENABLED                = RTUCONTROL_ERROR_BASE + 49
    ERROR_OWA3X_BAD_PD_SELECT                  = RTUCONTROL_ERROR_BASE + 50
    ERROR_OWA3X_BAD_OUTPUT_VAL                 = RTUCONTROL_ERROR_BASE + 51
    ERROR_EXPANSION_BOARD_NOT_WORKING          = RTUCONTROL_ERROR_BASE + 52
    ERROR_EXPANSION_BOARD_NOT_ANSWER           = RTUCONTROL_ERROR_BASE + 53
    ERROR_IBUTTON_NOT_DETECTED                 = RTUCONTROL_ERROR_BASE + 54
    ERROR_UMOUNT_CMD                           = RTUCONTROL_ERROR_BASE + 55
    ERROR_MOUNT_CMD                            = RTUCONTROL_ERROR_BASE + 56
    ERROR_NOT_USED                             = RTUCONTROL_ERROR_BASE + 57
    ERROR_OWA3X_ACCEL_NOT_READY                = RTUCONTROL_ERROR_BASE + 58
    ERROR_ACCEL_ALREADY_STARTED                = RTUCONTROL_ERROR_BASE + 59
    ERROR_PM_ANSWER                            = RTUCONTROL_ERROR_BASE + 60
    ERROR_ENTER_STANDBY                        = RTUCONTROL_ERROR_BASE + 61
    #************    IOs Section
    IOS_ERROR_BASE                             = 100
    ERROR_INVALID_OUTPUT_TYPE                  = IOS_ERROR_BASE + 1
    ERROR_INVALID_CALIBRATION_TYPE             = IOS_ERROR_BASE + 2
    ERROR_INVALID_END_ADVICE_TYPE              = IOS_ERROR_BASE + 3
    ERROR_INVALID_USAGE_TYPE                   = IOS_ERROR_BASE + 4
    ERROR_INVALID_PWM_DUTY_CYCLE               = IOS_ERROR_BASE + 5
    ERROR_INVALID_PWM_SOURCE_FREQ              = IOS_ERROR_BASE + 6
    ERROR_INVALID_PWM_CYCLE_TYPE               = IOS_ERROR_BASE + 7
    ERROR_OPENING_DEVICE_DRIVER                = IOS_ERROR_BASE + 8
    ERROR_CLOSING_DEVICE_DRIVER                = IOS_ERROR_BASE + 9
    ERROR_IN_IOCTL_COMMAND                     = IOS_ERROR_BASE + 10
    ERROR_TIMER_ALREADY_USED                   = IOS_ERROR_BASE + 11
    ERROR_TIMER_NOT_USED                       = IOS_ERROR_BASE + 12
    ERROR_NO_FREE_TIMERS                       = IOS_ERROR_BASE + 13
    ERROR_IOS_ALREADY_INITIALIZED              = IOS_ERROR_BASE + 14
    ERROR_IOS_NOT_INITIALIZED                  = IOS_ERROR_BASE + 15
    ERROR_IOS_ALREADY_STARTED                  = IOS_ERROR_BASE + 16
    ERROR_IOS_NOT_STARTED                      = IOS_ERROR_BASE + 17
    ERROR_READ_ANALOG_INPUT                    = IOS_ERROR_BASE + 18
    ERROR_IBUTTON_SEARCHING                    = IOS_ERROR_BASE + 19
    ERROR_OW_DISCOVERING                       = IOS_ERROR_BASE + 20
    ERROR_OW_TOO_MANY_DEVICES                  = IOS_ERROR_BASE + 21
    ERROR_IB_DATA_SIZE                         = IOS_ERROR_BASE + 22
    ERROR_IB_READ_DATA                         = IOS_ERROR_BASE + 23
    ERROR_PPS_IN_USE                           = IOS_ERROR_BASE + 24
    #************    GSM Section
    GSM_ERROR_BASE                             = 200
    GSM_ERR_ME_FAILURE                         = GSM_ERROR_BASE + 0
    GSM_ERR_CONNECTION_FAILURE                 = GSM_ERROR_BASE + 1
    GSM_ERR_ME_PHONE_ADAPTOR_LINK_RESERVED     = GSM_ERROR_BASE + 2
    GSM_ERR_OPERATION_NOT_ALLOWED              = GSM_ERROR_BASE + 3
    GSM_ERR_OPERATION_NOT_SUPPORTED            = GSM_ERROR_BASE + 4
    GSM_ERR_PH_SIM_PIN_REQUIRED                = GSM_ERROR_BASE + 5
    GSM_ERR_SIM_NOT_INSERTED                   = GSM_ERROR_BASE + 6
    GSM_ERR_SIM_PIN_REQUIRED                   = GSM_ERROR_BASE + 7
    GSM_ERR_SIM_PUK_REQUIRED                   = GSM_ERROR_BASE + 8
    GSM_ERR_SIM_FAILURE                        = GSM_ERROR_BASE + 9
    GSM_ERR_SIM_BUSY                           = GSM_ERROR_BASE + 10
    GSM_ERR_SIM_WRONG                          = GSM_ERROR_BASE + 11
    GSM_ERR_INCORRECT_PASSWORD                 = GSM_ERROR_BASE + 12
    GSM_ERR_SIM_PIN2_REQUIRED                  = GSM_ERROR_BASE + 13
    GSM_ERR_SIM_PUK2_REQUIRED                  = GSM_ERROR_BASE + 14
    GSM_ERR_MEMORY_FULL                        = GSM_ERROR_BASE + 15
    GSM_ERR_INVALID_INDEX                      = GSM_ERROR_BASE + 16
    GSM_ERR_NOT_FOUND                          = GSM_ERROR_BASE + 17
    GSM_ERR_MEMORY_FAILURE                     = GSM_ERROR_BASE + 18
    GSM_ERR_TEXT_STRING_TOO_LONG               = GSM_ERROR_BASE + 19
    GSM_ERR_INVALID_CHARACTERS_IN_TEXT_STRING  = GSM_ERROR_BASE + 20
    GSM_ERR_DIAL_STRING_TOO_LONG               = GSM_ERROR_BASE + 21
    GSM_ERR_INVALID_CHARACTERS_IN_DIAL_STRING  = GSM_ERROR_BASE + 22
    GSM_ERR_NO_NETWORK_SERVICE                 = GSM_ERROR_BASE + 23
    GSM_ERR_NETWORK_TIMEOUT                    = GSM_ERROR_BASE + 24
    GSM_ERR_UNKNOWN                            = GSM_ERROR_BASE + 25
    # SMS FAILURES
    GSM_ERR_SMS_ME_FAILURE                     = GSM_ERROR_BASE + 26
    GSM_ERR_SMS_SERVICE_OF_ME_RESERVED         = GSM_ERROR_BASE + 27
    GSM_ERR_SMS_OPERATION_NOT_ALLOWED          = GSM_ERROR_BASE + 28
    GSM_ERR_SMS_OPERATION_NOT_SUPPORTED        = GSM_ERROR_BASE + 29
    GSM_ERR_SMS_INVALID_PDU_MODE_PARAMETER     = GSM_ERROR_BASE + 30
    GSM_ERR_SMS_SMSC_ADDRESS_UNKNOWN           = GSM_ERROR_BASE + 31
    GSM_ERR_SMS_NO_CNMA_ACK_EXPECTED           = GSM_ERROR_BASE + 32
    GSM_ERR_SMS_UNKNOWN                        = GSM_ERROR_BASE + 33
    GSM_ERR_BUSY                               = GSM_ERROR_BASE + 34
    GSM_ERR_NO_ANSWER                          = GSM_ERROR_BASE + 35
    GSM_ERR_NO_CARRIER                         = GSM_ERROR_BASE + 36
    GSM_ERR_DIALING                            = GSM_ERROR_BASE + 37
    GSM_ERR_INIT_FAILURE                       = GSM_ERROR_BASE + 38
    GSM_ERR_TIMEOUT                            = GSM_ERROR_BASE + 39
    GSM_ERR_DATA_MODE                          = GSM_ERROR_BASE + 40
    GSM_ERR_GENERAL_FAILURE                    = GSM_ERROR_BASE + 41
    GSM_ERR_INIT_IN_PROGRESS                   = GSM_ERROR_BASE + 42
    GSM_ERR_IN_GPRS_PARAM                      = GSM_ERROR_BASE + 43
    GSM_ERR_ALREADY_INITIALIZED                = GSM_ERROR_BASE + 44
    GSM_ERR_NOT_INITIALIZED                    = GSM_ERROR_BASE + 45
    GSM_ERR_ALREADY_STARTED                    = GSM_ERROR_BASE + 46
    GSM_ERR_NOT_STARTED                        = GSM_ERROR_BASE + 47
    GSM_ERR_INVALID_DATA                       = GSM_ERROR_BASE + 48
    GSM_ERR_NETWORK_LOCK                       = GSM_ERROR_BASE + 49
    GSM_ERR_SMS_TYPE                           = GSM_ERROR_BASE + 50
    GSM_ERR_AUDIO_PARAMETER                    = GSM_ERROR_BASE + 51
    GSM_ERR_NOT_SWITCHED_ON                    = GSM_ERROR_BASE + 52
    GSM_ERR_PLMN_SELECT_FAILURE                = GSM_ERROR_BASE + 53
    GSM_ERR_NO_DIALTONE                        = GSM_ERROR_BASE + 54
    GSM_ERR_OPEN_AUDIO                         = GSM_ERROR_BASE + 55
    GSM_ERR_AUDIO_ALLOC_HW                     = GSM_ERROR_BASE + 56
    GSM_ERR_AUDIO_INIT_HW                      = GSM_ERROR_BASE + 57
    GSM_ERR_AUDIO_SET_ACTYPE                   = GSM_ERROR_BASE + 58
    GSM_ERR_AUDIO_SAMP_FORM                    = GSM_ERROR_BASE + 59
    GSM_ERR_AUDIO_SAMP_RATE                    = GSM_ERROR_BASE + 60
    GSM_ERR_AUDIO_CHAN_COUNT                   = GSM_ERROR_BASE + 61
    GSM_ERR_AUDIO_SET_PARAMS                   = GSM_ERROR_BASE + 62
    GSM_ERR_AUDIO_PCM_PREPARE                  = GSM_ERROR_BASE + 63
    GSM_ERR_AUDIO_PCM_LINK                     = GSM_ERROR_BASE + 64
    GSM_ERR_AUDIO_NOT_ALLOWED                  = GSM_ERROR_BASE + 65
    GSM_ERR_PS_BUSY                            = GSM_ERROR_BASE + 66
    GSM_ERR_SMS_SIM_NOT_READY                  = GSM_ERROR_BASE + 67
    GSM_ERR_AUDIO_ALREADY_OPENED               = GSM_ERROR_BASE + 68
    GSM_ERR_REJECTED_BUSY                      = GSM_ERROR_BASE + 69
    GSM_ERR_NOT_TIME_AVAILABLE                 = GSM_ERROR_BASE + 70
    GSM_ERR_NO_LCP_TIME                        = GSM_ERROR_BASE + 71
    GSM_ERR_NO_IP_TIME                         = GSM_ERROR_BASE + 72
    GSM_ERR_LINK_CREATE                        = GSM_ERROR_BASE + 73
    GSM_ERR_TEMP_NOT_ALLOWED                   = GSM_ERROR_BASE + 74
    GSM_ERR_NO_COVERAGE                        = GSM_ERROR_BASE + 75
    GSM_ERR_MODEL_UNKNOWN                      = GSM_ERROR_BASE + 76
    GSM_ERR_SDM_DISABLED                       = GSM_ERROR_BASE + 77
    GSM_ERR_DEVICE_DETECTION                   = GSM_ERROR_BASE + 78
    #..
    #Reserved ranges for GSM_ERR:             =         GSM_ERROR_BASE + 100

    #************    GPS Section
    GPS_ERROR_BASE                             = 400
    ERROR_IN_GPS_TYPE                          = GPS_ERROR_BASE + 1
    ERROR_NO_VALID_BAUDRATE                    = GPS_ERROR_BASE + 2
    ERROR_NO_VALID_PARITY                      = GPS_ERROR_BASE + 3
    ERROR_NO_VALID_BYTE_LENGTH                 = GPS_ERROR_BASE + 4
    ERROR_NO_VALID_STOPBITS                    = GPS_ERROR_BASE + 5
    ERROR_NO_VALID_PROTOCOL                    = GPS_ERROR_BASE + 6
    ERROR_PROTOCOL_NOT_IMPLEMENTED             = GPS_ERROR_BASE + 7
    ERROR_NO_VALID_PORT                        = GPS_ERROR_BASE + 8
    ERROR_GPS_NOT_STARTED                      = GPS_ERROR_BASE + 9
    ERROR_MSG_NOT_SENT_TO_GPS                  = GPS_ERROR_BASE + 10
    ERROR_NO_DATA_FROM_GPS                     = GPS_ERROR_BASE + 11
    ERROR_GPS_MSG_WITH_BAD_CHK                 = GPS_ERROR_BASE + 12
    ERROR_GPS_PORT_NOT_OPENED                  = GPS_ERROR_BASE + 13
    ERROR_GPS_NOT_POWER_ON                     = GPS_ERROR_BASE + 14
    ERROR_UNLINKPORT_IN_FINALIZE               = GPS_ERROR_BASE + 15
    ERROR_UNLOAD_LIBRARY_IN_FINALIZE           = GPS_ERROR_BASE + 16
    ERROR_MSG_NOT_ALLOWED                      = GPS_ERROR_BASE + 17
    ERROR_GPS_ALREADY_INITIALIZED              = GPS_ERROR_BASE + 18
    ERROR_GPS_NOT_INITIALIZED                  = GPS_ERROR_BASE + 19
    ERROR_GPS_ALREADY_STARTED                  = GPS_ERROR_BASE + 20
    ERROR_GPS_BINARY_TIMEOUT                   = GPS_ERROR_BASE + 21
    ERROR_GPS_BINARY_NACK                      = GPS_ERROR_BASE + 22
    ERROR_FUNCTION_NOT_ALLOWED_IN_NMEA         = GPS_ERROR_BASE + 23
    ERROR_FUNCTION_NOT_ALLOWED_IN_BINARY       = GPS_ERROR_BASE + 24
    ERROR_NO_MEMORY_IN_GPS_FUNCTION            = GPS_ERROR_BASE + 25
    ERROR_FUNCTION_NOT_ALLOWED_ON_GPS          = GPS_ERROR_BASE + 26
    ERROR_GPS_BINARY_TX                        = GPS_ERROR_BASE + 27
    ERROR_GPS_BINARY_WAIT                      = GPS_ERROR_BASE + 28
    ERROR_GPS_BINARY_RX_NACK                   = GPS_ERROR_BASE + 29
    ERROR_GPS_NOT_NEW_MSG                      = GPS_ERROR_BASE + 30
    ERROR_GPS_RX_WAIT                          = GPS_ERROR_BASE + 31
    ERROR_GPS_BIN_CHK                          = GPS_ERROR_BASE + 32
    ERROR_NO_VALID_MEAS_RATE                   = GPS_ERROR_BASE + 33
    #****************** TEST_ORION Section

    TEST_ERROR_BASE                            = 500
    ERROR_TEST_IO                              = TEST_ERROR_BASE + 1
    ERROR_TEST_RTU                             = TEST_ERROR_BASE + 2
    ERROR_TEST_GSM                             = TEST_ERROR_BASE + 3
    ERROR_TEST_UART                            = TEST_ERROR_BASE + 4
    ERROR_TEST_LED                             = TEST_ERROR_BASE + 5

    #***************** INET ERROR Section

    INET_ERROR_BASE                            = 600
    ERROR_INET_ALREADY_RUNNING                 = INET_ERROR_BASE + 0
    ERROR_INET_NOT_INITIALIZED                 = INET_ERROR_BASE + 1
    ERROR_INET_NOT_STARTED                     = INET_ERROR_BASE + 2
    ERROR_INET_IP_IF_NOT_READY                 = INET_ERROR_BASE + 3
    ERROR_INET_IP_NOT_AVAILABLE                = INET_ERROR_BASE + 4
    ERROR_INET_GSM_ON_VOICE                    = INET_ERROR_BASE + 5
    ERROR_INET_GSM_ON_CALL                     = INET_ERROR_BASE + 6
    #***************** FMS ERROR Section
    FMS_ERROR_BASE                             = 1500
    ERROR_FMS_ALREADY_INITIALIZED              = FMS_ERROR_BASE + 1
    ERROR_FMS_NOT_INITIALIZED                  = FMS_ERROR_BASE + 2
    ERROR_FMS_ALREADY_STARTED                  = FMS_ERROR_BASE + 3
    ERROR_STARTING_FMS                         = FMS_ERROR_BASE + 4
    ERROR_FMS_CREATE_SOCKET                    = FMS_ERROR_BASE + 5
    ERROR_FMS_CFG_SOCKET                       = FMS_ERROR_BASE + 6
    ERROR_FMS_BIND_SOCKET                      = FMS_ERROR_BASE + 7
    ERROR_FMS_THREAD_INIT                      = FMS_ERROR_BASE + 8
    ERROR_FMS_NOT_STARTED                      = FMS_ERROR_BASE + 9
    ERROR_FMS_LOAD_LIBRARY                     = FMS_ERROR_BASE + 10
    ERROR_FMS_UNLOAD_LIBRARY                   = FMS_ERROR_BASE + 11
    ERROR_FMS_LOAD_FUNCTION                    = FMS_ERROR_BASE + 12
    ERROR_FMS_OPTION_NOT_ENABLED               = FMS_ERROR_BASE + 13
    ERROR_FMS_ENABLE_CAN                       = FMS_ERROR_BASE + 14
    ERROR_FMS_GET_OPTION                       = FMS_ERROR_BASE + 15
    ERROR_FMS_TIRE_NOT_FOUND                   = FMS_ERROR_BASE + 16
    ERROR_FMS_SRV_CONF                         = FMS_ERROR_BASE + 17




class OwaErrorMgt():

    def __init__(self) -> None:
        pass

    def error_action(self, msg):
        log.error(msg)
        # raise Exception(error_msg)

    def check_error(self, res, msg):
        if res != OwaErrors.NO_ERROR:
            if msg :
                error_msg = msg
            else:
                error_msg = ""
                error_msg = "Error " + str(res)

            self.error_action(error_msg)
