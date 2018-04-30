#!/usr/bin/env python3
# -*- coding: utf-8

import socket

from PyQt5 import QtCore, QtWidgets

from qopenvpn import stun
from qopenvpn.ui_qopenvpnlogviewer import Ui_QOpenVPNLogViewer


class QOpenVPNLogViewer(QtWidgets.QDialog, Ui_QOpenVPNLogViewer):
    def __init__(self, parent=None, flags=QtCore.Qt.WindowCloseButtonHint):
        super(QOpenVPNLogViewer, self).__init__(parent, flags)

        self.setupUi(self)
        self.refreshButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.refreshButton.clicked.connect(self.refresh)

        # force dialog to open centered on currently active screen
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(),
                                                      QtWidgets.qApp.desktop().availableGeometry()))
        self.refresh()

    def journalctl(self, disable_sudo=False):
        """Run journalctl command and get OpenVPN logs"""
        self.proc = QtCore.QProcess(self)
        self.proc.setProcessEnvironment(QtCore.QProcessEnvironment.systemEnvironment())
        self.proc.setProcessChannelMode(self.proc.MergedChannels)
        self.proc.finished.connect(self.update_journal)
        if self.proc.state() == self.proc.NotRunning:
            settings = QtCore.QSettings()
            cmdline = []
            if not disable_sudo and settings.value("use_sudo", type=bool):
                cmdline.append(settings.value("sudo_command") or "sudo")
            cmdline.extend([
                "journalctl", "-b", "-u",
                "{}@{}".format(settings.value("service_name"), settings.value("vpn_name"))
            ])
            self.proc.start(' '.join(cmdline))

    # noinspection PyBroadException
    @staticmethod
    def getip():
        """Get external IP address and hostname"""
        try:
            stunclient = stun.StunClient()
            ip, port = stunclient.get_ip()
        except:
            ip = ""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except:
            hostname = ""
        return ip, hostname

    @QtCore.pyqtSlot()
    def refresh(self):
        """Refresh logs"""
        self.journalctl(True)
        QtCore.QTimer.singleShot(0, self.refresh_timeout)

    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus)
    def update_journal(self, exitcode, exitstatus):
        if exitcode == 0 and exitstatus == QtCore.QProcess.NormalExit:
            cmdout = self.proc.readAllStandardOutput().data().decode().strip()
        else:
            cmdout = self.proc.errorString()
        self.logViewerEdit.setPlainText(cmdout)
        self.logViewerEdit.verticalScrollBar().setValue(self.logViewerEdit.verticalScrollBar().maximum())

    def refresh_timeout(self):
        """Move scrollbar to bottom and refresh IP address
        (must be called by single shot timer or else scrollbar sometimes doesn't move)"""
        ip = self.getip()
        self.ipAddressEdit.setText("{} ({})".format(ip[0], ip[1]) if ip[1] else ip[0])

