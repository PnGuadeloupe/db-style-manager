# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DbStyleManager
                                 A QGIS plugin
 Sync styles to Postgis
                              -------------------
        begin                : 2018-05-25
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Etienne Trimaille
        email                : etienne.trimaille@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os.path

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtGui import QAction, QIcon, QInputDialog
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsMapLayerRegistry, QgsMapLayerStyle, QGis, QgsDataSourceURI, QgsMapLayerRegistry, QgsProject
from tools import resources_path, tr


class DbStyleManager:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            os.path.dirname(__file__),
            'i18n',
            'DBStyleManager_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                # noinspection PyArgumentList,PyCallByClass
                QCoreApplication.installTranslator(self.translator)

        self.menu = tr(u'&DB Style Manager')
        self.toolbar = self.iface.addToolBar(u'DbStyleManager')
        self.toolbar.setObjectName(u'DbStyleManager')

        self.action_load_qgis_style_layer = None
        self.action_enable_sync_style = None
        self.action_load_style_legend = None
        self.action_save_style = None
        self.action_save_style_default = None

    def manage_style(self, layers_idx):
        """Slot for layersAdded."""
        s = QSettings()
        enabled = s.value('db_style_manager/load_style_auto', False, bool)
        for layer in layers_idx:
            if enabled and isinstance(layer, QgsVectorLayer):
                self.load_style_from_database(layer)

    # noinspection PyPep8Naming
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Load style auto
        tooltip = tr('Load styles automatically from PostgreSQL')
        icon = resources_path('icon.png')
        self.action_enable_sync_style = QAction(
            QIcon(icon), tr('Load styles automatically'), self.iface.mainWindow())
        self.action_enable_sync_style.setStatusTip(tooltip)
        self.action_enable_sync_style.setWhatsThis(tooltip)
        self.action_enable_sync_style.setCheckable(True)
        self.action_enable_sync_style.setChecked(False)
        self.action_enable_sync_style.triggered.connect(self.enable_load_style)
        self.iface.addPluginToMenu(tr('DB Style Manager'), self.action_enable_sync_style)
        self.toolbar.addAction(self.action_enable_sync_style)

        # Display layer_styles table
        tooltip = tr('Load a style summary from PostgreSQL')
        icon = resources_path('qgis_layer.svg')
        self.action_load_qgis_style_layer = QAction(
            QIcon(icon), tr('Load a style summary from PostgreSQL'), self.iface.mainWindow())
        self.action_load_qgis_style_layer.setStatusTip(tooltip)
        self.action_load_qgis_style_layer.setWhatsThis(tooltip)
        self.action_load_qgis_style_layer.triggered.connect(self.load_qgis_style_layer)
        self.iface.addPluginToMenu(tr('DB Style Manager'), self.action_load_qgis_style_layer)
        self.toolbar.addAction(self.action_load_qgis_style_layer)

        # Crash
        s = QSettings()
        enabled = s.value('db_style_manager/load_style_auto', False, bool)
        self.action_enable_sync_style.setChecked(enabled)

        # Load style legend
        icon = resources_path('icon.png')
        self.action_load_style_legend = QAction(
            QIcon(icon), tr('Reset all styles'), self.iface.legendInterface())
        self.action_load_style_legend.triggered.connect(self.load_style_legend)

        # Save style
        icon = resources_path('icon.png')
        self.action_save_style = QAction(
            QIcon(icon), tr('Save style'), self.iface.legendInterface())
        self.action_save_style.triggered.connect(self.save_current_style)

        # Save style as default
        icon = resources_path('icon.png')
        self.action_save_style_default = QAction(
            QIcon(icon), tr('Save style as default'), self.iface.legendInterface())
        self.action_save_style_default.triggered.connect(self.save_current_style_default)

        self.iface.legendInterface().addLegendLayerAction(
            self.action_save_style, tr('Database Style Manager'), '', QgsMapLayer.VectorLayer, True)
        self.iface.legendInterface().addLegendLayerAction(
            self.action_save_style_default, tr('Database Style Manager'), '', QgsMapLayer.VectorLayer, True)
        self.iface.legendInterface().addLegendLayerAction(
            self.action_load_style_legend, tr('Database Style Manager'), '', QgsMapLayer.VectorLayer, True)

        # noinspection PyArgumentList
        registry = QgsMapLayerRegistry.instance()
        registry.layersAdded.connect(self.manage_style)

        self.enable_load_style()

    def load_qgis_style_layer(self):
        qs = QSettings()
        qs.beginGroup('PostgreSQL/connections')
        names = []
        for k in sorted(qs.allKeys()):
            if '/' in k:
                parts = k.split('/')
                if parts[0] not in names:
                    names.append(parts[0])
        qs.endGroup()

        connection_name, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            'Select Database',
            'List of connections. This tool will create a group with different layers.',
            names,
            0,
            False)

        layers = []

        if not ok:
            # No database selected, we abort
            return

        table_name = 'layer_styles'
        qs.beginGroup('PostgreSQL/connections/' + connection_name)
        credentials = {
            'service': None,
            'host': None,
            'port': None,
            'database': None,
            'username': None,
            'password': None,
        }

        for k in sorted(qs.allKeys()):
            if k in credentials.keys():
                credentials[k] = qs.value(k)
        qs.endGroup()

        is_host = credentials['host'] != ''
        uri = QgsDataSourceURI()
        if is_host:
            uri.setConnection(credentials['host'], credentials['port'], credentials['database'], credentials['username'], credentials['password'], QgsDataSourceURI.SSLdisable, '')
        else:
            uri.setConnection(credentials['service'], credentials['database'],  credentials['username'], credentials['password'], QgsDataSourceURI.SSLdisable, '')

        # QGIS Layer styles table
        uri.setDataSource('public', table_name, None, '', 'id')
        vlayer = QgsVectorLayer(uri.uri(False), table_name, 'postgres')
        if vlayer.isValid():
            layers.append(vlayer)

        # Summary
        sql = """\
(SELECT
 layer_styles.f_table_schema,
 layer_styles.f_table_name,
 bool_or(layer_styles.useasdefault) AS has_a_default,
 count(*) AS nb_styles
 FROM public.layer_styles
 GROUP BY layer_styles.f_table_schema, layer_styles.f_table_name)""".replace('\n', '')
        uri.setDataSource('', sql, None, '', 'f_table_schema,f_table_name')
        layer = QgsVectorLayer(uri.uri(), 'Summary existing styles', 'postgres')
        if layer.isValid():
            layers.append(layer)

        # Orphaned styles
        sql = """\
(SELECT
 layer_styles.f_table_schema::text,
 layer_styles.f_table_name::text
 FROM public.layer_styles
 GROUP BY layer_styles.f_table_schema, layer_styles.f_table_name
 EXCEPT (
 SELECT
 pg_tables.schemaname AS f_table_schema,
 pg_tables.tablename AS f_table_name
 FROM pg_tables
 WHERE pg_tables.schemaname NOT IN ('pg_catalog', 'information_schema')))""".replace('\n', '')
        uri.setDataSource('', sql, None, '', 'f_table_schema,f_table_name')
        layer = QgsVectorLayer(uri.uri(), 'Orphaned styles', 'postgres')
        if layer.isValid():
            layers.append(layer)

        # Missing styles
        sql = """\
(SELECT
 pg_tables.schemaname::text AS f_table_schema,
 pg_tables.tablename::text AS f_table_name
 FROM pg_tables
 WHERE pg_tables.schemaname NOT IN ('pg_catalog', 'information_schema')
 EXCEPT
 (
 SELECT
 layer_styles.f_table_schema,
 layer_styles.f_table_name
 FROM public.layer_styles
 GROUP BY layer_styles.f_table_schema, layer_styles.f_table_name
 )
 )""".replace('\n', '')
        uri.setDataSource('', sql, None, '', 'f_table_schema,f_table_name')
        layer = QgsVectorLayer(uri.uri(), 'Missing styles', 'postgres')
        if layer.isValid():
            layers.append(layer)

        # Add all layers to a group
        root = QgsProject.instance().layerTreeRoot()
        group_analysis = root.insertGroup(0, connection_name)
        for layer in layers:
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            group_analysis.addLayer(layer)

    def save_current_style(self):
        if QGis.QGIS_VERSION_INT >= 21820:
            layer = self.iface.activeLayer()
            name = layer.name()
            manager = layer.styleManager()
            layer.saveStyleToDatabase(manager.currentStyle(), name, False, '', '')
        else:
            self.iface.messageBar().pushCritical(
                tr('QGIS >= 2.18.20 is needed'),
                tr('QGIS >= 2.18.20 is needed to save style in database.'))

    def save_current_style_default(self):
        if QGis.QGIS_VERSION_INT >= 21820:
            layer = self.iface.activeLayer()
            name = layer.name()
            manager = layer.styleManager()
            layer.saveStyleToDatabase(manager.currentStyle(), name, True, '', '')
        else:
            self.iface.messageBar().pushCritical(
                tr('QGIS >= 2.18.20 is needed'),
                tr('QGIS >= 2.18.20 is needed to save style in database.'))

    def enable_load_style(self):
        s = QSettings()
        enabled = self.action_enable_sync_style.isChecked()
        s.setValue('db_style_manager/load_style_auto', enabled)

        self.action_save_style.setEnabled(enabled)
        self.action_save_style_default.setEnabled(enabled)
        self.action_load_style_legend.setEnabled(enabled)

    def load_style_legend(self):
        self.load_style_from_database(self.iface.activeLayer())

    @staticmethod
    def load_style_from_database(layer):
        manager = layer.styleManager()
        existing_styles = manager.styles()
        for s in existing_styles:
            manager.removeStyle(s)

        manager.currentStyle()
        manager.renameStyle(manager.currentStyle(), '')
        manager.renameStyle('', 'default')
        styles = layer.listStylesInDatabase()
        if len(styles) == 0:
            # No style for all layers in the database, we do nothing
            return

        number_styles = styles[0]
        if number_styles == 0:
            # No style for this layer in the database, we do nothing
            return

        related_styles_idx = styles[1][0:number_styles]
        related_styles_names = styles[2][0:number_styles]
        related_styles_description = styles[3][0:number_styles]
        related_styles = zip(related_styles_idx, related_styles_names, related_styles_description)
        for style in related_styles:
            xml_style = layer.getStyleFromDatabase(style[0], '')
            # description = style[2]
            manager.addStyle(style[1], QgsMapLayerStyle(xml_style))

        # Deactivated in 0.3, because in QGIS 2.18 we can't know which one is the default style
        # if len(number_styles) > 0:
        #     # If we have at least one style, we take the first one for the title and name
        #     layer.setTitle(related_styles[0][2])
        #     layer.setName(related_styles[0][2])

        if len(related_styles) >= 1:
            # We got one layer, we can set it by default in QGIS
            manager.setCurrentStyle(related_styles[0][1])
            manager.removeStyle('default')

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu(tr('DB Style Manager'), self.action_enable_sync_style)
        self.iface.removePluginMenu(tr('DB Style Manager'), self.action_load_qgis_style_layer)
        self.iface.removeToolBarIcon(self.action_enable_sync_style)
        self.iface.removeToolBarIcon(self.action_load_qgis_style_layer)
        self.iface.legendInterface().removeLegendLayerAction(self.action_save_style)
        self.iface.legendInterface().removeLegendLayerAction(self.action_save_style_default)
        self.iface.legendInterface().removeLegendLayerAction(self.action_load_style_legend)
        del self.toolbar
