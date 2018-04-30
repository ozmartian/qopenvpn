#!/usr/bin/env python3
# -*- coding: utf-8

import glob
import os
import subprocess
import sys

from PyQt5 import QtCore, QtWidgets

from qopenvpn.ui_qopenvpnsettings import Ui_QOpenVPNSettings


class QOpenVPNSettings(QtWidgets.QDialog, Ui_QOpenVPNSettings):
    def __init__(self, parent=None, flags=QtCore.Qt.WindowCloseButtonHint):
        super(QOpenVPNSettings, self).__init__(parent, flags)
        self.setupUi(self)

        self.setStyleSheet('''
            QComboBox, QComboBox:on {
              background: #838383;
              color: #FFF;
            }
            QComboBox:on {
              background: #838383;
            }
            QComboBox QAbstractItemView {
              border: 1px solid #838383;
              selection-background-color: #EAEAEA;
              selection-color: #000;
            }
            ''')

        settings = QtCore.QSettings()
        self.autoconnectCheckBox.setChecked(settings.value("auto_connect", False, type=bool))
        self.warningCheckBox.setChecked(settings.value("show_warning", False, type=bool))
        self.showlogCheckBox.setChecked(settings.value("show_log", False, type=bool))

        # Checks for the new location of OpenVPN configuration files introduced in OpenVPN 2.4
        # See https://github.com/OpenVPN/openvpn/blob/master/Changes.rst#user-visible-changes
        # "The configuration files are picked up from the /etc/openvpn/server/ and
        # /etc/openvpn/client/ directories (depending on unit file)."
        # Remove this unaesthetic version check when openvpn 2.4 is widely accepcted
        try:
            output = subprocess.run(["openvpn", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
        except OSError:
            print("An installation of OpenVPN could not be found on your machine!", file=sys.stderr)
            output = ""

        # Take second tuple of version output (i.e. `2.4.0`)
        # and extract its major and minor components (i.e. 2 and 4)
        # noinspection PyUnresolvedReferences
        output = output.decode()
        version_string = output.split()[1] if output else ""
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
            self.initialVPN = self.vpnNameComboBox.currentText()

        self.sudoCommandComboBox.addItems(['kdesu', 'kdesudo', 'gksu', 'sudo'])
        self.sudoCommandComboBox.setCurrentText(settings.value("sudo_command"))

        # force dialog to open centered on currently active screen
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(),
                                                      QtWidgets.qApp.desktop().availableGeometry()))

    def accept(self):
        settings = QtCore.QSettings()
        vpnName = self.vpnNameComboBox.currentText()
        settings.setValue("vpn_name", vpnName)
        settings.setValue("auto_connect", self.autoconnectCheckBox.isChecked())
        settings.setValue("show_log", self.showlogCheckBox.isChecked())
        settings.setValue("show_warning", self.warningCheckBox.isChecked())
        settings.setValue("sudo_command", self.sudoCommandComboBox.currentText())
        if vpnName != self.initialVPN:
            self.parent.vpn_changed = True
        super(QOpenVPNSettings, self).accept()
