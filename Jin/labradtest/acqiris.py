import functools

import numpy as np

import aqdrv4
from aqdrv4 import (getNbrInstruments, closeAll, AcqirisException, TimeoutException)


class AcqirisInstrument(object):
    def __init__(self, name, *args, **kw):
        self.instrumentID = aqdrv4.init(name, *args, **kw)
        self.devName, self.serial, self.bus, self.slot = aqdrv4.getInstrumentData(self.instrumentID)
    
    def configAveraging(self, channel, **params):
        """Setup parameters for averaging mode"""
        for key, value in params.items():
            aqdrv4.configAvgConfig(self.instrumentID, channel, key, value)
    
    def __getattr__(self, name):
        """For attributes that have not been defined explicitly, we defer to the
        underlying driver function, adding our instrumentID as the first parameter
        """
        f = getattr(aqdrv4, name)
        @functools.wraps(f)
        def func(*args, **kw):
            return f(self.instrumentID, *args, **kw)
        return func
    
    def grabWaveform(self, nSamples, nAverages=1, channels=[1], timeout=1000, forceAverageMode=False):
        """Convenience function that runs an acquisition, processes the data and returns waveforms
        
        nAverages - the number of averages to perform.  if nAverages == 1, acquires a single trace
        channels - a list specifying which channels to acquire
        timeout - time in milliseconds to wait before timing out when attempting to acquire data
        
        returns a 2D numpy array of data, where the first index refers to the channel, in the order
        given by the channels argument.
        """
        if nAverages <= 0:
            raise Exception('grabWaveform: nAverages must be >= 1')
        
        if nAverages == 1 and not forceAverageMode:
            self.configMode(0, 0, 0) # single trace mode
            readPar = aqdrv4.AqReadParameters(dataType=aqdrv4.DATATYPE_DOUBLE,
                                              readMode=0, # standard waveform
                                              nbrSegments=1,
                                              nbrSamplesInSeg=nSamples,
                                              firstSegment=0,
                                              firstSampleInSegment=0)
        else:
            self.configMode(2, 0, 0) # averaging mode
            self.configAveraging(1, NbrSamples=nSamples, NbrSegments=1, NbrWaveforms=nAverages, StartDelay=0, StopDelay=0)
            readPar = aqdrv4.AqReadParameters(dataType=aqdrv4.DATATYPE_INT,
                                              readMode=2, # averaged waveform
                                              nbrSegments=1,
                                              nbrSamplesInSeg=nSamples,
                                              firstSegment=0,
                                              firstSampleInSegment=0)
        self.acquire()
        self._awaitAcquisition(timeout)
        
        waveforms = []
        for channel in channels:
            dataArray, dataDesc, segDescArray = self.readData(channel, readPar)
            dataAvg = _extractWaveform(dataArray, dataDesc, rescale=True)
            waveforms.append(dataAvg)
        
        return np.array(waveforms)
    
    def _awaitAcquisition(self, timeout):
        """Wait for acquisition to complete, or else raise TimeoutException
        
        Makes multiple calls to waitForEndOfAcquisition as needed to handle
        arbitrarily-long timeouts.  This is necessary because the driver
        limits the timeout to 10 seconds per call.
        """
        remaining = timeout
        while True:
            try:
                timeout = min(remaining, 10000)
                remaining -= timeout
                self.waitForEndOfAcquisition(timeout=timeout)
                break
            except TimeoutException:
                if remaining:
                    continue
                self.stopAcquisition()
                raise

def _extractWaveform(dataArray, dataDesc, collapse=True, rescale=True):
    """Extract waveform data returned from Acqiris into a numpy array
    
    Returns an array whose dtype is determined by the type of data read from the device
    (byte, short, int or double).  The returned array will in general be two-dimensional
    with the first index giving the segment and the second giving the sample within the
    segment.  If collapse is True (the default), then the array will be collapsed into
    a one-dimensional waveform in the case when there is only one segment.  If rescale
    is True (the default), then the values will be rescaled based on vGain and vOffset,
    resulting in a floating point result regardless of the acquired data type.
    """
    indexFirstPoint = dataDesc.indexFirstPoint
    nbrSamplesPerSeg = dataDesc.returnedSamplesPerSeg
    nbrSegments = dataDesc.returnedSegments
    data = np.ctypeslib.as_array(dataArray)
    data = data[indexFirstPoint:indexFirstPoint + nbrSamplesPerSeg*nbrSegments]
    if nbrSegments > 1 or not collapse:
        data = data.reshape(nbrSegments, -1)
    if rescale and data.dtype != float:
        # we only rescale the data if asked
        # also, float data from a single-trace acquisition does not need to be rescaled
        data = data.astype(float)
        data /= dataDesc.nbrAvgWforms 
        data -= 255/2. # hack: vOffset doesn't work, so this adds a manual offset (8-bit only!)
        data = dataDesc.vGain * data - dataDesc.vOffset
    return data

