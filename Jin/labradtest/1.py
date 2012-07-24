#!/usr/bin/env python
# Copyright (c) 2008 Qtrac Ltd. All rights reserved.
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later version. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future_builtins import *

import re
from PyQt4.QtCore import (Qt, SIGNAL, pyqtSignature)
from PyQt4.QtGui import (QApplication, QDialog)
from PyQt4 import QtCore, QtGui
import ui_1

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False


class test(QDialog,
        ui_1.Ui_MainWindow):

    def __init__(self, text, parent=None):
        super(test, self).__init__(parent)
        self.__text = unicode(text)
        self.__index = 0
        self.setupUi(self)
        if not MAC:
            print ('ok')
#            self.findButton.setFocusPolicy(Qt.NoFocus)
#            self.replaceButton.setFocusPolicy(Qt.NoFocus)
#            self.replaceAllButton.setFocusPolicy(Qt.NoFocus)
#            self.closeButton.setFocusPolicy(Qt.NoFocus)
        self.updateUi()


    @pyqtSignature("QString")
    def on_findLineEdit_textEdited(self, text):
        self.__index = 0
        self.updateUi()


    def makeRegex(self):
        findText = unicode(self.findLineEdit.text())
        if unicode(self.syntaxComboBox.currentText()) == "Literal":
            findText = re.escape(findText)
        flags = re.MULTILINE|re.DOTALL|re.UNICODE
        if not self.caseCheckBox.isChecked():
            flags |= re.IGNORECASE
        if self.wholeCheckBox.isChecked():
            findText = r"\b{0}\b".format(findText)
        return re.compile(findText, flags)


    @pyqtSignature("")
    def on_pushButton_clicked(self):
        print ('push me!!!')
        self.textEdit.setHtml(QtGui.QApplication.translate("MainWindow", "\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:15pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:25pt;\">dddddddddddd</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        
    @pyqtSignature("")
    def on_replaceButton_clicked(self):
        regex = self.makeRegex()
        self.__text = regex.sub(unicode(self.replaceLineEdit.text()),
                                self.__text, 1)
        

    @pyqtSignature("")
    def on_replaceAllButton_clicked(self):
        regex = self.makeRegex()
        self.__text = regex.sub(unicode(self.replaceLineEdit.text()),
                                self.__text)
        

    def updateUi(self):
        print('OK')
#        enable = not self.findLineEdit.text().isEmpty()
#        self.findButton.setEnabled(enable)
#        self.replaceButton.setEnabled(enable)
#        self.replaceAllButton.setEnabled(enable)


    def text(self):
        return self.__text


if __name__ == "__main__":
    import sys

    text = """US experience shows that, unlike traditional patents,
software patents do not encourage innovation and R&D, quite the
contrary. In particular they hurt small and medium-sized enterprises
and generally newcomers in the market. They will just weaken the market
and increase spending on patents and litigation, at the expense of
technological innovation and research. Especially dangerous are
attempts to abuse the patent system by preventing interoperability as a
means of avoiding competition with technological ability.
--- Extract quoted from Linus Torvalds and Alan Cox's letter
to the President of the European Parliament
http://www.effi.org/patentit/patents_torvalds_cox.html"""

    def found(where):
        print("Found at {0}".format(where))

    def nomore():
        print("No more found")

    app = QApplication(sys.argv)
    form = test(text)
    #form.connect(form, SIGNAL("found"), found)
    #form.connect(form, SIGNAL("notfound"), nomore)
    form.show()
    app.exec_()
    print(form.text())

