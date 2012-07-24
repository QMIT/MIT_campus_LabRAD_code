import atexit
import ctypes
from ctypes import (byref, c_double, c_int, c_uint, c_char_p, c_ushort, )

import numpy as np

aqdrv = ctypes.windll.LoadLibrary('AqDrv4')

BUF_SIZE = 1024

ACQIRIS_ERROR_ACQ_TIMEOUT = 0xBFFA4900L
ACQIRIS_ERROR_PROC_TIMEOUT = 0xBFFA4902L

class AcqirisException(Exception):
    """Encapsulates an error returned by a call to an Acqiris driver function"""
    def __new__(cls, instrumentID, errorCode):
        if errorCode < 0:
            errorCode += 2**32
        if errorCode in [ACQIRIS_ERROR_ACQ_TIMEOUT,
                         ACQIRIS_ERROR_PROC_TIMEOUT]:
            cls = TimeoutException
        return Exception.__new__(cls, instrumentID, errorCode)
    
    def __init__(self, instrumentID, errorCode):
        self.instrumentID = instrumentID
        if errorCode < 0:
            errorCode += 2**32
        self.errorCode = errorCode
        message = ctypes.create_string_buffer(BUF_SIZE)
        aqdrv['Acqrs_errorMessage'](c_uint(instrumentID), c_int(errorCode), message, ctypes.sizeof(message))
        Exception.__init__(self, message.value)
        
    def __str__(self):
        return '%s(inst=%d, error=%08X): %s' % (self.__class__.__name__,
                                                self.instrumentID, self.errorCode, self.message)
        
class TimeoutException(AcqirisException):
    """Special case of timeout errors, since we may want to trap these and retry"""
    

def _call(fn, args, prefix='Acqrs'):
    result = aqdrv['%s_%s' % (prefix, fn)](*args)
    if result:
        if len(args) and isinstance(args[0], c_uint):
            instrumentID = args[0].value
        else:
            instrumentID = 0
        raise AcqirisException(instrumentID, result)

def call(fn, *args):
    return _call(fn, args, prefix='Acqrs')

def call_D1(fn, *args):
    return _call(fn, args, prefix='AcqrsD1')

class AqReadParameters(ctypes.Structure):
    _fields_ = [('dataType', c_int),
                ('readMode', c_int),
                ('firstSegment', c_int),
                ('nbrSegments', c_int),
                ('firstSampleInSeg', c_int),
                ('nbrSamplesInSeg', c_int),
                ('segmentOffset', c_int),
                ('dataArraySize', c_int),
                ('segDescArraySize', c_int),
                ('flags', c_int),
                ('reserved', c_int),
                ('reserved2', c_double),
                ('reserved3', c_double)]

class AqDataDescriptor(ctypes.Structure):
    _fields_ = [('returnedSamplesPerSeg', c_int),
                ('indexFirstPoint', c_int),
                ('sampTime', c_double),
                ('vGain', c_double),
                ('vOffset', c_double),
                ('returnedSegments', c_int),
                ('nbrAvgWforms', c_int),
                ('actualTriggersInAcqLo', c_uint),
                ('actualTriggersInAcqHi', c_uint),
                ('actualDataSize', c_uint),
                ('reserved2', c_int),
                ('reserved3', c_double)]

class AqSegmentDescriptor(ctypes.Structure):
    _fields_ = [('horPos', c_double),
                ('timeStampLo', c_uint),
                ('timeStampHi', c_uint)]

class AqSegmentDescriptorRaw(ctypes.Structure):
    _fields_ = [('horPos', c_double),
                ('timeStampLo', c_uint),
                ('timeStampHi', c_uint),
                ('indexFirstPoint', c_uint),
                ('actualSegmentSize', c_uint),
                ('reserved', c_int)]

class AqSegmentDescriptorAvg(ctypes.Structure):
    _fields_ = [('horPos', c_double),
                ('timeStampLo', c_uint),
                ('timeStampHi', c_uint),
                ('actualTriggersInSeg', c_uint),
                ('avgOvfl', c_int),
                ('avgStatus', c_int),
                ('avgMax', c_int),
                ('flags', c_uint),
                ('reserved', c_int)]


# AcqirisInterface.h

def calibrate(instrumentID):
    """Performs an autocalibration of the instrument
    
    instrumentID - id of the instrument to calibrate
    """
    call('calibrate', c_uint(instrumentID))

def calibrateEx(instrumentID, calType=0, modifier=0, flags=0):
    """Performs a (partial) autocalibration of the instrument
    
    instrumentID - id of the instrument to calibrate
    calType - 0: calibrate the entire instrument
              1: calibrate only the current channel configuration
              2: calibrate external clock timing
              3: calibrate only at the current frequency
              4: fast calibration for current settings only
    modifier - for calType 0, 1, or 2: unused
               for calType 3 or 4: 0, calibrate all channels
                                   n, calibrate channel 'n' only
    """
    call('calibrateEx', c_uint(instrumentID), c_int(calType), c_int(modifier), c_int(flags))

def calibrateCancel(instrumentID):
    """Interrupts a calibration of the instrument launched from a different thread"""
    call('calibrateCancel', c_uint(instrumentID))

def calLoad(instrumentID, filePathName, flags):
    """Load calibration values from file
    
    instrumentID - id of the instrument to check
    filePathName - a string containing the file path
    flags - 0 = default filename. Calibration values will be loaded
                from the 'snXXXXX_calVal.bin' file in the working
                directory. filePathName MUST be None or '' (empty
                String).
            1 = specify path only. Calibration values will be loaded
                from the 'snXXXXX_calVal.bin' file in the specified
                directory. filePathName MUST be non-NULL.
            2 = specify filename. 'filePathName' represents the
                filename (with or without path) and MUST be
                non-NULL and non-empty.
    """
    call('calLoad', c_uint(instrumentID), c_char_p(filePathName), c_int(flags))

def calRequired(instrumentID, channel):
    """Check if a self-calibration is needed
    
    instrumentID - id of the instrument to check
    channel - id of the channel to check
    """
    isRequired = c_ushort()
    call('calRequired', c_uint(instrumentID), c_uint(channel), byref(isRequired))
    return bool(isRequired.value)

def calSave(instrumentID, filePathName, flags):
    """Save calibration values to file
    
    instrumentID - id of the instrument to check
    filePathName - a string containing the file path
    flags - 0 = default filename. Calibration values will be loaded
                from the 'snXXXXX_calVal.bin' file in the working
                directory. filePathName MUST be NULL or '' (empty
                String).
            1 = specify path only. Calibration values will be loaded
                from the 'snXXXXX_calVal.bin' file in the specified
                directory. 'filePathName' MUST be non-NULL.
            2 = specify filename. 'filePathName' represents the
                filename (with or without path) and MUST be
                non-NULL and non-empty.
    """
    call('calSave', c_uint(instrumentID), c_char_p(filePathName), c_int(flags))

def close(instrumentID):
    """Closes an instrument
    
    instrumentID - id of the instrument to close
    
    Close the specified instrument. Once closed,
    this instrument is not available anymore and
    needs to be reenabled using initWithOptions or init.
    
    For freeing properly all resources, closeAll
    must still be called when the application closes,
    even if close was called for each instrument.
    """
    call('close', c_uint(instrumentID))

def closeAll():
    """Closes all instruments in preparation for closing the application.
    
    This function should be the last call to the driver, before closing
    an application.  If this function is not called, closing the application
    might crash the computer in some situations, particularly in
    multi-threaded applications.
    """
    call('closeAll')

# ensure that all instruments get called before python shuts down
atexit.register(closeAll)

def errorMessage(instrumentID, errorCode):
    """Translates an error code into human-readable form"""
    message = ctypes.create_string_buffer(BUF_SIZE)
    call('errorMessage', c_uint(instrumentID), c_int(errorCode), c_int(BUF_SIZE), message)
    return message.value

def getDevType():
    raise Exception('not implemented')

def getDevTypeByIndex():
    raise Exception('not implemented')

def getInstrumentData(instrumentID):
    """Returns some basic data about a specified instrument.
    
    Returns a tuple of (name, serial number, PCI bus number, PCI slot number)
    """
    name = ctypes.create_string_buffer(BUF_SIZE)
    serial = ctypes.c_int()
    bus = ctypes.c_int()
    slot = ctypes.c_int()
    call('getInstrumentData', instrumentID, name,
                              byref(serial), byref(bus), byref(slot))
    return name.value, serial.value, bus.value, slot.value

def getInstrumentInfo(instrumentID, parameterString, returnType):
    """Returns general information about a specified instrument
    
    Return type must be one of 'int', 'uint', 'double' or 'str',
    indicating the expected return type for the requested parameter.
    """
    if returnType == 'int':
        retVal = c_int()
        infoValue = byref(retVal)
    elif returnType == 'uint':
        retVal = c_uint()
        infoValue = byref(retVal)
    elif returnType == 'double':
        retVal = c_double()
        infoValue = byref(retVal)
    elif returnType == 'str':
        retVal = ctypes.create_string_buffer(BUF_SIZE)
        infoValue = retVal
    else:
        raise Exception("returnType must be one of 'int', 'uint', 'double' or 'str'")
    call('getInstrumentInfo', c_uint(instrumentID), c_char_p(parameterString), infoValue)
    return retVal.value

def getNbrChannels(instrumentID):
    """Returns the number of channels on the specified module"""
    nbrChannels = c_int()
    call('getNbrChannels', c_uint(instrumentID), byref(nbrChannels))
    return nbrChannels.value

def getNbrInstruments():
    """Returns the number of Acqiris instruments found on the computer"""
    nbrInstruments = c_int()
    call('getNbrInstruments', byref(nbrInstruments))
    return nbrInstruments.value

def getVersion(instrumentID, versionItem):
    """Returns the version numbers associated with a specified instrument or current device driver.
    
    instrumentID - instrument identifier
    versionItem - 1 for version of Kernel-Mode Driver
                  2 for version of EEPROM Common Section
                  3 for version of EEPROM Instrument Section
                  4 for version of CPLD firmware
    """
    version = c_int()
    call('getVersion', c_uint(instrumentID), c_int(versionItem), byref(version))
    return version.value

def init(resourceName, resetDevice=False, options={}):
    """Initializes an instrument
    
    resourceName - string which identifies the resource to be initialized
    resetDevice - if True, resets the module after initialization
    options - options to be used in initialization.  If options are given,
              then this calls Acqrs_initWithOptions, otherwise it calls Acqrs_init.
              Options can be specified as a string in the form required by the driver,
              or as a python map, e.g. options={'CAL': False}
              
    returns the instrumentID of the initialized instrument.
    """
    instrumentID = c_uint()
    if options:
        if isinstance(options, str):
            optionsString = options
        else:
            optionsString = ','.join('%s=%s' % (k, v) for (k, v) in options.items())
        call('initWithOptions',
             c_char_p(resourceName), False, c_ushort(resetDevice), optionsString,
             byref(instrumentID))        
    else:
        call('init',
             c_char_p(resourceName), False, c_ushort(resetDevice),
             byref(instrumentID))
    return instrumentID.value

def initWithOptions(resourceName, resetDevice=False, optionsString=''):
    raise Exception('not implemented; instead call init with additional options parameter')

def logicDeviceIO():
    raise Exception('not implemented')

def powerSystem(powerOn=True):
    """Forces all instruments to prepare entry into or return from the system power down state"""
    call('powerSystem', c_int(powerOn), c_int(0))

def reset(instrumentID):
    """Resets an instrument
    
    Note that according to the programmers reference manual:
    'There is no known situation where this action is to be recommended'
    """
    call('reset', c_uint(instrumentID))

def resetMemory(instrumentID):
    """Resets the instrument's memory to a known default state"""
    call('resetMemory', c_uint(instrumentID))

def resumeControl(instrumentID):
    """Resume the control of an instrument that was suspended"""
    call('resumeControl', c_uint(instrumentID))

def setAttributeString(instrumentID, channel, name, value):
    """Sets an attribute with a string value"""
    call('setAttributeString', c_uint(instrumentID), c_int(channel), c_char_p(name), c_char_p(value))

def setLEDColor(instrumentID, color):
    """Sets the from panel LED to the desired color
    
    instrumentID - instrument identifier
    color - 0 = OFF (return to normal acquisition status indicator)
            1 - Green
            2 - Red
            3 - Yellow
    """
    call('setLEDColor', c_uint(instrumentID), c_int(color))

def setSimulationOptions(options):
    """Sets one or several options for simulation
    
    These will be used if init is called with the option 'simulate'=True
    The simulation options are reset to none by passing an empty string
    """
    call('setSimulationOptions', c_char_p(options))

def suspendControl(instrumentID):
    """Suspend control of an instrument to allow using it from another process"""
    call('suspendControl', c_uint(instrumentID))


# AcqirisD1Interface.h

def accumulateData():
    raise Exception('not implemented')

def acqDone(instrumentID):
    """Checks if the acquisition has terminated"""
    done = c_ushort()
    call_D1('acqDone', c_uint(instrumentID), byref(done))
    return bool(done.value)

def acquire(instrumentID):
    """Starts an acquisition"""
    call_D1('acquire', c_uint(instrumentID))

def acquireEx():
    raise Exception('not implemented')

def averagedData(instrumentID, channel, readPar, nbrAcq, calculateMean, timeout):
    """Perform a series of acquisitions and get the resulting averaged waveform
    
    instrumentID - instrument identifier
    channel - the channel to acquire
    readPar - AqReadParameters structure describing the read request
    nbrAcq - the number of acquisitions (averages) to perform
    calculateMean - boolean indicating whether to divide sumArray by nbrAcq to get averages
    timeout - acquisition timeout in seconds
    
    Returns:
    dataArray - waveform destination array
    sumArray - waveform accumulation array
    dataDesc - waveform descriptor structure (AqDataDescriptor)
               returned values are for the last acquisition
    segDescArray - segment descriptor structure (AqSegmentDescriptorAvg)
                   returned values are for the last acquisition
    """
    nbrSegments = readPar.nbrSegments
    nbrSamples = readPar.nbrSamplesInSeg * nbrSegments
    
    dataArray = (c_byte * (nbrSamples + 32))() # is this correct, or should it be c_int?
    sumArray = (c_int * (nbrSamples))()
    dataDesc = AqDataDescriptor()
    segDescArray = (AqSegmentDescriptorAvg * nSegments)()
    
    readPar.dataArraySize = ctypes.sizeof(dataArray)
    readPar.segDescArraySize = ctypes.sizeof(segDescArray)
    call_D1('averagedData',
            c_uint(instrumentID), c_int(channel),
            byref(readPar), c_int(nbrAcq), c_ushort(calculateMean), c_double(timeout),
            dataArray, sumArray, byref(dataDesc), segDescArray)
    return (dataArray, sumArray, dataDesc, segDescArray)

def bestNominalSamples(instrumentID):
    """Helper function to return the maximum number of samples that fit into the available memory"""
    nomSamples = c_int()
    call_D1('bestNominalSamples', c_uint(instrumentID), byref(nomSamples))
    return nomSamples.value

def bestSampInterval(instrumentID, maxSamples, timeWindow):
    """Helper function to return the best possible sampling rate for an acquisition
    
    Computes the best sampling rate to cover the timeWindow with no more than maxSamples,
    taking into account the requested state of the instrument, in particular the
    requested number of segments.  Also calculates the 'real' nominal number of
    samples that can be accomodated (computed as timeWindow/samplingInterval).
    
    Returns a tuple of (sampInterval, nomSamples)
    """
    sampInterval = c_double()
    nomSamples = c_int()
    call_D1('bestSampInterval',
            c_uint(instrumentID), c_int(maxSamples), c_double(timeWindow),
            byref(sampInterval), byref(nomSamples))
    return (sampInterval.value, nomSamples.value)

def configAvgConfig(instrumentID, channelNbr, parameterString, value):
    """Configures a parameter for averager/analyzer operation"""
    if isinstance(value, (int, long)):
        func = 'configAvgConfigInt32'
        value = c_int(value)
    elif isinstance(value, double):
        func = 'configAvgConfigReal64'
        value = c_double(value)
    else:
        raise Exception('value must be int or double')
    call_D1(func, c_uint(instrumentID), c_int(channelNbr), c_char_p(parameterString), value)

def configAvgConfigInt32():
    raise Exception('not implemented; instead call configAvgConfig directly with integer value')

def configAvgConfigReal64():
    raise Exception('not implemented; instead call configAvgConfig directly with double value')

def configChannelCombination(instrumentID, nbrConvertersPerChannel, usedChannels):
    """Configures how many converters are to be used for which channels"""
    call_D1('configChannelCombination',
            c_uint(instrumentID), c_int(nbrCOnvertersPerChannel), c_int(usedChannels))

def configControlIO(instrumentID, connector, signal, qualifier1, qualifier2):
    """Configures a ControlIO connector"""
    call_D1('configControlIO',
            c_uint(instrumentID), c_int(connector), c_int(signal),
            c_int(qualifier1), c_double(qualifier2))

CLOCK_INT = 0
CLOCK_EXT = 1
CLOCK_EXT_REF = 2
CLOCK_EXT_START_STOP = 4

def configExtClock(instrumentID, clockType, inputThreshold,
                   delayNbrSamples=0, inputFrequency=0.0, sampFrequency=0.0):
    """Configures the external clock of the digitizer
    
    clockType - 0 = Internal clock (default)
                1 = External clock, continuously running
                2 = External reference (10 MHz)
                4 = External clock, with start/stop sequence
    inputThreshold - Input threshold for external clock or reference in mV
    
    parameters delayNbrSamples, inputFrequency and sampFrequency only apply
    when clockType = 1
    """
    call_D1('configExtClock',
            c_uint(instrumentID), c_int(clockType), c_double(inputThreshold), c_int(delayNbrSamples),
            c_double(inputFrequency), c_double(sampFrequency))

def configFCounter(instrumentID, signalChannel, type, targetValue, apertureTime):
    """Configures a frequency counter measurement"""
    call_D1('configFCounter',
            c_uint(instrumentID), c_int(signalChannel), c_int(type),
            c_double(targetValue), c_double(apertureTime), c_double(0.0), c_int(0))

def configHorizontal(instrumentID, sampInterval, delayTime):
    """Configures the horizontal control parameters of the digitizer"""
    call_D1('configHorizontal', c_uint(instrumentID), c_double(sampInterval), c_double(delayTime))

def configMemory(instrumentID, nbrSamples, nbrSegments):
    """Configures the memory control parameters of the digitizer"""
    call_D1('configMemory', c_uint(instrumentID), c_int(nbrSamples), c_int(nbrSegments))

def configMemoryEx():
    raise Exception('not implemented')

MODE_NORMAL = 0
MODE_AVERAGE = 2

def configMode(instrumentID, mode=0, modifier=0, flags=0):
    """Configures the operational mode of Averagers and Analyzers and certain special Digitizer acquisition modes
    
    mode - 0 = normal data acquisition
           1 = AC/SC stream data to DPU
           2 = averaging mode
           3 = buffered data acquisition
           5 = Peak mode for Analyzers with this option
           6 = frequency counter mode
           7 = AP235/AP240-SSR mode
    modifier - unused; set to 0
    flags - possible values depends on mode (see docs)
    """
    call_D1('configMode', c_uint(instrumentID), c_int(mode), c_int(modifier), c_int(flags))

def configMultiInput(instrumentID, channel, input):
    """Selects the active input when there are multiple inputs on a channel"""
    call_D1('configMultiInput', c_uint(instrumentID), c_int(channel), c_int(input))

def configSetupArray():
    raise Exception('not implemented')

TRIG_EDGE = 0
TRIG_TV = 1
TRIG_OR = 3
TRIG_NOR = 4
TRIG_AND = 5
TRIG_NAND = 6

def configTrigClass(instrumentID, trigClass, sourcePattern):
    """Configures the trigger class control parameters of the digitizer"""
    call_D1('configTrigClass',
            c_uint(instrumentID), c_int(trigClass), c_int(sourcePattern),
            c_int(0), c_int(0), c_double(0.0), c_double(0.0))

TRIG_COUPLING_DC = 0
TRIG_COUPLING_AC = 1
TRIG_COUPLING_HF_REJECT = 2
TRIG_COUPLING_DC_50W = 3
TRIG_COUPLING_AC_50W = 4

SLOPE_POS = 0
SLOPE_NEG = 1
SLOPE_OUT_OF_WINDOW = 2
SLOPE_INTO_WINDOW = 3
SLOPE_HF_DIVIDE = 4
SLOPE_SPIKE = 5

def configTrigSource(instrumentID, channel, trigCoupling, trigSlope, trigLevel1, trigLevel2=0.0):
    """Configures the trigger source control parameters for the specified trigger source"""
    call_D1('configTrigSource',
            c_uint(instrumentID), c_int(channel), c_int(trigCoupling), c_int(trigSlope),
            c_double(trigLevel1), c_double(trigLevel2))

def configTrigTV():
    raise Exception('not implemented')

COUPLING_GND = 0
COUPLING_DC_1M = 1
COUPLING_AC_1M = 2
COUPLING_DC_50 = 3
COUPLING_AC_50 = 4

BANDWIDTH_NOLIM = 0
BANDWIDTH_25M = 1
BANDWIDTH_700M = 2
BANDWIDTH_200M = 3
BANDWIDTH_20M = 4
BANDWIDTH_35M = 5

def configVertical(instrumentID, channel, fullScale, offset, coupling, bandwidth):
    """Configures the vertical control parameters for a specified channel of the digitizer"""
    call_D1('configVertical',
            c_uint(instrumentID), c_int(channel),
            c_double(fullScale), c_double(offset), c_int(coupling), c_int(bandwidth))

def forceTrig():
    raise Exception('not implemented')

def forceTrigEx():
    raise Exception('not implemented')

def freeBank():
    raise Exception('not implemented')

def getAvgConfig(instrumentID, channelNbr, parameterString, returnType):
    """Returns an attribute from the analyzer/averager configuration for channelNbr
    
    Return type must be one of 'int' or 'double' to indicate
    the expected return type for the requested parameter.
    """
    if returnType == 'int':
        retVal = c_int()
    elif returnType == 'double':
        retVal = c_double()
    else:
        raise Exception("returnType must be one of 'int' or 'double'")
    call_D1('getInstrumentInfo', c_uint(instrumentID), c_char_p(parameterString), byref(retVal))
    return retVal.value

def getAvgConfigInt32():
    raise Exception("not implemented; instead call getAvgConfig with returnType='int'")

def getAvgConfigReal64():
    raise Exception("not implemented; instead call getAvgConfig with returnType='double'")

def getChannelCombination(instrumentID):
    """Returns the current channel combination parameters of the digitizer
    
    Returns a tuple of (nbrConvertersPerChannel, usedChannels)
    """
    nbrConvertersPerChannel = c_int()
    usedChannels = c_int()
    call_D1('getChannelCombination', c_uint(instrumentID), byref(nbrConvertersPerChannel), byref(usedChannels))
    return (nbrConvertersPerChannel.value, usedChannels.value)

def getControlIO(instrumentID, connector):
    """Returns the configuration of a ControlIO connector
    
    Returns a tuple of (signal, qualifier1, qualifier2)
    """
    signal = c_int()
    qualifier1 = c_int()
    qualifier2 = c_double()
    call_D1('getControlIO', c_uint(instrumentID), c_int(connector), byref(signal), byref(qualifier1), byref(qualifier2))
    return (signal.value, qualifier1.value, qualifier2.value)

def getExtClock(instrumentID):
    """Returns the current external clock control parameters of the digitizer
    
    Returns a tuple of (clockType, inputThreshold, delayNbrSamples, inputFrequency, sampFrequency)
    """
    clockType = c_int()
    inputThreshold = c_double()
    delayNbrSamples = c_int()
    inputFrequency = c_double()
    sampFrequency = c_double()
    call_D1('getExtClock', c_uint(instrumentID),
            byref(clockType), byref(inputThreshold), byref(delayNbrSamples), byref(inputFrequency), byref(sampFrequency))
    return (clockType.value, inputThreshold.value, delayNbrSamples.value, inputFrequency.value, sampFrequency.value)

def getFCounter(instrumentID):
    """Returns the current frequency counter configuration
    
    Returns a tuple of (signalChannel, type, targetValue, apertureTime)
    """
    signalChannel = c_int()
    type = c_int()
    targetValue = c_double()
    apertureTime = c_double()
    call_D1('getFCounter',
            c_uint(instrumentID), byref(signalChannel), byref(type),
            byref(targetValue), byref(apertureTime), byref(c_double()), byref(c_int()))
    return (signalChannel.value, type.value, targetValue.value, apertureTime.value)

def getHorizontal(instrumentID):
    """Returns the current horizontal control parameters of the digitizer
    
    Returns a tuple of (sampInterval, delayTime)
    """
    sampInterval = c_double()
    delayTime = c_double()
    call_D1('getHorizontal', c_uint(instrumentID), byref(sampInterval), byref(delayTime))
    return (sampInterval.value, delayTime.value)

def getMemory(instrumentID):
    """Returns the current memory control parameters of the digitizer
    
    Returns a tuple of (nbrSamples, nbrSegments)
    """
    nbrSamples = c_int()
    nbrSegments = c_int()
    call_D1('getMemory', c_uint(instrumentID), byref(nbrSamples), byref(nbrSegments))
    return (nbrSamples.value, nbrSegments.value)

def getMemoryEx():
    raise Exception('not implemented')

def getMode(instrumentID):
    """Returns the current operational mode of the digitizer
    
    Returns a tuple of (mode, modifier, flags)
    """
    mode = c_int()
    modifier = c_int()
    flags = c_int()
    call_D1('getMode', c_uint(instrumentID), byref(mode), byref(modifier), byref(flags))
    return (mode.value, modifier.value, flags.value)

def getMultiInput(instrumentID, channel):
    """Returns the multiple input configuration on a channel"""
    input = c_int()
    call_D1('getMultiInput', c_uint(instrumentID), c_int(channel), byref(c_int))
    return input.value

def getSetupArray():
    raise Exception('not implemented')

def getTrigClass(instrumentID):
    """Returns the current trigger class control parameters of the digitizer
    
    Returns a tuple of (trigClass, sourcePattern)
    """
    trigClass = c_int()
    sourcePattern = c_int()
    call_D1('getTrigClass', c_uint(instrumentID), byref(trigClass), byref(sourcePattern),
            byref(c_int()), byref(c_int()), byref(c_double()), byref(c_double()))
    return (trigClass.value, sourcePattern.value)

def getTrigSource(instrumentID, channel):
    """Returns the current trigger source control parameters for a specified channel
    
    Returns a tuple of (trigCoupling, trigSlope, trigLevel1, trigLevel2)
    """
    trigCoupling = c_int()
    trigSlope = c_int()
    trigLevel1 = c_double()
    trigLevel2 = c_double()
    call_D1('getTrigSource', c_uint(instrumentID), c_int(channel),
            byref(trigCoupling), byref(trigSlope), byref(trigLevel1), byref(trigLevel2))
    return (trigCoupling.value, trigSlope.value, trigLevel1.value, trigLevel2.value)

def getTrigTV():
    raise Exception('not implemented')

def getVertical(instrumentID, channel):
    """Returns the vertical control parameters for a specified channel in the digitizer
    
    Returns a tuple of (fullScale, offset, coupling, bandwidth)
    """
    fullScale = c_double()
    offset = c_double()
    coupling = c_int()
    bandwidth = c_int()
    call_D1('getVertical', c_uint(instrumentID), c_int(channel),
            byref(fullScale), byref(offset), byref(coupling), byref(bandwidth))
    return (fullScale.value, offset.value, coupling.value, bandwidth.value)

def multiInstrAutoDefine():
    """Automatically initialize all digitizers and combine as many as possible to MultiInstruments
    
    Returns the number of user-accessible instruments
    """
    nbrInstruments = c_int()
    call_D1('multiInstrAutoDefine', '', byref(nbrInstruments))
    return nbrInstruments.value

def multiInstrDefine():
    raise Exception('not implemented')

def multiInstrUndefineAll():
    raise Exception('not implemented')

def procDone(instrumentsID):
    """Checks if the on-board data processing has terminated"""
    done = c_ushort()
    call_D1('procDone', c_uint(instrumentID), byref(done))
    return bool(done.value)

def processData():
    raise Exception('not implemented')

DATATYPE_BYTE = 0
DATATYPE_SHORT = 1
DATATYPE_INT = 2
DATATYPE_DOUBLE = 3

def readData(instrumentID, channel, readPar):
    """Returns all waveform information
    
    This function handles allocation of the dataArray and segDescArray,
    and so will set the dataArraySize and segDescArraySize fields in the
    readPar structure.
    """
    nbrSegments = readPar.nbrSegments
    nbrSamples = readPar.nbrSamplesInSeg * nbrSegments
    
    # allocate data array based on the requested type
    if readPar.dataType == DATATYPE_BYTE:
        dataType = c_byte
    elif readPar.dataType == DATATYPE_SHORT:
        dataType = c_short
    elif readPar.dataType == DATATYPE_INT:
        dataType = c_int
    elif readPar.dataType == DATATYPE_DOUBLE:
        dataType = c_double
    dataArray = (dataType * (nbrSamples + 32))()
    
    # allocate data descriptor struct
    dataDesc = AqDataDescriptor()
    
    # allocate segment descriptor array
    if readPar.readMode in [0, 1, 3]:
        segDescType = AqSegmentDescriptor
    elif readPar.readMode in [2, 5, 6]:
        segDescType = AqSegmentDescriptorAvg
    elif readPar.readMode in [11]:
        segDescType = AqSegmentDescriptorSeqRaw
    else:
        raise Exception('unknown readMode: %d' % (readPar.readMode))
    segDescArray = (segDescType * nbrSegments)()
    
    # set the sizes of data and segment descriptor arrays
    readPar.dataArraySize = ctypes.sizeof(dataArray)
    readPar.segDescArraySize = ctypes.sizeof(segDescArray)
    
    call_D1('readData', c_uint(instrumentID), c_int(channel), byref(readPar),
            dataArray, byref(dataDesc), segDescArray)
    return (dataArray, dataDesc, segDescArray)

def readFCounter(instrumentID):
    """Returns the result of a frequency counter measurement"""
    result = c_double()
    call_D1('readFCounter', c_uint(instrumentID), byref(result))
    return result.value

def reportNbrAcquiredSegments(instrumentID):
    """Returns the number of segments already acquired for a digitizer
    
    For averagers, it gives the number of triggers already accepted for the current acquisition
    """
    nbrSegments = c_int()
    call_D1('reportNbrAcquiredSegments', c_uint(instrumentID), byref(nbrSegments))
    return nbrSegments.value

def resetDigitizerMemory(instrumentID):
    """Resets the digitizer memory to a known default state"""
    call_D1('resetDigitizerMemory', c_uint(instrumentID))

def restoreInternalRegisters():
    raise Exception('not implemented')

def stopAcquisition(instrumentID):
    """Stops the acquisition"""
    call_D1('stopAcquisition', c_uint(instrumentID))

def stopProcessing(instrumentID):
    """Stops on-board data processing"""
    call_D1('stopProcessing', c_uint(instrumentID))

def waitForEndOfAcquisition(instrumentID, timeout):
    """Waits for the end of acquisition"""
    call_D1('waitForEndOfAcquisition', c_uint(instrumentID), c_int(timeout))

def waitForEndOfProcessing(instrumentID, timeout):
    """Waits for the end of processing"""
    call_D1('waitForEndOfProcessing', c_uint(instrumentID), c_int(timeout))


