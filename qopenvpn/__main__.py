#!/usr/bin/env python3
# -*- coding: utf-8

import glob
import os
import signal
import socket
import subprocess
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from qopenvpn import notify, stun
from qopenvpn.ui_qopenvpnlogviewer import Ui_QOpenVPNLogViewer
from qopenvpn.ui_qopenvpnsettings import Ui_QOpenVPNSettings


# Allow CTRL+C and/or SIGTERM to kill us (PyQt blocks it otherwise)
signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, signal.SIG_DFL)


class QOpenVPNSettings(QtWidgets.QDialog, Ui_QOpenVPNSettings):
    def __init__(self, parent=None, flags=QtCore.Qt.WindowCloseButtonHint):
        super(QOpenVPNSettings, self).__init__(parent, flags)
        self.setupUi(self)

        settings = QtCore.QSettings()
        self.sudoCommandEdit.setText(settings.value("sudo_command") or "kdesu")
        self.sudoCheckBox.setChecked(settings.value("use_sudo", False, type=bool))
        self.warningCheckBox.setChecked(settings.value("show_warning", False, type=bool))
        self.showlogCheckBox.setChecked(settings.value("show_log", False, type=bool))

        # Checks for the new location of OpenVPN configuration files introduced in OpenVPN 2.4
        # See https://github.com/OpenVPN/openvpn/blob/master/Changes.rst#user-visible-changes
        # "The configuration files are picked up from the /etc/openvpn/server/ and
        # /etc/openvpn/client/ directories (depending on unit file)."
        # Remove this unaesthetic version check when openvpn 2.4 is widely accepcted
        try:
            output = subprocess.check_output(["/usr/bin/env", "openvpn", "--version"])
        except subprocess.CalledProcessError as e:
            output = e.output
        except OSError:
            print("An installation of OpenVPN could not be found on your machine!", file=sys.stderr)
            output = ""

        # Take second tuple of version output (i.e. `2.4.0`)
        # and extract its major and minor components (i.e. 2 and 4)
        version_string = output.decode("utf8").split()[1] if output else ""
        version_components = version_string.split(".")
        if len(version_components) >= 2:
            major, minor = version_components[0:2]
            major = int(major)
            minor = int(minor)
        else:
            print("Couldn't determine the installed OpenVPN version, assuming v0.0", file=sys.stderr)
            major = minor = 0

        # Matches version 2.4.x or greater
        if major >= 2 and minor >= 4:
            settings.setValue("config_location", "/etc/openvpn/client/*.conf")
            settings.setValue("service_name", "openvpn-client")
        else:
            settings.setValue("config_location", "/etc/openvpn/*.conf")
            settings.setValue("service_name", "openvpn")

        # Fill VPN combo box with .conf files from /etc/openvpn{,/client}
        for f in sorted(glob.glob(settings.value("config_location"))):
            vpn_name = os.path.splitext(os.path.basename(f))[0]
            self.vpnNameComboBox.addItem(vpn_name)

        i = self.vpnNameComboBox.findText(settings.value("vpn_name"))
        if i > -1:
            self.vpnNameComboBox.setCurrentIndex(i)

        # force dialog to open centered on currently active screen
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(),
                                                      QtWidgets.qApp.desktop().availableGeometry()))

    def accept(self):
        settings = QtCore.QSettings()
        settings.setValue("sudo_command", self.sudoCommandEdit.text())
        settings.setValue("use_sudo", self.sudoCheckBox.isChecked())
        settings.setValue("show_warning", self.warningCheckBox.isChecked())
        settings.setValue("vpn_name", self.vpnNameComboBox.currentText())
        settings.setValue("show_log", self.showlogCheckBox.isChecked())
        QtWidgets.QDialog.accept(self)


class QOpenVPNLogViewer(QtWidgets.QDialog, Ui_QOpenVPNLogViewer):
    def __init__(self, parent=None, flags=QtCore.Qt.WindowCloseButtonHint):
        super(QOpenVPNLogViewer, self).__init__(parent, flags)
        self.setupUi(self)
        self.refreshButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.refreshButton.clicked.connect(self.refresh)
        self.refresh()

        # force dialog to open centered on currently active screen
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(),
                                                      QtWidgets.qApp.desktop().availableGeometry()))

    @staticmethod
    def journalctl(disable_sudo=False):
        """Run journalctl command and get OpenVPN logs"""
        settings = QtCore.QSettings()
        cmdline = []
        if not disable_sudo and settings.value("use_sudo", type=bool):
            cmdline.append(settings.value("sudo_command") or "sudo")
        cmdline.extend([
            "journalctl", "-b", "-u",
            "{}@{}".format(settings.value("service_name"), settings.value("vpn_name"))
        ])
        try:
            output = subprocess.check_output(cmdline)
        except subprocess.CalledProcessError as e:
            output = e.output
        return output

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

    def refresh(self):
        """Refresh logs"""
        self.logViewerEdit.setPlainText(self.journalctl(disable_sudo=True).decode("utf8"))
        QtCore.QTimer.singleShot(0, self.refresh_timeout)

    def refresh_timeout(self):
        """Move scrollbar to bottom and refresh IP address
        (must be called by single shot timer or else scrollbar sometimes doesn't move)"""
        self.logViewerEdit.verticalScrollBar().setValue(self.logViewerEdit.verticalScrollBar().maximum())
        ip = self.getip()
        self.ipAddressEdit.setText("{} ({})".format(ip[0], ip[1]) if ip[1] else ip[0])


class QOpenVPNWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QOpenVPNWidget, self).__init__(parent)
        self.vpn_enabled = False
        self.connected = None

        # intialize D-Bus notification daemon
        notify.init(QtWidgets.qApp.applicationName(), mainloop='qt')

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
            self.trayIcon.setToolTip('CONNECTED<br/>since %s' % self.connected)
            self.startAction.setVisible(False)
            self.stopAction.setVisible(True)
            self.vpn_enabled = True
        else:
            self.trayIcon.setIcon(self.iconDisabled)
            self.trayIcon.setToolTip('DISCONNECTED')
            self.startAction.setVisible(True)
            self.stopAction.setVisible(False)

            if not disable_warning and settings.value("show_warning", type=bool) and self.vpn_enabled:
                QtWidgets.QMessageBox.warning(self, self.tr("QOpenVPN - Warning"),
                                              self.tr("You have been disconnected from VPN!"))
            self.vpn_enabled = False

    def systemctl(self, command, disable_sudo=False, quiet=False):
        """Run systemctl command"""
        settings = QtCore.QSettings()
        cmdline = []
        if not disable_sudo and settings.value("use_sudo", type=bool):
            cmdline.append(settings.value("sudo_command") or "sudo")
        cmdline.extend([
            "systemctl", command,
            "{}@{}".format(settings.value("service_name"), settings.value("vpn_name"))
        ])
        stdout = stderr = subprocess.DEVNULL if quiet else None
        return subprocess.call(cmdline, stdout=stdout, stderr=stderr)

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
        self.notify('QOpenVPN', 'Disconnecting from %s' % settings.value("vpn_name"),
                    "{}/openvpn_disabled.svg".format(self.imgpath))
        if retcode == 0:
            self.connected = None
            self.update_status(disable_warning=True)

    def vpn_status(self):
        """Check if OpenVPN service is running"""
        retcode = self.systemctl("is-active", disable_sudo=True, quiet=True)
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
        dialog = QOpenVPNLogViewer(self)
        dialog.exec_()

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
        if self.vpn_enabled:
            reply = QtWidgets.QMessageBox.question(
                self, self.tr("QOpenVPN - Quit"),
                self.tr("You are still connected to VPN! Do you really want to quit "
                        "QOpenVPN GUI (OpenVPN service will keep running in background)?"),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
            )
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
    w = QOpenVPNWidget()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
