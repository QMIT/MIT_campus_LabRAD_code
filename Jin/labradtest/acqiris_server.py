"""
### BEGIN NODE INFO
[info]
name = Acqiris ADC
version = 1.0
description = 
instancename = Acqiris ADC

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import ctypes
import functools
import math

from twisted.python import log
from twisted.internet import defer, reactor, threads
from twisted.internet.defer import inlineCallbacks, returnValue

from labrad import types as T, util
from labrad.devices import DeviceServer, DeviceWrapper
from labrad.errors import Error
from labrad.server import setting
from labrad.units import s, ms, V, mV, Hz, MHz, GHz

import acqiris
import aqdrv4

# TODO make it possible to run ADCs on multiple computers
# TODO support auto-calculation of timeout
# TODO expose additional functionality as settings
# - calibration
# - ability to query device state
# - suspend/resume
# - controlIO

class AcqirisDevice(DeviceWrapper):
    def connect(self, name):
        print 'connecting to %s...' % name,
        self.name = name
        self.inst = acqiris.AcqirisInstrument(name)
        print 'done.'
        print 'calibrating %s...' % name,
        self.inst.calibrate()
        print 'done.'
    
    def __getattr__(self, name):
        """For attributes that have not been defined explicitly,
        we defer to the underlying instrument
        """
        f = getattr(self.inst, name)
        @functools.wraps(f)
        def func(*args, **kw):
            return f(*args, **kw)
        return func
    
    def shutdown(self):
        print 'disconnecting from %s...' % self.name,
        #self.inst.close() # for some reason, this throws an exception...
        print 'done.'
    
    def _suspend(self):
        self.inst.suspendControl()
    
    @inlineCallbacks
    def _resume(self):
        """Resume control of the adc device.
        
        We defer this to a thread because it may block.
        """
        def resume():
            self.resumeControl()
        yield threads.deferToThread(resume)

class AcqirisServer(DeviceServer):
    """Provides access to Acqiris ADC boards."""
    name = 'Acqiris ADC'
    deviceWrapper = AcqirisDevice

    def findDevices(self):
        """Find acqiris instruments.
        
        Returns a list of (name, args, kw) tuples giving the device name
        and the positional and keyword arguments that will be passed to
        the device wrapper's "connect" method.
        """
        nbrDevices = acqiris.getNbrInstruments()
        names = ['PCI::INSTR%d' % i for i in range(nbrDevices)]
        return [(name, (name,), {}) for name in names]

    @inlineCallbacks
    def stopServer(self):
        print 'closing all acqiris connections...',
        acqiris.closeAll()
        print 'done.'
        yield DeviceServer.stopServer(self)

    @setting(100, nSamples='w', sampInterval='v[s]', delayTime='v[s]', returns='')
    def config_horizontal(self, c, nSamples, sampInterval, delayTime):
        """Configures the horizontal (time) axis for acquisition.
        
        This corresponds to the AcqrsD1_configHorizontal and AcqrsD1_configMemory
        commands of the aqdrv4 interface library.
        """
        nSegments = 1 # we do not currently support segmented waveforms
        dev = self.selectedDevice(c)
        dev.configHorizontal(sampInterval[s], delayTime[s])
        dev.configMemory(nSamples, nSegments)
        c['nSamples'] = nSamples
    
    @setting(150, clockType=['w', 's'], inputThreshold='v[mV]', delayNbrSamples='w', inputFrequency='v[MHz]', sampFrequency='v[MHz]', returns='')
    def config_clock(self, c, clockType, inputThreshold=0*mV, delayNbrSamples=0, inputFrequency=10*MHz, sampFrequency=1*GHz):
        """Configures the internal or external clock reference for the selected device
        
        This corresponds to the AcqrsD1_configExtClock command of the aqdrv4 interface library.
        """
        if isinstance(clockType, str):
            clockDict = {
                'INT': aqdrv4.CLOCK_INT,
                'EXT': aqdrv4.CLOCK_EXT,
                'EXT_REF': aqdrv4.CLOCK_EXT_REF,
                'EXT_START_STOP': aqdrv4.CLOCK_EXT_START_STOP
            }
            clockType = getChoice('clockType', clockType, clockDict)
        dev = self.selectedDevice(c)
        dev.configExtClock(clockType, inputThreshold[mV], delayNbrSamples, inputFrequency[Hz], sampFrequency[Hz])
    
    @setting(200, channel='w', fullScale='v[V]', offset='v[V]', coupling=['s', 'w'], bandwidth=['s', 'w'], returns='')
    def config_vertical(self, c, channel, fullScale, offset, coupling, bandwidth):
        """Configures the vertical (voltage) axis for acquisition on a single channel
        
        This corresponds to the AcqrsD1_configVertical command of the aqdrv4 interface library.
        """
        if isinstance(coupling, str):
            coupleDict = {
                'GND': aqdrv4.COUPLING_GND,
                'DC_1M': aqdrv4.COUPLING_DC_1M,
                'AC_1M': aqdrv4.COUPLING_AC_1M,
                'DC_50': aqdrv4.COUPLING_DC_50,
                'AC_50': aqdrv4.COUPLING_AC_50
            }
            coupling = getChoice('coupling', coupling, coupleDict)
        if isinstance(bandwidth, str):
            bwDict = {
                'NOLIM': aqdrv4.BANDWIDTH_NOLIM,
                '25MHz': aqdrv4.BANDWIDTH_25M,
                '700MHz': aqdrv4.BANDWIDTH_700M,
                '200MHz': aqdrv4.BANDWIDTH_200M,
                '20MHz': aqdrv4.BANDWIDTH_20M,
                '35MHz': aqdrv4.BANDWIDTH_35M
            }
            bandwidth = getChoice('bandwidth', bandwidth, bwDict)
        dev = self.selectedDevice(c)
        dev.configVertical(channel, fullScale[V], offset[V], coupling, bandwidth)

    @setting(500, trigClass=['s', 'w'], sources=['s', 'i', '*s', '*i'], returns='')
    def config_trigger_class(self, c, trigClass, sources):
        """Configures the trigger class for the currently-selected instrument.
        
        trigClass - the trigger class, given as a string (EDGE, TV, OR, NOR, AND, NAND) or an int (see the driver docs)
        sources - a list of trigger sources, specified as strings or integers
                  the strings must be in the form 'INTn' for internal channels
                  or 'EXTn' for external channels where n is the channel number
                  alternatively, use positive integers 1, 2, ... for internal channels
                  and negative integers -1, -2, ... for external trigger channels
                  for trigger classes that use only a single channel, it is allowable
                  to specify just that one trigger.
        
        some examples:
        config_trigger_class('EDGE', 'INT1') - trigger on channel 1
        config_trigger_class('AND', ['INT2', 'EXT1']) - trigger on channel 2 and external trigger 1
        
        This corresponds to the AcqrsD1_configTrigClass command of the aqdrv4 interface library.
        """
        if isinstance(trigClass, str):
            trigDict = {
                'EDGE': aqdrv4.TRIG_EDGE,
                'TV': aqdrv4.TRIG_TV,
                'OR': aqdrv4.TRIG_OR,
                'NOR': aqdrv4.TRIG_NOR,
                'AND': aqdrv4.TRIG_AND,
                'NAND': aqdrv4.TRIG_NAND
            }
            trigClass = getChoice('trigClass', trigClass, trigDict)
        sourcePattern = 0
        if isinstance(sources, (str, int)):
            sources = [sources]
        for source in sources:
            if isinstance(source, str):
                if source.startswith('INT'):
                    source = int(source[3:])
                elif source.startswith('EXT'):
                    source = -int(source[3:])
                else:
                    raise Exception("Invalid trigger source: %s.  Must be of the form 'INTn' or 'EXTn' for channel n.")
            if source > 0:
                sourcePattern |= 0x00000001 << (source - 1)
            elif source < 0:
                sourcePattern |= 0x80000000 >> (-source - 1)
            else:
                raise Exception('Invalid trigger source: must be nonzero.')
            
        dev = self.selectedDevice(c)
        dev.configTrigClass(trigClass, sourcePattern)
    
    @setting(550, channel=['s', 'i'], trigCoupling=['s', 'w'], trigSlope=['s', 'w'], trigLevel='v', trigLevel2='v', returns='')
    def config_trigger_source(self, c, channel, trigCoupling, trigSlope, trigLevel, trigLevel2=None):
        """Configure the triggering for a particular channel
        
        channel - specifies the trigger channel to configure.  can be specified as an integer or string, as for config_trigger_class
        trigCoupling - specifies the trigger coupling for this channel
        trigSlope - specifies the trigger slope for this channel
        trigLevel - specifies the trigger level
        trigLevel2 - specifies the second trigger level (used only when trigSlope is one of the window triggering modes)
        
        trigger levels are interpreted as a percentage of full scale for internal channels,
        or in millivolts for external channels
        
        This corresponds to the AcqrsD1_configTrigSlope command of the aqdrv4 interface library.
        """
        if isinstance(channel, str):
            if channel.startswith('INT'):
                channel = int(channel[3:])
            elif channel.startswith('EXT'):
                channel = -int(channel[3:])
            else:
                raise Exception("Invalid trigger source: %s.  Must be of the form 'INTn' or 'EXTn' for channel n." % channel)
        if channel == 0:
            raise Exception('Trigger channel must be nonzero')
        if isinstance(trigCoupling, str):
            coupleDict = {
                'DC': aqdrv4.TRIG_COUPLING_DC,
                'AC': aqdrv4.TRIG_COUPLING_AC,
                'HF_REJECT': aqdrv4.TRIG_COUPLING_HF_REJECT,
                'DC_50W': aqdrv4.TRIG_COUPLING_DC_50W,
                'AC_50W': aqdrv4.TRIG_COUPLING_AC_50W
            }
            trigCoupling = getChoice('trigCoupling', trigCoupling, coupleDict)
        if isinstance(trigSlope, str):
            slopeDict = {
                'POS': (aqdrv4.SLOPE_POS, False),
                'NEG': (aqdrv4.SLOPE_NEG, False),
                'OUT_OF_WINDOW': (aqdrv4.SLOPE_OUT_OF_WINDOW, True),
                'INTO_WINDOW': (aqdrv4.SLOPE_INTO_WINDOW, True),
                'HF_DIVIDE': (aqdrv4.SLOPE_HF_DIVIDE, False),
                'SPIKE': (aqdrv4.SLOPE_SPIKE, False)
            }
            trigSlope, windowed = getChoice('trigSlope', trigSlope, slopeDict)
            if windowed and trigLevel2 is None:
                raise Exception('must specify trigLevel2 when using windowed triggering')
        # interpret trigger levels as percentages (millivolts) for internal (external) channels
        def checkUnits(level):
            if channel > 0:
                return level[''] # internal channels use percentage (dimensionless)
            elif channel < 0:
                return level['mV'] # external channels use millivolts
        trigLevel = checkUnits(trigLevel)
        if trigLevel2 is None:
            trigLevel2 = 0.0
        else:
            trigLevel2 = checkUnits(trigLevel2)

        # update the trigger configuration
        dev = self.selectedDevice(c)
        dev.configTrigSource(channel, trigCoupling, trigSlope, trigLevel, trigLevel2)

    @setting(1000, averages='w', channels='*w', timeout='v[ms]', returns='*2v[V]')
    def acquire(self, c, averages=1, channels=[1], timeout=1000*ms):
        """Performs an acquisition with the specified number of averages
        
        Returns a 2D array of the voltage waveforms on the specified channels
        """
        dev = self.selectedDevice(c)
        waveforms = dev.grabWaveform(c['nSamples'], averages, channels, int(math.ceil(timeout[ms])), forceAverageMode=True)
        return waveforms
    
    @setting(9999, name='s', args='?', returns='?')
    def call_driver_func(self, c, name, args=[]):
        """Call an arbitrary driver function on the currently-selected device
        
        name - the name of the function in aqdrv4.py to call.  These names
               follow those in the C interface, but with the Acqrs_ or AcqrsD1_
               prefixes removed.
        args - tuple of arguments to be passed to the driver function
        
        any values returned from the driver function will be returned
        """
        dev = self.selectedDevice(c)
        func = getattr(dev, name)
        return func(*args)


def getChoice(name, value, options):
    """Convert a string value into a numeric value from the given options.
    
    Provides a helpful error message if there is no match.
    """
    if value not in options:
        allowed = ', '.join(sorted(options.keys()))
        raise KeyError("invalid %s: %s.  Allowed values are: %s" % (name, value, allowed))
    return options[value]


__server__ = AcqirisServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
