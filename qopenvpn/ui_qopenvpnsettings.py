# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'qopenvpnsettings.ui'
#
# Created by: PyQt5 UI code generator 5.8.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtWidgets


class Ui_QOpenVPNSettings(object):
    def setupUi(self, QOpenVPNSettings):
        QOpenVPNSettings.setObjectName("QOpenVPNSettings")
        QOpenVPNSettings.resize(265, 262)
        topLayout = QtWidgets.QVBoxLayout(QOpenVPNSettings)
        topLayout.setObjectName("topLayout")
        self.label = QtWidgets.QLabel(QOpenVPNSettings)
        self.label.setObjectName("label")
        topLayout.addWidget(self.label)
        self.vpnNameComboBox = QtWidgets.QComboBox(QOpenVPNSettings)
        self.vpnNameComboBox.setObjectName("vpnNameComboBox")
        self.vpnNameComboBox.setCursor(QtCore.Qt.PointingHandCursor)
        self.vpnNameComboBox.setMaxVisibleItems(6)
        topLayout.addWidget(self.vpnNameComboBox)
        self.autoconnectCheckBox = QtWidgets.QCheckBox(QOpenVPNSettings)
        self.autoconnectCheckBox.setObjectName("autoconnectCheckBox")
        self.autoconnectCheckBox.setCursor(QtCore.Qt.PointingHandCursor)
        # self.autoconnectCheckBox.setStyleSheet('margin-top: 10px;')
        topLayout.addWidget(self.autoconnectCheckBox)
        self.showlogCheckBox = QtWidgets.QCheckBox(QOpenVPNSettings)
        self.showlogCheckBox.setObjectName("showlogCheckBox")
        self.showlogCheckBox.setCursor(QtCore.Qt.PointingHandCursor)
        topLayout.addWidget(self.showlogCheckBox)
        self.warningCheckBox = QtWidgets.QCheckBox(QOpenVPNSettings)
        self.warningCheckBox.setObjectName("warningCheckBox")
        self.warningCheckBox.setCursor(QtCore.Qt.PointingHandCursor)
        topLayout.addWidget(self.warningCheckBox)
        groupbox1 = QtWidgets.QGroupBox()
        groupbox1.setLayout(topLayout)
        self.label_2 = QtWidgets.QLabel(QOpenVPNSettings)
        self.label_2.setObjectName("label_2")
        self.sudoCommandComboBox = QtWidgets.QComboBox(QOpenVPNSettings)
        self.sudoCommandComboBox.setObjectName("sudoCommandComboBox")
        self.sudoCommandComboBox.setCursor(QtCore.Qt.PointingHandCursor)
        bottomLayout = QtWidgets.QVBoxLayout(QOpenVPNSettings)
        bottomLayout.addWidget(self.label_2)
        bottomLayout.addWidget(self.sudoCommandComboBox)
        bottomLayout.addItem(QtWidgets.QSpacerItem(1, 10))
        groupbox2 = QtWidgets.QGroupBox(QOpenVPNSettings)
        groupbox2.setLayout(bottomLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(QOpenVPNSettings)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout = QtWidgets.QGridLayout(QOpenVPNSettings)
        self.gridLayout.addWidget(groupbox1, 0, 0)
        self.gridLayout.addWidget(groupbox2, 1, 0)
        self.gridLayout.addItem(QtWidgets.QSpacerItem(1, 10), 2, 0)
        self.gridLayout.addWidget(self.buttonBox, 3, 0)

        self.retranslateUi(QOpenVPNSettings)
        self.buttonBox.accepted.connect(QOpenVPNSettings.accept)
        self.buttonBox.rejected.connect(QOpenVPNSettings.reject)
        QtCore.QMetaObject.connectSlotsByName(QOpenVPNSettings)
        QOpenVPNSettings.setTabOrder(self.vpnNameComboBox, self.autoconnectCheckBox)
        QOpenVPNSettings.setTabOrder(self.autoconnectCheckBox, self.showlogCheckBox)
        QOpenVPNSettings.setTabOrder(self.showlogCheckBox, self.warningCheckBox)
        QOpenVPNSettings.setTabOrder(self.warningCheckBox, self.sudoCommandComboBox)
        QOpenVPNSettings.setTabOrder(self.sudoCommandComboBox, self.buttonBox)

    def retranslateUi(self, QOpenVPNSettings):
        _translate = QtCore.QCoreApplication.translate
        QOpenVPNSettings.setWindowTitle(_translate("QOpenVPNSettings", "QOpenVPN Settings"))
        self.label.setText(_translate("QOpenVPNSettings", "OpenVPN profile:"))
        self.label.setStyleSheet('font-weight: bold;')
        self.label_2.setText(_translate("QOpenVPNSettings", "<i>sudo</i> command:"))
        self.label_2.setStyleSheet('font-weight: bold;')
        self.autoconnectCheckBox.setText(_translate("QOpenVPNSettings", "Auto-connect when started"))
        self.warningCheckBox.setText(_translate("QOpenVPNSettings", "Warn if disconnected"))
        self.showlogCheckBox.setText(_translate("QOpenVPNSettings", "View logs when connecting"))
