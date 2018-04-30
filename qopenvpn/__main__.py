#!/usr/bin/env python3
# -*- coding: utf-8

import os
import signal
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from qopenvpn import notify
from qopenvpn.logviewer import QOpenVPNLogViewer
from qopenvpn.settings import QOpenVPNSettings

# Allow CTRL+C and/or SIGTERM to kill us (PyQt blocks it otherwise)
signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, signal.SIG_DFL)


class QOpenVPNWidget(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(QOpenVPNWidget, self).__init__(parent)
        self.vpn_enabled = False
        self.vpn_changed = False
        self.first_run = True
        self.connected = None

        self.settings = QtCore.QSettings()

        # intialize D-Bus notification daemon
        notify.init(QtWidgets.qApp.applicationName())

        self.imgpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')

        self.trayIcon = QtWidgets.QSystemTrayIcon(self)
        self.trayIconMenu = QtWidgets.QMenu(self)

        self.create_icon()
        self.create_actions()
        self.create_menu()
        self.vpn_status()

        # Update status every 10 seconds
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.vpn_status)
        self.timer.start(5000)

        # Setup system tray icon doubleclick timer
        self.icon_doubleclick_timer = QtCore.QTimer(self)
        self.icon_doubleclick_timer.setSingleShot(True)
        self.icon_doubleclick_timer.timeout.connect(self.icon_doubleclick_timeout)

        self.setMouseTracking(True)
        self.installEventFilter(self)

    def create_actions(self):
        """Create actions and connect relevant pyqtSignals"""
        self.startAction = QtWidgets.QAction(self.iconActive, self.tr("&Start"), self)
        self.startAction.triggered.connect(self.vpn_start)
        self.stopAction = QtWidgets.QAction(self.iconDisabled, self.tr("S&top"), self)
        self.stopAction.triggered.connect(self.vpn_stop)
        self.settingsAction = QtWidgets.QAction(self.iconSettings, self.tr("S&ettings..."), self)
        self.settingsAction.triggered.connect(self.show_settings)
        self.logsAction = QtWidgets.QAction(self.iconLogs, self.tr("View &logs"), self)
        self.logsAction.triggered.connect(self.logs)
        self.quitAction = QtWidgets.QAction(self.iconQuit, self.tr("&Quit"), self)
        self.quitAction.triggered.connect(self.quit)

    def create_menu(self):
        """Create menu and add items to it"""
        self.trayIconMenu.addAction(self.startAction)
        self.trayIconMenu.addAction(self.stopAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.settingsAction)
        self.trayIconMenu.addAction(self.logsAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addAction(self.quitAction)

    def create_icon(self):
        """Create system tray icon"""
        # Workaround for Plasma 5 not showing SVG icons
        self.iconActive = QtGui.QIcon("{}/openvpn.svg".format(self.imgpath))
        self.iconActive = QtGui.QIcon(self.iconActive.pixmap(128, 128))
        self.iconDisabled = QtGui.QIcon("{}/openvpn_disabled.svg".format(self.imgpath))
        self.iconDisabled = QtGui.QIcon(self.iconDisabled.pixmap(128, 128))
        self.iconSettings = QtGui.QIcon("{}/settings.svg".format(self.imgpath))
        self.iconSettings = QtGui.QIcon(self.iconSettings.pixmap(32, 32))
        self.iconLogs = QtGui.QIcon("{}/logs.svg".format(self.imgpath))
        self.iconLogs = QtGui.QIcon(self.iconLogs.pixmap(32, 32))
        self.iconQuit = QtGui.QIcon("{}/exit.svg".format(self.imgpath))
        self.iconQuit = QtGui.QIcon(self.iconQuit.pixmap(32, 32))
        self.trayIcon.activated.connect(self.icon_activated)
        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.trayIcon.setIcon(self.iconDisabled)
        self.trayIcon.setToolTip("QOpenVPN")
        self.trayIcon.show()

    def cmdexec(self, command, callback, disable_warning=False):
        self.proc = QtCore.QProcess(self)
        self.proc.setProcessEnvironment(QtCore.QProcessEnvironment.systemEnvironment())
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        if self.proc.state() == QtCore.QProcess.NotRunning:
            if disable_warning:
                self.proc.finished.connect(lambda code, status: callback(code, status, disable_warning))
            else:
                self.proc.finished.connect(callback)
            self.proc.start(' '.join(command))

    def systemctl(self, command, callback, disable_sudo=False, disable_warning=False):
        """Run systemctl command"""
        cmdline = []
        if not disable_sudo:
            cmdline.append(self.settings.value("sudo_command"))
        cmdline.extend([
            "systemctl", command,
            "{}@{}".format(self.settings.value("service_name"), self.settings.value("vpn_name"))
        ])
        self.cmdexec(cmdline, callback, disable_warning)

    def vpn_start(self):
        """Start OpenVPN service"""
        self.systemctl("start", self.on_vpn_start)

    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus)
    def on_vpn_start(self, exitcode, exitstatus):
        if exitstatus == QtCore.QProcess.NormalExit:
            self.notify('QOpenVPN', 'Connecting to %s' % self.settings.value("vpn_name"),
                        "{}/openvpn.svg".format(self.imgpath))
            if self.settings.value("show_log", False, type=bool):
                self.logs()
            if exitcode == 0:
                self.connected = QtCore.QTime().currentTime().toString('HH:mm:ss')
                self.vpn_status()

    def vpn_stop(self):
        """Stop OpenVPN service"""
        self.systemctl("stop", self.on_vpn_stop)

    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus)
    def on_vpn_stop(self, exitcode, exitstatus):
        if exitstatus == QtCore.QProcess.NormalExit:
            self.notify('QOpenVPN', 'Disconnected from %s' % self.settings.value("vpn_name"),
                        "{}/openvpn_disabled.svg".format(self.imgpath))
            if exitcode == 0:
                self.connected = None
                self.vpn_status(disable_warning=True)

    def vpn_status(self, disable_warning=False):
        """Check if OpenVPN service is running"""
        self.systemctl("is-active", self.on_vpn_status, disable_sudo=True, disable_warning=disable_warning)

    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus)
    @QtCore.pyqtSlot(int, QtCore.QProcess.ExitStatus, bool)
    def on_vpn_status(self, exitcode, exitstatus, disable_warning=False):
        if exitstatus == QtCore.QProcess.NormalExit:
            if exitcode == 0:
                self.trayIcon.setIcon(self.iconActive)
                tooltip = 'CONNECTED'
                tooltip += '<br/><font size="-1">to <b>{}</b></font>'.format(self.settings.value("vpn_name"))
                if self.connected is not None:
                    tooltip += '<br/><font size="-1">since {}</font>'.format(self.connected)
                self.trayIcon.setToolTip(tooltip)
                self.startAction.setVisible(False)
                self.stopAction.setVisible(True)
                self.vpn_enabled = True
            else:
                self.trayIcon.setIcon(self.iconDisabled)
                self.trayIcon.setToolTip('DISCONNECTED')
                self.startAction.setVisible(True)
                self.stopAction.setVisible(False)
                if not disable_warning and bool(self.settings.value("show_warning")) and self.vpn_enabled:
                    QtWidgets.QMessageBox.warning(self, self.tr("Warning"), self.tr("OpenVPN was disconnected!"))
                self.vpn_enabled = False
        if self.first_run and not self.vpn_enabled and self.settings.value("auto_connect", type=bool):
            self.startAction.trigger()
        self.first_run = False

    def show_settings(self):
        """Show show_settings dialog"""
        dialog = QOpenVPNSettings(self)
        if dialog.exec_():
            if self.vpn_changed and self.vpn_enabled:
                self.vpn_stop()
                self.vpn_start()
                self.vpn_changed = False

    @staticmethod
    def notify(title, msg, icon='', urgency=1):
        notification = notify.Notification(title, msg, icon)
        notification.set_urgency(urgency)
        return notification.show()

    def logs(self):
        logviewer = QOpenVPNLogViewer(self)
        logviewer.exec_()

    def icon_activated(self, reason):
        """Start or stop OpenVPN by double-click on tray icon"""
        if reason == QtWidgets.QSystemTrayIcon.Trigger or reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            if self.icon_doubleclick_timer.isActive():
                self.icon_doubleclick_timer.stop()
                if self.vpn_enabled:
                    self.vpn_stop()
                else:
                    self.vpn_start()
            else:
                self.icon_doubleclick_timer.start(QtWidgets.QApplication.doubleClickInterval())

    def icon_doubleclick_timeout(self):
        """Action performed after single-click on tray icon"""
        pass

    def quit(self):
        """Quit QOpenVPN GUI (and ask before quitting if OpenVPN is still running)"""
        # noinspection PyCallByClass
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter,
                                                      QtWidgets.QMessageBox.sizeHint(self),
                                                      QtWidgets.qApp.desktop().availableGeometry()))
        if self.vpn_enabled:
            reply = QtWidgets.QMessageBox.warning(self,
                                                  self.tr("QOpenVPN - Quit"),
                                                  self.tr("You are still connected to VPN! Do you really want to quit "
                                                          "(OpenVPN service will keep running in the background)?"),
                                                  QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                  QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                QtWidgets.QApplication.quit()
        else:
            QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("QOpenVPN")
    app.setOrganizationDomain("qopenvpn.eutopia.cz")
    app.setApplicationName("QOpenVPN")
    app.setQuitOnLastWindowClosed(False)
    # noinspection PyUnusedLocal
    w = QOpenVPNWidget()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
