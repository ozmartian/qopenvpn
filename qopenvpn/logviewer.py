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

        self.proc = QtCore.QProcess()
        self.proc.setProcessEnvironment(QtCore.QProcessEnvironment.systemEnvironment())
        self.proc.setProcessChannelMode(self.proc.MergedChannels)

        # force dialog to open centered on currently active screen
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(),
                                                      QtWidgets.qApp.desktop().availableGeometry()))

    def cmdexec(self, command, output=False):
        if self.proc.state() == self.proc.NotRunning:
            self.proc.start(' '.join(command))
            self.proc.waitForFinished(-1)
            if self.proc.exitStatus() == self.proc.NormalExit:
                if output:
                    cmdout = str(self.proc.readAllStandardOutput().data(), 'utf-8')
                    return self.proc.exitCode(), cmdout
                else:
                    return self.proc.exitCode()
            else:
                return 1, self.proc.errorString()
        return 1

    def journalctl(self, disable_sudo=False):
        """Run journalctl command and get OpenVPN logs"""
        settings = QtCore.QSettings()
        cmdline = []
        if not disable_sudo and settings.value("use_sudo", type=bool):
            cmdline.append(settings.value("sudo_command") or "sudo")
        cmdline.extend([
            "journalctl", "-b", "-u",
            "{}@{}".format(settings.value("service_name"), settings.value("vpn_name"))
        ])
        result = self.cmdexec(cmdline, output=True)
        return result[1]

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
        self.logViewerEdit.setPlainText(self.journalctl(disable_sudo=True))
        QtCore.QTimer.singleShot(0, self.refresh_timeout)

    def refresh_timeout(self):
        """Move scrollbar to bottom and refresh IP address
        (must be called by single shot timer or else scrollbar sometimes doesn't move)"""
        self.logViewerEdit.verticalScrollBar().setValue(self.logViewerEdit.verticalScrollBar().maximum())
        ip = self.getip()
        self.ipAddressEdit.setText("{} ({})".format(ip[0], ip[1]) if ip[1] else ip[0])
