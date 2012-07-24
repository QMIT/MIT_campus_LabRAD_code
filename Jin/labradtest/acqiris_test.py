import matplotlib.pyplot as plt

import acqiris
import aqdrv4

n = acqiris.getNbrInstruments()
print 'found %d instruments' % n

i = 0
if n > 1:
    i = int(raw_input('Choose an instrument (0-%d): ' % (n-1)))

print 'initializing instrument %d' % i
inst = acqiris.AcqirisInstrument('PCI::INSTR%d' % i)

name, serial, bus, slot = inst.getInstrumentData()
print '  name: %s' % name
print '  serial: %d' % serial
print '  bus: %d' % bus
print '  slot: %d' % slot

print 'calibrating...',
inst.calibrate()
print 'done.'

sampInterval = 500e-12
delayTime = 0.0

acqChannel = 1
acqCoupling = aqdrv4.COUPLING_DC_50
acqBandwidth = aqdrv4.BANDWIDTH_NOLIM

trigChannel = 1
trigClass = aqdrv4.TRIG_EDGE
trigCoupling = aqdrv4.TRIG_COUPLING_DC
trigLevel = 0.0 # in % of full-scale
trigSlope = aqdrv4.SLOPE_POS
nSamples = 2048 # max is 8083
nSegments = 1
nAverage = 10000
fullScale = 0.05 # Vpp: 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0
offset = 0.0

# setup acquisition parameters
inst.configHorizontal(sampInterval, delayTime)
inst.configMemory(nSamples, nSegments)
inst.configVertical(acqChannel, fullScale, offset, acqCoupling, acqBandwidth)
inst.configTrigClass(trigClass, 0x00000001)
inst.configTrigSource(trigChannel, trigCoupling, trigSlope, trigLevel)

data = inst.grabWaveform(nSamples)[0]
dataAvg = inst.grabWaveform(nSamples, nAverage)[0]

inst.close()
acqiris.closeAll()


fig, ax = plt.subplots(1, 1)
ax.plot(data, 'r-', label='raw')
ax.plot(dataAvg, 'k-', label='averaged')
plt.show()
