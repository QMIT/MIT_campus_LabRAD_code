from guidata.qt.QtGui import QFont

from guiqwt.plot import CurveDialog, CurveWidget
from guiqwt.builder import make
import numpy as np
import matplotlib.pyplot as pp
def plot(*items):
    win = CurveDialog(edit=True, toolbar=True, wintitle="CurveDialog test",
                      options=dict(title="PNA", xlabel="frequency",
                                   ylabel="amplitude"))
    plot = win.get_plot()
    for item in items:
        plot.add_item(item)
    plot.set_axis_font("left", QFont("Courier"))
    win.get_itemlist_panel().show()
    plot.set_items_readonly(False)
    win.show()
    win.exec_()

def test():
    """Test"""
    # -- Create QApplication
    import guidata
    _app = guidata.qapplication()
    # --
    from numpy import linspace, sin
    import labrad
    cx=labrad.connect('lab-rat', password='0rland0')
#    ai=cx.agilent_pna_with_vxi_11
#    ai.select_device(0)
#    testscan=ai.freq_sweep()
    psg=cx.agilent_psg_no_pulse_check
    Select_LO=psg.select_device('lab-rat GPIB Bus - TCPIP0::192.168.5.101::inst0')
    Select_RF=psg.select_device('lab-rat GPIB Bus - TCPIP0::192.168.5.102::inst1')

    adc=cx.acqiris_adc
    adc.select_device(0)
    adc.config_clock('INT')
    adc.config_horizontal(2048,1e-9,0)
    adc.config_trigger_class('EDGE', 'EXT1')
    adc.config_trigger_source('EXT1', 'DC', 'POS', 2000)
    adc.config_vertical(1, 0.05,0,'DC_50','NOLIM')
    adc.config_vertical(2, 0.05,0,'DC_50','NOLIM')
    
    fscan=int(10.9905e9)     #center frequency for scanning
    fwidth=int(10e6)        #frequency range for scan, [fscan-fpan, fscan+fpan]
    fstep=int(0.01e6)          #frequency steps for scanning
    fdelta=int(10e6)         #mixer delta        
    
    i=0
    print len(range(fscan-fwidth, fscan+fwidth+fstep, fstep))
    xx=np.multiply(range(fscan-fwidth, fscan+fwidth+fstep, fstep),1e-9)
    yy=np.zeros(len(xx))
    psg.select_device('lab-rat GPIB Bus - TCPIP0::192.168.5.101::inst0')
    psg.output(True)
    psg.select_device('lab-rat GPIB Bus - TCPIP0::192.168.5.102::inst1')
    psg.output(True)


    #main loop
    for f in range(fscan-fwidth, fscan+fwidth+fstep, fstep):
        psg.select_device('lab-rat GPIB Bus - TCPIP0::192.168.5.101::inst0')
        psg.frequency(f*1e-9)
        psg.select_device('lab-rat GPIB Bus - TCPIP0::192.168.5.102::inst1')
        psg.frequency((f+fdelta)*1e-9)
        pp.pause(0.2)
        testscan=adc.acquire(1900,[1,2])
        rawsignal=testscan.asarray[0]
#        clearsignal=testscan.asarray[0]
        rawoffset=np.mean(rawsignal)
#        print rawoffset
        clearsignal=np.subtract(rawsignal, rawoffset)
        rms=np.sqrt(np.mean(np.square(clearsignal)))
        print rms, i
        yy[i]=np.log10(rms)*10
        i=i+1
        #loop here
        
    
#    len(testscan)
#    II=testscan.asarray[0]
#    QQ=testscan.asarray[1]
#    MODE=np.sqrt(np.square(II)+np.square(QQ))
#    xx=range(2048)
#    x = linspace(-10, 10, 200)
#    dy = x/100.
#    y = sin(sin(sin(x)))    
#    x2 = linspace(-10, 10, 20)
#    y2 = sin(sin(sin(x2)))
#    plot(make.curve(x, y, color="b"),
#         make.curve(x2, y2, color="g", curvestyle="Sticks"),
#         make.curve(x, sin(2*y), color="r"),
#         make.merror(x, y/2, dy),
#         make.label("Relative position <b>outside</b>",
#                    (x[0], y[0]), (-10, -10), "BR"),
#         make.label("Relative position <i>inside</i>",
#                    (x[0], y[0]), (10, 10), "TL"),
#         make.label("Absolute position", "R", (0,0), "R"),
#         make.legend("TR"),
#         make.marker(position=(5., .8), label_cb=lambda x, y: u"A = %.2f" % x,
#                     markerstyle="|", movable=False)
#         )
    plot(make.curve(xx, yy, color="b"),
#         make.curve(xx, QQ, color="g"),
#         make.curve(xx, MODE, color="r"),
#         make.curve(x, sin(2*y), color="r"),
#         make.merror(x, y/2, dy),
#         make.label("ADC SCAN<b>test</b>",
#                   (xx[0], II[0]), (-10, -10), "BR"),
#         make.label("ADC SCAN<b>test 2X</b>",
#                   (xx[0], QQ[0]), (-10, -10), "BR")
#         make.label("ADC SCAN<b>test 2X</b>",
#                    (xx[0], MODE[0]), (-10, -10), "BR"),
#         make.label("Relative position <i>inside</i>",
#                    (x[0], y[0]), (10, 10), "TL"),
#         make.label("Absolute position", "R", (0,0), "R"),
#         make.legend("TR")
#         make.marker(position=(5., .8), label_cb=lambda xx, yy: u"A = %.2f" % xx,
#                     markerstyle="|", movable=False)
         )

if __name__ == "__main__":
    test()