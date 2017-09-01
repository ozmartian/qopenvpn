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
        self.connected = None

        # intialize D-Bus notification daemon
        notify.init(QtWidgets.qApp.applicationName())

        self.proc = QtCore.QProcess()
        self.proc.setProcessEnvironment(QtCore.QProcessEnvironment.systemEnvironment())
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.imgpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')

        self.trayIcon = QtWidgets.QSystemTrayIcon(self)
        self.trayIconMenu = QtWidgets.QMenu(self)

        self.create_icon()
        self.create_actions()
        self.create_menu()
        self.update_status()

        # Update status every 10 seconds
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)

        # Setup system tray icon doubleclick timer
        self.icon_doubleclick_timer = QtCore.QTimer(self)
        self.icon_doubleclick_timer.setSingleShot(True)
        self.icon_doubleclick_timer.timeout.connect(self.icon_doubleclick_timeout)

        self.setMouseTracking(True)
        self.installEventFilter(self)

    def create_actions(self):
        """Create actions and connect relevant signals"""
        self.startAction = QtWidgets.QAction(self.iconActive, self.tr("&Start"), self)
        self.startAction.triggered.connect(self.vpn_start)
        self.stopAction = QtWidgets.QAction(self.iconDisabled, self.tr("S&top"), self)
        self.stopAction.triggered.connect(self.vpn_stop)
        self.settingsAction = QtWidgets.QAction(self.iconSettings, self.tr("S&ettings..."), self)
        self.settingsAction.triggered.connect(self.settings)
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

    def update_status(self, disable_warning=False):
        """Update GUI according to OpenVPN status"""
        settings = QtCore.QSettings()
        vpn_status = self.vpn_status()
        if vpn_status:
            self.trayIcon.setIcon(self.iconActive)
            tooltip = 'CONNECTED'
            if self.connected is not None:
                tooltip += '<font size="-1">since %s</font>' % self.connected
            self.trayIcon.setToolTip(tooltip)
            self.startAction.setVisible(False)
            self.stopAction.setVisible(True)
            self.vpn_enabled = True
        else:
            self.trayIcon.setIcon(self.iconDisabled)
            self.trayIcon.setToolTip('DISCONNECTED')
            self.startAction.setVisible(True)
            self.stopAction.setVisible(False)

            if not disable_warning and settings.value("show_warning", type=bool) and self.vpn_enabled:
                QtWidgets.QMessageBox.warning(self, self.tr("QOpenVPN - Warning"), self.tr("OpenVPN was disconnected!"))
            self.vpn_enabled = False

    def cmdexec(self, command, output=False):
        if self.proc.state() == QtCore.QProcess.NotRunning:
            self.proc.start(' '.join(command))
            self.proc.waitForFinished(-1)
            if self.proc.exitStatus() == QtCore.QProcess.NormalExit:
                if output:
                    cmdout = str(self.proc.readAllStandardOutput().data(), 'utf-8')
                    return self.proc.exitCode(), cmdout
                else:
                    return self.proc.exitCode()
            else:
                return 1, self.proc.errorString()
        return 1

    def systemctl(self, command, disable_sudo=False):
        """Run systemctl command"""
        settings = QtCore.QSettings()
        cmdline = []
        if not disable_sudo and settings.value("use_sudo", type=bool):
            cmdline.append(settings.value("sudo_command") or "sudo")
        cmdline.extend([
            "systemctl", command,
            "{}@{}".format(settings.value("service_name"), settings.value("vpn_name"))
        ])
        # stdout = stderr = subprocess.DEVNULL if quiet else None
        # return subprocess.call(cmdline, stdout=stdout, stderr=stderr)
        return self.cmdexec(cmdline)

    def vpn_start(self):
        """Start OpenVPN service"""
        settings = QtCore.QSettings()
        retcode = self.systemctl("start")
        self.notify('QOpenVPN', 'Connecting to %s' % settings.value("vpn_name"),
                    "{}/openvpn.svg".format(self.imgpath))
        if settings.value("show_log", False, type=bool):
            self.logs()
        if retcode == 0:
            self.connected = QtCore.QTime().currentTime().toString('HH:mm')
            self.update_status()

    def vpn_stop(self):
        """Stop OpenVPN service"""
        settings = QtCore.QSettings()
        retcode = self.systemctl("stop")
        self.notify('QOpenVPN', 'Disconnected from %s' % settings.value("vpn_name"),
                    "{}/openvpn_disabled.svg".format(self.imgpath))
        if retcode == 0:
            self.connected = None
            self.update_status(disable_warning=True)

    def vpn_status(self):
        """Check if OpenVPN service is running"""
        retcode = self.systemctl("is-active", disable_sudo=True)
        return retcode == 0

    def settings(self):
        """Show settings dialog"""
        dialog = QOpenVPNSettings(self)
        if dialog.exec_() and self.vpn_enabled:
            self.vpn_stop()
            self.vpn_start()

    @staticmethod
    def notify(title, msg, icon='', urgency=1):
        notification = notify.Notification(title, msg, icon)
        notification.set_urgency(urgency)
        return notification.show()

    def logs(self):
        """Show log viewer dialog"""
        logsThread = QtCore.QThread(self)
        logsWorker = QOpenVPNLogViewer()
        logsWorker.moveToThread(logsThread)
        logsThread.started.connect(logsWorker.refresh)
        logsThread.finished.connect(logsThread.deleteLater, QtCore.Qt.DirectConnection)
        logsThread.start()
        logsWorker.exec_()

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
