# -*- coding: utf-8 -*-
"""
ChatGISBot QGIS Plugin
"""

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
import os.path

from .resources import *
from .chatgisbot_dialog import ChatGISBotDialog


class ChatGISBot:
    """QGIS Plugin implementation."""

    def __init__(self, iface):
        """Plugin constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Localization
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            "i18n",
            f"ChatGISBot_{locale}.qm"
        )

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr("&ChatGISBot")
        self.first_start = True
        self.dlg = None

    def tr(self, message):
        """Translate message using Qt translation system."""
        return QCoreApplication.translate("ChatGISBot", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        """Add an action to the QGIS interface."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip:
            action.setStatusTip(status_tip)
        if whats_this:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create menu entry and toolbar icon."""
        icon_path = ":/plugins/chatgisbot/icon.png"
        self.add_action(
            icon_path,
            text=self.tr("Chat GIS Bot"),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def unload(self):
        """Remove plugin menu and toolbar icons."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Open the ChatGISBot dialog."""
        if self.first_start:
            self.first_start = False
            self.dlg = ChatGISBotDialog(self.iface)

        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
