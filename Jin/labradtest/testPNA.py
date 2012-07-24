from guidata.qt.QtGui import QFont

from guiqwt.plot import CurveDialog, CurveWidget
from guiqwt.builder import make
import numpy as np
def plot(*items):
    win = CurveDialog(edit=True, toolbar=True, wintitle="CurveDialog test",
                      options=dict(title="PNA", xlabel="frequency",
                                   ylabel="dBm"))
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
    ai=cx.agilent_pna
    ai.select_device(0)
    ai.s_parameters(['S21'])
    ai.averages(1000)
    ai.bandwidth(100)
    ai.power(0)
    ai.frequency_range(10.93e9, 11.03e9)
    ai.num_points(3201)
    testscan=ai.freq_sweep()
    print len(testscan)
    xx=testscan[0].asarray
    print xx
    yytemp=testscan[1].asarray[0]
    print yytemp
    yy=np.square(np.abs(yytemp))
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
    plot(make.curve(xx*1e-9, 10*np.log10(yy), color="b")#,
#         make.curve(xx*2e-9, 10*np.log10(yy), color="g"),
#         make.curve(x, sin(2*y), color="r"),
#         make.merror(x, y/2, dy),
#         make.label("PNA SCAN<b>test</b>",
#                    (xx[0], yy[0]), (-10, -10), "BR"),
#         make.label("PNA SCAN<b>test 2X</b>",
#                    (xx[0], yy[0]), (-10, -10), "BR"),
#         make.label("Relative position <i>inside</i>",
#                    (x[0], y[0]), (10, 10), "TL"),
#         make.label("Absolute position", "R", (0,0), "R"),
#         make.legend("TR")
#         make.marker(position=(5., .8), label_cb=lambda xx, yy: u"A = %.2f" % xx,
#                     markerstyle="|", movable=False)
         )

if __name__ == "__main__":
    test()