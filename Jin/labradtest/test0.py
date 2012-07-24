# -*- coding: utf-8 -*-
from PyQt4.QtGui import QVBoxLayout, QDialog
from PyQt4.QtCore import Qt
from guiqwt.plot import CurveWidget, PlotManager
from guiqwt.builder import make
from guiqwt.tools import SelectTool
from guiqwt.events import ClickHandler
from guiqwt.signals import SIG_CLICK_EVENT

import numpy as np

class MyTool(SelectTool):
    def setup_filter(self, baseplot):
        start_state = SelectTool.setup_filter(self, baseplot)
        self.click = ClickHandler(baseplot.filter, Qt.LeftButton,
                                   mods=Qt.ShiftModifier, start_state=start_state)
        self.connect(self.click, SIG_CLICK_EVENT, self.dce)
        return start_state

    def dce(self, filter, evt):
        print evt.pos()
        plot = filter.plot
        rct = plot.contentsRect()
        print "Rect:", rct
        print "X:", plot.invTransform(self.curve_item.xAxis(), evt.x()-rct.left())
        print "Y:", plot.invTransform(self.curve_item.yAxis(), evt.y()-rct.top())
        print

class TestDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.widget = CurveWidget()
        self.curve_item = make.curve([], [], color='r')
        self.widget.plot.add_item(self.curve_item)
        self.pm = PlotManager(self.widget)
        self.pm.add_plot(self.widget.plot)
        t = self.pm.add_tool(MyTool)
        t.curve_item = self.curve_item
        self.pm.set_default_tool(t)
        t.activate()
        self.layout().addWidget(self.widget)
        self.update_curve()

    def update_curve(self):
        x = np.arange(0,10,.1)
        y = np.sin(np.sin(x))
        self.curve_item.set_data(x, y)
        self.curve_item.plot().replot()

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    win = TestDialog()
    win.show()
    app.exec_()
