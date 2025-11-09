# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QpositionalDialog
                                 A QGIS plugin
 assessment the positional quality of geographic data
                              -------------------
        git sha              : $Format:%H$
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

# Import required libraries
# Import standard libraries and QGIS APIs
import os
import math
import threading
from datetime import datetime
import collections
import numpy as np
import io

# QGIS GUI components and UI designer support
from qgis.gui import (QgsFieldComboBox, QgsMapLayerComboBox)
from qgis.PyQt import (uic, QtWidgets)
from qgis.PyQt.QtCore import QVariant, QPoint, QPointF, QRectF, QSettings, QSize, QRect
from qgis.PyQt.QtSvg import QSvgGenerator
from qgis.PyQt.QtGui import QPen, QColor, QGradient, QBrush, QRadialGradient, QPixmap, QPolygonF, QImage, QPainter, QPainterPath

# Standard Qt Widgets used in the plugin
from PyQt5.QtWidgets import (QFileDialog, QTabWidget, QListWidget, 
    QPushButton, QComboBox, QTextEdit, QGridLayout, QCheckBox, 
    QDialog, QTableWidget, QTableWidgetItem, QAbstractScrollArea, 
    QMessageBox, QInputDialog, QProgressBar, QTextBrowser)
from qgis.PyQt.QtWidgets import (QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsSimpleTextItem, QGraphicsRectItem, 
    QGraphicsPixmapItem, QGraphicsPolygonItem, QApplication, QWidget, QGraphicsPathItem)
from PyQt5.QtSvg import QGraphicsSvgItem, QSvgRenderer
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QByteArray, QBuffer
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView

# Image processing and plotting libraries
from PIL import Image
import matplotlib.pyplot as plot
from scipy.interpolate import griddata
from scipy.interpolate import make_interp_spline

# QGIS core libraries
from qgis import processing
from qgis.core import (QgsVectorLayer, QgsFeatureRequest, QgsField, QgsProject, QgsMarkerSymbol,  
    QgsSimpleFillSymbolLayer, QgsSymbolLayer, QgsProperty, QgsFillSymbol, QgsSingleSymbolRenderer, QgsArrowSymbolLayer, 
    QgsPointXY, QgsFeature, QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProcessingFeedback, QgsWkbTypes,QgsMapLayerProxyModel, QgsProcessingFeatureSourceDefinition)
from processing.tools import dataobjects
from qgis.utils import iface
import qgis.utils

# The project is instantiated
project = QgsProject.instance()

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Qpositional_dialog_base.ui'))

class QpositionalDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Main dialog window class for the Qpositional plugin.
    Inherits from QDialog and the form class generated from the Qt Designer UI.
    """
    def __init__(self, parent=None):
        """
        Constructor. Initializes the UI and connects interface elements to their corresponding methods.
        """
        super(QpositionalDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

        # Load the GUI elements designed in Qt Designer
        self.setupUi(self)

        # Reload and activate the plugin in case it's needed (useful during development)
        qgis.utils.unloadPlugin('Qpositional')
        qgis.utils.loadPlugin('Qpositional')
        qgis.utils.startPlugin('Qpositional')

        # Connect layer combo boxes to their respective handlers
        self.Layer_E1.layerChanged.connect(self.SLayer_E1)
        self.Layer_E2.layerChanged.connect(self.SLayer_E2)
        self.Layer_E3.layerChanged.connect(self.SLayer_E3)
        self.Layer_E4.layerChanged.connect(self.SLayer_E4)
        self.Layer_E5.layerChanged.connect(self.SLayer_E5)
        self.Layer_F1.layerChanged.connect(self.SLayer_E1)
        self.Layer_F2.layerChanged.connect(self.SLayer_E2)
        self.Layer_F3.layerChanged.connect(self.SLayer_E3)
        self.Layer_F4.layerChanged.connect(self.SLayer_E4)
        self.Layer_F5.layerChanged.connect(self.SLayer_E5)

        # Disable all additional layer inputs at start
        self.Layer_E2.setEnabled(False)
        self.Layer_F2.setEnabled(False)
        self.Layer_E3.setEnabled(False)
        self.Layer_F3.setEnabled(False)
        self.Layer_E4.setEnabled(False)
        self.Layer_F4.setEnabled(False)
        self.Layer_E5.setEnabled(False)
        self.Layer_F5.setEnabled(False)

        global var_rest
        var_rest=""

        # Connect buttons and UI elements to corresponding functions
        self.Boton1.clicked.connect(self.paso2)
        self.Boton2.clicked.connect(self.paso3)
        self.bt_restart.setEnabled(False)
        self.bt_restart.clicked.connect(self.rest)
        self.tabWidget.setTabEnabled(1,False)
        self.tabWidget.setTabEnabled(2,False)
        self.tabWidget.setTabEnabled(3,False)
        self.tabWidget.setTabEnabled(4,False)
        self.tabWidget.currentChanged.connect(self.camb_text)
        self.circular = QGraphicsScene(self)
        self.grafic.setScene(self.circular)

        self.cde.textActivated.connect(self.dataset)

        self.az_mean_c.stateChanged.connect(self.redraw)
        self.des_cir_c.stateChanged.connect(self.redraw)
        self.cir_unit_c.clicked.connect(self.cir_unit)
        self.cir_dist_c.clicked.connect(self.cir_dist)
        self.den_gra_c.clicked.connect(self.den_gra)
        self.Bt_apply.clicked.connect(self.redraw)
        self.rem_out.clicked.connect(self.rem_outliers)
        self.mod_hist_c.clicked.connect(self.hist_mod)
        self.Bt_asicur.clicked.connect(self.asi_cur)
        self.Bt_qplotu.clicked.connect(self.qplotuni)
        self.clas_mod.valueChanged[int].connect(self.hist_mod)
        self.red_mode_s.valueChanged[int].connect(self.redraw)
        self.result = None
        self.gen_info.clicked.connect(self.informe)
        self.descarga.clicked.connect(self.desc_data)
        self.data_csv.fileChanged.connect(self.hab_desc)
        self.file_info.fileChanged.connect(self.hab_info)
        self.copygraf.clicked.connect(self.clip)
        self.savesvg.clicked.connect(self.saveassvg)
        self.b_undo.clicked.connect(self.f_undo)

        # Disable buttons until data is loaded
        self.gen_info.setEnabled(False)
        self.descarga.setEnabled(False)

        # Set up calendar input format
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("dd-MM-yyyy")
        fecha=datetime.now()
        self.fecha.setDate(fecha)
        
        # UI label configuration
        self.label_36.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignCenter) 
        self.label_36.setText("The dataset evaluated only shall be compared with the homolog dataset")

        # Define and initialize global variables
        global imagen
        imagen=list()
        global grafic

        global lon_feat
        lon_feat=0


        cant_layer=QgsProject.instance().mapLayers().values()


        # Filters are created for the combo boxes of the data sets to be loaded
        self.Layer_E1.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_E2.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_E3.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_E4.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_E5.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_F1.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_F2.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_F3.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_F4.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.Layer_F5.setFilters(QgsMapLayerProxyModel.VectorLayer)

        #A list is made with the inactive layers
        lay_all = list(project.mapLayers().values())
        lay_act=iface.mapCanvas().layers()

        for i in range(len(lay_act)):
            while lay_act[i] in lay_all:
                lay_all.remove(lay_act[i])
        
        # Only active datasets in QGIS are listed.
        self.Layer_E1.setExceptedLayerList(lay_all)
        self.Layer_E2.setExceptedLayerList(lay_all)
        self.Layer_E3.setExceptedLayerList(lay_all)
        self.Layer_E4.setExceptedLayerList(lay_all)
        self.Layer_E5.setExceptedLayerList(lay_all)
        self.Layer_F1.setExceptedLayerList(lay_all)
        self.Layer_F2.setExceptedLayerList(lay_all)
        self.Layer_F3.setExceptedLayerList(lay_all)
        self.Layer_F4.setExceptedLayerList(lay_all)
        self.Layer_F5.setExceptedLayerList(lay_all)

        
        # Display warning if no datasets are preloaded in QGIS        
        if len(cant_layer)==0:
            QMessageBox.information(iface.mainWindow(), "Dataset not available", 'For better performance of this plugin you should preload the dataset before running Qpositional')

            self.label_36.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignCenter)            
            self.label_36.setText("<b>Must close Qpositional</b>")
        else:
            # Add a group for temporary layers
            grupo = "Temporal"
            root = project.layerTreeRoot()
            gr_cd = root.addGroup(grupo)
            global migrupo
            migrupo = root.findGroup(grupo)
            global ruta_i 
            ruta_i=""

            # Plugin version label
            self.lb_ver.setText('0.9.2')

            # Prepare starting table layout
            self.Tab_start.clear()
            self.Tab_start.setRowCount(5)
            self.Tab_start.setColumnCount(5)            
            self.Tab_start.setHorizontalHeaderItem(0, QTableWidgetItem("EPSG/Unit Dataset Evaluated"))
            self.Tab_start.setHorizontalHeaderItem(1, QTableWidgetItem("EPSG/Unit Dataset Sources"))
            self.Tab_start.setHorizontalHeaderItem(2, QTableWidgetItem("Action"))
            self.Tab_start.setHorizontalHeaderItem(3, QTableWidgetItem("Geometry Dataset Evaluated"))
            self.Tab_start.setHorizontalHeaderItem(4, QTableWidgetItem("Geometry Dataset Sources"))

    # Function to load the layers of the data sets to be evaluated and reference
    def SLayer_E1(self):
        global cont
        global Layer_E1
        global Layer_F1
        Layer_E1 = self.Layer_E1.currentLayer()
        Layer_F1 = self.Layer_F1.currentLayer()

        # If the layer supports spatial indexing, create one
        if isinstance(Layer_E1, QgsVectorLayer):
            if (Layer_E1.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_E1})
        if isinstance(Layer_F1, QgsVectorLayer):
            if (Layer_F1.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_F1})

        # If both layers are valid and not the same
        if Layer_E1 and Layer_F1 and Layer_E1!=Layer_F1:
            # Ensure geometries are compatible: Point-Polygon or vice versa
            if Layer_E1.geometryType()!=Layer_F1.geometryType():
                if (Layer_E1.geometryType()==0 and Layer_F1.geometryType()==2) or (Layer_E1.geometryType()==2 and Layer_F1.geometryType()==0): 
                    self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                    self.Boton1.setEnabled(True)
                    self.Layer_E2.setEnabled(True)
                    self.Layer_F2.setEnabled(True)
                    cont=1

                    # Populate info table with CRS, reprojection needs, and geometry types
                    celda01 = QTableWidgetItem(Layer_E1.crs().userFriendlyIdentifier())
                    celda02 = QTableWidgetItem(Layer_F1.crs().userFriendlyIdentifier())
                    if Layer_E1.crs().userFriendlyIdentifier()==Layer_F1.crs().userFriendlyIdentifier():
                        celda03 = QTableWidgetItem(str('None'))
                    else:
                        celda03 = QTableWidgetItem(str('Reproject'))
                    celda04=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E1.wkbType()))
                    celda05=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F1.wkbType()))

                    self.Tab_start.setItem(0,0,celda01)
                    self.Tab_start.setItem(0,1,celda02)
                    self.Tab_start.setItem(0,2,celda03)
                    self.Tab_start.setItem(0,3,celda04)
                    self.Tab_start.setItem(0,4,celda05)

                else:
                    # Show error if incompatible geometry types    
                    self.adv_1.setText("<font style='color:#FF0000'><b>The geometry types must be the same or (Point-Polygon or Polygon-Point)</b></font>")
                    self.Boton1.setEnabled(False)

                    # Information about the loaded layers is loaded
                    celda1 = QTableWidgetItem(str(''))
                    celda2 = QTableWidgetItem(str(''))
                    celda3 = QTableWidgetItem(str(''))
                    celda4 = QTableWidgetItem(str(''))
                    celda5 = QTableWidgetItem(str(''))
                    self.Tab_start.setItem(0,0,celda1)
                    self.Tab_start.setItem(0,1,celda2)
                    self.Tab_start.setItem(0,2,celda3)
                    self.Tab_start.setItem(0,3,celda4)
                    self.Tab_start.setItem(0,4,celda5)

            else:
                # Allow same geometry types (e.g., point-point)
                self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                self.Boton1.setEnabled(True)
                self.Layer_E2.setEnabled(True)
                self.Layer_F2.setEnabled(True)
                cont=1

                # Information about the loaded layers is loaded
                celda01 = QTableWidgetItem(Layer_E1.crs().userFriendlyIdentifier())
                celda02 = QTableWidgetItem(Layer_F1.crs().userFriendlyIdentifier())
                if Layer_E1.crs().userFriendlyIdentifier()==Layer_F1.crs().userFriendlyIdentifier():
                    celda03 = QTableWidgetItem(str('None'))
                else:
                    celda03 = QTableWidgetItem(str('Reproject'))
                celda04=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E1.wkbType()))
                celda05=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F1.wkbType()))

                self.Tab_start.setItem(0,0,celda01)
                self.Tab_start.setItem(0,1,celda02)
                self.Tab_start.setItem(0,2,celda03)
                self.Tab_start.setItem(0,3,celda04)
                self.Tab_start.setItem(0,4,celda05)

        else:
            self.adv_1.setText("<font style='color:#FF0000'><b>A dataset to be evaluated and a dataset source are required</b></font>")
            self.Boton1.setEnabled(False)

            # Information about the loaded layers is loaded
            celda1 = QTableWidgetItem(str(''))
            celda2 = QTableWidgetItem(str(''))
            celda3 = QTableWidgetItem(str(''))
            celda4 = QTableWidgetItem(str(''))
            celda5 = QTableWidgetItem(str(''))
            self.Tab_start.setItem(0,0,celda1)
            self.Tab_start.setItem(0,1,celda2)
            self.Tab_start.setItem(0,2,celda3)
            self.Tab_start.setItem(0,3,celda4)
            self.Tab_start.setItem(0,4,celda5)

    # Functions SLayer_E2 to SLayer_E5 follow the exact same logic as SLayer_E1,
    # but apply it to each subsequent pair of layers (E2/F2, ..., E5/F5),
    # updating the corresponding row in the summary table (`Tab_start`) and enabling the next layer input widgets.

    # Function to load the layers of the data sets to be evaluated and reference
    def SLayer_E2(self):
        global cont
        global Layer_E2
        global Layer_F2
        Layer_E2 = self.Layer_E2.currentLayer()
        Layer_F2 = self.Layer_F2.currentLayer()

        # Create spatial index to layer 
        if isinstance(Layer_E2, QgsVectorLayer):
            if (Layer_E2.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_E2})
        if isinstance(Layer_F2, QgsVectorLayer):
            if (Layer_F2.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_F2})

        if Layer_E2 and Layer_F2 and Layer_E2!=Layer_F2:
            if Layer_E2.geometryType()!=Layer_F2.geometryType():
                if (Layer_E2.geometryType()==0 and Layer_F2.geometryType()==2) or (Layer_E2.geometryType()==2 and Layer_F2.geometryType()==0): 
                    self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                    self.Boton1.setEnabled(True)
                    self.Layer_E3.setEnabled(True)
                    self.Layer_F3.setEnabled(True)
                    cont=2

                    # Information about the loaded layers is loaded
                    celda11 = QTableWidgetItem(Layer_E2.crs().userFriendlyIdentifier())
                    celda12 = QTableWidgetItem(Layer_F2.crs().userFriendlyIdentifier())
                    if Layer_E2.crs().userFriendlyIdentifier()==Layer_F2.crs().userFriendlyIdentifier():
                        celda13 = QTableWidgetItem(str('None'))
                    else:
                        celda13 = QTableWidgetItem(str('Reproject'))
                    celda14=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E2.wkbType()))
                    celda15=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F2.wkbType()))

                    self.Tab_start.setItem(1,0,celda11)
                    self.Tab_start.setItem(1,1,celda12)
                    self.Tab_start.setItem(1,2,celda13)
                    self.Tab_start.setItem(1,3,celda14)
                    self.Tab_start.setItem(1,4,celda15)

                else:    
                    self.adv_1.setText("<font style='color:#FF0000'><b>The geometry types must be the same or (Point-Polygon or Polygon-Point)</b></font>")
                    self.Boton1.setEnabled(False)

                    # Information about the loaded layers is loaded
                    celda1 = QTableWidgetItem(str(''))
                    celda2 = QTableWidgetItem(str(''))
                    celda3 = QTableWidgetItem(str(''))
                    celda4 = QTableWidgetItem(str(''))
                    celda5 = QTableWidgetItem(str(''))
                    self.Tab_start.setItem(1,0,celda1)
                    self.Tab_start.setItem(1,1,celda2)
                    self.Tab_start.setItem(1,2,celda3)
                    self.Tab_start.setItem(1,3,celda4)
                    self.Tab_start.setItem(1,4,celda5)

            else:
                self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                self.Boton1.setEnabled(True)
                self.Layer_E3.setEnabled(True)
                self.Layer_F3.setEnabled(True)
                cont=2

                # Information about the loaded layers is loaded
                celda11 = QTableWidgetItem(Layer_E2.crs().userFriendlyIdentifier())
                celda12 = QTableWidgetItem(Layer_F2.crs().userFriendlyIdentifier())
                if Layer_E2.crs().userFriendlyIdentifier()==Layer_F2.crs().userFriendlyIdentifier():
                    celda13 = QTableWidgetItem(str('None'))
                else:
                    celda13 = QTableWidgetItem(str('Reproject'))
                celda14=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E2.wkbType()))
                celda15=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F2.wkbType()))

                self.Tab_start.setItem(1,0,celda11)
                self.Tab_start.setItem(1,1,celda12)
                self.Tab_start.setItem(1,2,celda13)
                self.Tab_start.setItem(1,3,celda14)
                self.Tab_start.setItem(1,4,celda15)

        else:
            self.adv_1.setText("<font style='color:#FF0000'><b>A dataset to be evaluated and a dataset source are required</b></font>")
            self.Boton1.setEnabled(False)

            # Information about the loaded layers is loaded
            celda1 = QTableWidgetItem(str(''))
            celda2 = QTableWidgetItem(str(''))
            celda3 = QTableWidgetItem(str(''))
            celda4 = QTableWidgetItem(str(''))
            celda5 = QTableWidgetItem(str(''))
            self.Tab_start.setItem(1,0,celda1)
            self.Tab_start.setItem(1,1,celda2)
            self.Tab_start.setItem(1,2,celda3)
            self.Tab_start.setItem(1,3,celda4)
            self.Tab_start.setItem(1,4,celda5)

    # Function to load the layers of the data sets to be evaluated and reference
    def SLayer_E3(self):
        global cont
        global Layer_E3
        global Layer_F3
        Layer_E3 = self.Layer_E3.currentLayer()
        Layer_F3 = self.Layer_F3.currentLayer()

        # Create spatial index to layer 
        if isinstance(Layer_E3, QgsVectorLayer):
            if (Layer_E3.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_E3})
        if isinstance(Layer_F3, QgsVectorLayer):
            if (Layer_F3.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_F3})

        if Layer_E3 and Layer_F3 and Layer_E3!=Layer_F3:
            if Layer_E3.geometryType()!=Layer_F3.geometryType():
                if (Layer_E3.geometryType()==0 and Layer_F3.geometryType()==2) or (Layer_E3.geometryType()==2 and Layer_F3.geometryType()==0): 
                    self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                    self.Boton1.setEnabled(True)
                    self.Layer_E4.setEnabled(True)
                    self.Layer_F4.setEnabled(True)
                    cont=3

                    # Information about the loaded layers is loaded
                    celda21 = QTableWidgetItem(Layer_E3.crs().userFriendlyIdentifier())
                    celda22 = QTableWidgetItem(Layer_F3.crs().userFriendlyIdentifier())
                    if Layer_E3.crs().userFriendlyIdentifier()==Layer_F3.crs().userFriendlyIdentifier():
                        celda23 = QTableWidgetItem(str('None'))
                    else:
                        celda23 = QTableWidgetItem(str('Reproject'))
                    celda24=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E3.wkbType()))
                    celda25=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F3.wkbType()))

                    self.Tab_start.setItem(2,0,celda21)
                    self.Tab_start.setItem(2,1,celda22)
                    self.Tab_start.setItem(2,2,celda23)
                    self.Tab_start.setItem(2,3,celda24)
                    self.Tab_start.setItem(2,4,celda25)

                else:
                    self.adv_1.setText("<font style='color:#FF0000'><b>The geometry types must be the same or (Point-Polygon or Polygon-Point)</b></font>")
                    self.Boton1.setEnabled(False)

                    # Information about the loaded layers is loaded
                    celda1 = QTableWidgetItem(str(''))
                    celda2 = QTableWidgetItem(str(''))
                    celda3 = QTableWidgetItem(str(''))
                    celda4 = QTableWidgetItem(str(''))
                    celda5 = QTableWidgetItem(str(''))
                    self.Tab_start.setItem(2,0,celda1)
                    self.Tab_start.setItem(2,1,celda2)
                    self.Tab_start.setItem(2,2,celda3)
                    self.Tab_start.setItem(2,3,celda4)
                    self.Tab_start.setItem(2,4,celda5)

            else:
                self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                self.Boton1.setEnabled(True)
                self.Layer_E4.setEnabled(True)
                self.Layer_F4.setEnabled(True)
                cont=3

                # Information about the loaded layers is loaded
                celda21 = QTableWidgetItem(Layer_E3.crs().userFriendlyIdentifier())
                celda22 = QTableWidgetItem(Layer_F3.crs().userFriendlyIdentifier())
                if Layer_E3.crs().userFriendlyIdentifier()==Layer_F3.crs().userFriendlyIdentifier():
                    celda23 = QTableWidgetItem(str('None'))
                else:
                    celda23 = QTableWidgetItem(str('Reproject'))
                celda24=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E3.wkbType()))
                celda25=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F3.wkbType()))

                self.Tab_start.setItem(2,0,celda21)
                self.Tab_start.setItem(2,1,celda22)
                self.Tab_start.setItem(2,2,celda23)
                self.Tab_start.setItem(2,3,celda24)
                self.Tab_start.setItem(2,4,celda25)

        else:
            self.adv_1.setText("<font style='color:#FF0000'><b>A dataset to be evaluated and a dataset source are required</b></font>")
            self.Boton1.setEnabled(False)

            # Information about the loaded layers is loaded
            celda1 = QTableWidgetItem(str(''))
            celda2 = QTableWidgetItem(str(''))
            celda3 = QTableWidgetItem(str(''))
            celda4 = QTableWidgetItem(str(''))
            celda5 = QTableWidgetItem(str(''))
            self.Tab_start.setItem(2,0,celda1)
            self.Tab_start.setItem(2,1,celda2)
            self.Tab_start.setItem(2,2,celda3)
            self.Tab_start.setItem(2,3,celda4)
            self.Tab_start.setItem(2,4,celda5)

    # Function to load the layers of the data sets to be evaluated and reference
    def SLayer_E4(self):
        global cont
        global Layer_E4
        global Layer_F4
        Layer_E4 = self.Layer_E4.currentLayer()
        Layer_F4 = self.Layer_F4.currentLayer()

        # Create spatial index to layer 
        if isinstance(Layer_E4, QgsVectorLayer):
            if (Layer_E4.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_E4})
        if isinstance(Layer_F4, QgsVectorLayer):
            if (Layer_F4.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_F4})

        if Layer_E4 and Layer_F4 and Layer_E4!=Layer_F4:
            if Layer_E4.geometryType()!=Layer_F4.geometryType():
                if (Layer_E4.geometryType()==0 and Layer_F4.geometryType()==2) or (Layer_E4.geometryType()==2 and Layer_F4.geometryType()==0): 
                    self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                    self.Boton1.setEnabled(True)
                    self.Layer_E5.setEnabled(True)
                    self.Layer_F5.setEnabled(True)
                    cont=4

                    # Information about the loaded layers is loaded
                    celda31 = QTableWidgetItem(Layer_E4.crs().userFriendlyIdentifier())
                    celda32 = QTableWidgetItem(Layer_F4.crs().userFriendlyIdentifier())
                    if Layer_E4.crs().userFriendlyIdentifier()==Layer_F4.crs().userFriendlyIdentifier():
                        celda33 = QTableWidgetItem(str('None'))
                    else:
                        celda33 = QTableWidgetItem(str('Reproject'))
                    celda34=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E4.wkbType()))
                    celda35=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F4.wkbType()))

                    self.Tab_start.setItem(3,0,celda31)
                    self.Tab_start.setItem(3,1,celda32)
                    self.Tab_start.setItem(3,2,celda33)
                    self.Tab_start.setItem(3,3,celda34)
                    self.Tab_start.setItem(3,4,celda35)

                else:
                    self.adv_1.setText("<font style='color:#FF0000'><b>The geometry types must be the same or (Point-Polygon or Polygon-Point)</b></font>")
                    self.Boton1.setEnabled(False)

                    # Information about the loaded layers is loaded
                    celda1 = QTableWidgetItem(str(''))
                    celda2 = QTableWidgetItem(str(''))
                    celda3 = QTableWidgetItem(str(''))
                    celda4 = QTableWidgetItem(str(''))
                    celda5 = QTableWidgetItem(str(''))
                    self.Tab_start.setItem(3,0,celda1)
                    self.Tab_start.setItem(3,1,celda2)
                    self.Tab_start.setItem(3,2,celda3)
                    self.Tab_start.setItem(3,3,celda4)
                    self.Tab_start.setItem(3,4,celda5)

            else:
                self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                self.Boton1.setEnabled(True)
                self.Layer_E5.setEnabled(True)
                self.Layer_F5.setEnabled(True)
                cont=4

                # Information about the loaded layers is loaded
                celda31 = QTableWidgetItem(Layer_E4.crs().userFriendlyIdentifier())
                celda32 = QTableWidgetItem(Layer_F4.crs().userFriendlyIdentifier())
                if Layer_E4.crs().userFriendlyIdentifier()==Layer_F4.crs().userFriendlyIdentifier():
                    celda33 = QTableWidgetItem(str('None'))
                else:
                    celda33 = QTableWidgetItem(str('Reproject'))
                celda34=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E4.wkbType()))
                celda35=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F4.wkbType()))

                self.Tab_start.setItem(3,0,celda31)
                self.Tab_start.setItem(3,1,celda32)
                self.Tab_start.setItem(3,2,celda33)
                self.Tab_start.setItem(3,3,celda34)
                self.Tab_start.setItem(3,4,celda35)

        else:
            self.adv_1.setText("<font style='color:#FF0000'><b>A dataset to be evaluated and a dataset source are required</b></font>")
            self.Boton1.setEnabled(False)

            # Information about the loaded layers is loaded
            celda1 = QTableWidgetItem(str(''))
            celda2 = QTableWidgetItem(str(''))
            celda3 = QTableWidgetItem(str(''))
            celda4 = QTableWidgetItem(str(''))
            celda5 = QTableWidgetItem(str(''))
            self.Tab_start.setItem(3,0,celda1)
            self.Tab_start.setItem(3,1,celda2)
            self.Tab_start.setItem(3,2,celda3)
            self.Tab_start.setItem(3,3,celda4)
            self.Tab_start.setItem(3,4,celda5)

    # Function to load the layers of the data sets to be evaluated and reference
    def SLayer_E5(self):
        global cont
        global Layer_E5
        global Layer_F5
        Layer_E5 = self.Layer_E5.currentLayer()
        Layer_F5 = self.Layer_F5.currentLayer()

        # Create spatial index to layer 
        if isinstance(Layer_E5, QgsVectorLayer):
            if (Layer_E5.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_E5})
        if isinstance(Layer_F5, QgsVectorLayer):
            if (Layer_F5.dataProvider().hasSpatialIndex() == 1):
                processing.run("native:createspatialindex", {'INPUT':Layer_F5})

        if Layer_E5 and Layer_F5  and Layer_E5!=Layer_F5:
            if Layer_E5.geometryType()!=Layer_F5.geometryType():
                if (Layer_E5.geometryType()==0 and Layer_F5.geometryType()==2) or (Layer_E5.geometryType()==2 and Layer_F5.geometryType()==0): 
                    self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                    self.Boton1.setEnabled(True)
                    cont=5

                    # Information about the loaded layers is loaded
                    celda41 = QTableWidgetItem(Layer_E5.crs().userFriendlyIdentifier())
                    celda42 = QTableWidgetItem(Layer_F5.crs().userFriendlyIdentifier())
                    if Layer_E5.crs().userFriendlyIdentifier()==Layer_F5.crs().userFriendlyIdentifier():
                        celda43 = QTableWidgetItem(str('None'))
                    else:
                        celda43 = QTableWidgetItem(str('Reproject'))
                    celda44=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E5.wkbType()))
                    celda45=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F5.wkbType()))

                    self.Tab_start.setItem(4,0,celda41)
                    self.Tab_start.setItem(4,1,celda42)
                    self.Tab_start.setItem(4,2,celda43)
                    self.Tab_start.setItem(4,3,celda44)
                    self.Tab_start.setItem(4,4,celda45)

                else:
                    self.adv_1.setText("<font style='color:#FF0000'><b>The geometry types must be the same or (Point-Polygon or Polygon-Point)</b></font>")
                    self.Boton1.setEnabled(False)

                    # Information about the loaded layers is loaded
                    celda1 = QTableWidgetItem(str(''))
                    celda2 = QTableWidgetItem(str(''))
                    celda3 = QTableWidgetItem(str(''))
                    celda4 = QTableWidgetItem(str(''))
                    celda5 = QTableWidgetItem(str(''))
                    self.Tab_start.setItem(4,0,celda1)
                    self.Tab_start.setItem(4,1,celda2)
                    self.Tab_start.setItem(4,2,celda3)
                    self.Tab_start.setItem(4,3,celda4)
                    self.Tab_start.setItem(4,4,celda5)

            else:
                self.adv_1.setText("<font style='color:#297500'><b>Loaded a dataset to evaluate and a dataset source</b></font>")
                self.Boton1.setEnabled(True)
                cont=5

                # Information about the loaded layers is loaded
                celda41 = QTableWidgetItem(Layer_E5.crs().userFriendlyIdentifier())
                celda42 = QTableWidgetItem(Layer_F5.crs().userFriendlyIdentifier())
                if Layer_E5.crs().userFriendlyIdentifier()==Layer_F5.crs().userFriendlyIdentifier():
                    celda43 = QTableWidgetItem(str('None'))
                else:
                    celda43 = QTableWidgetItem(str('Reproject'))
                celda44=QTableWidgetItem(QgsWkbTypes.displayString(Layer_E5.wkbType()))
                celda45=QTableWidgetItem(QgsWkbTypes.displayString(Layer_F5.wkbType()))

                self.Tab_start.setItem(4,0,celda41)
                self.Tab_start.setItem(4,1,celda42)
                self.Tab_start.setItem(4,2,celda43)
                self.Tab_start.setItem(4,3,celda44)
                self.Tab_start.setItem(4,4,celda45)

        else:
            self.adv_1.setText("<font style='color:#FF0000'><b>A dataset to be evaluated and a dataset source are required</b></font>")
            self.Boton1.setEnabled(False)

            # Information about the loaded layers is loaded
            celda1 = QTableWidgetItem(str(''))
            celda2 = QTableWidgetItem(str(''))
            celda3 = QTableWidgetItem(str(''))
            celda4 = QTableWidgetItem(str(''))
            celda5 = QTableWidgetItem(str(''))
            self.Tab_start.setItem(4,0,celda1)
            self.Tab_start.setItem(4,1,celda2)
            self.Tab_start.setItem(4,2,celda3)
            self.Tab_start.setItem(4,3,celda4)
            self.Tab_start.setItem(4,4,celda5)

    # The layer list is created, the common coverage area is created, and the data sets are verified.
    def paso2(self):
        # Set progress bar to initial value
        self.progressBar.setValue(15)
        
        # Define global variable
        global Layer_E, Layer_F, entid, inter_cd
        Layer_E = list()
        Layer_F = list()
        entid=list()

        # The context is configured for use in geoprocesses that require working with invalid geometries.
        context = dataobjects.createContext()
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        # Function to update progress bar during processing
        def progress_changed(progress):
            self.progressBar.setValue(int(progress))

        # Create a feedback object for use in processing
        feed = QgsProcessingFeedback()
        feed.progressChanged.connect(progress_changed)

        # Enable second tab and switch to it
        self.tabWidget.setTabEnabled(1,True)
        self.tabWidget.setCurrentIndex(1)

        # Depending on number of valid layer pairs, populate the lists
        if cont==1:
            Layer_E=[Layer_E1]
            Layer_F=[Layer_F1]
        if cont==2:
            Layer_E=[Layer_E1,Layer_E2]
            Layer_F=[Layer_F1,Layer_F2]
        if cont==3:
            Layer_E=[Layer_E1,Layer_E2,Layer_E3]
            Layer_F=[Layer_F1,Layer_F2,Layer_F3]
        if cont==4:
            Layer_E=[Layer_E1,Layer_E2,Layer_E3,Layer_E4]
            Layer_F=[Layer_F1,Layer_F2,Layer_F3,Layer_F4]
        if cont==5:
            Layer_E=[Layer_E1,Layer_E2,Layer_E3,Layer_E4,Layer_E5]
            Layer_F=[Layer_F1,Layer_F2,Layer_F3,Layer_F4,Layer_F5]
        
        # Get number of features in each evaluation layer        
        n=0
        entid.clear()
        while n<=(cont-1):
            entid.append(len(Layer_E[n]))
            n += 1

        # Prepare output table
        # The results output interface is configured
        self.Tab_ver.clear()
        self.Tab_ver.setRowCount(cont)
        self.Tab_ver.setColumnCount(6)            
        self.Tab_ver.setHorizontalHeaderItem(0, QTableWidgetItem("Dataset Evaluated"))
        self.Tab_ver.setHorizontalHeaderItem(1, QTableWidgetItem("Features"))
        self.Tab_ver.setHorizontalHeaderItem(2, QTableWidgetItem("Dataset Source"))
        self.Tab_ver.setHorizontalHeaderItem(3, QTableWidgetItem("Features"))
        self.Tab_ver.setHorizontalHeaderItem(4, QTableWidgetItem("Extent"))
        self.Tab_ver.setHorizontalHeaderItem(5, QTableWidgetItem("Error vectors"))

        Tab_ver = QTableWidget()
        self.Tab_ver.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        self.progressBar.setValue(25)

        # Fill initial rows with dataset names and feature counts
        fila = 0
        for registro in Layer_E:
            celda1 = QTableWidgetItem(registro.name())
            celda2 = QTableWidgetItem(str(len(registro)))
            celda3 = QTableWidgetItem(Layer_F[fila].name())
            self.Tab_ver.setItem(fila,0,celda1)
            self.Tab_ver.setItem(fila,1,celda2)
            self.Tab_ver.setItem(fila,2,celda3)
            fila +=1 

        # Generates the extension with the coverage of the data sets to be evaluated
        i = 0
        inter_cd=list()
        inter_cd.clear()
        xmin=list()
        ymin=list()
        xmax=list()
        ymax=list()
        xmin.clear()
        ymin.clear()
        xmax.clear()
        ymax.clear()

        # Store reprojected layers
        cdr_reproy=list()
        cdr_reproy.clear()

        # Store 's' (fail) or 'n' (success) for each pair
        fallo=list()
        fallo.clear()


        for i in range((len(Layer_E))):
            # If required, the Reference Data Set is reprojected.
            if Layer_E[i].crs().description()!=Layer_F[i].crs().description():
                c_cde = Layer_E[i].crs().authid()
                ver_cde = QgsCoordinateReferenceSystem(c_cde)
                cdr_rep=processing.run("native:reprojectlayer", {'INPUT':Layer_F[i],'TARGET_CRS':ver_cde,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context, feedback=feed)
                processing.run("native:createspatialindex", {'INPUT':cdr_rep['OUTPUT']})
                name_l=str(Layer_F[i].name())+"_Reproy"
                ren=processing.run("native:renamelayer", {'INPUT': cdr_rep["OUTPUT"],'NAME': name_l}, context=context)
                project.addMapLayer(cdr_rep["OUTPUT"], False)
                migrupo.addLayer(cdr_rep["OUTPUT"])
                cdr_reproy.append(Layer_F[i].name)
                Layer_F[i]=ren["OUTPUT"]

            # Generate extent polygons for both layers
            exten_cde_i = processing.run("native:polygonfromlayerextent", {'INPUT': Layer_E[i],'ROUND_TO':0,'OUTPUT':'TEMPORARY_OUTPUT'})
            project.addMapLayer(exten_cde_i["OUTPUT"], True)

            exten_cde = processing.run("native:fixgeometries", {'INPUT': exten_cde_i["OUTPUT"],'METHOD':1,'OUTPUT':'TEMPORARY_OUTPUT'})
            project.addMapLayer(exten_cde_i["OUTPUT"], True)


            exten_cdr_i = processing.run("native:polygonfromlayerextent", {'INPUT': Layer_F[i],'ROUND_TO':0,'OUTPUT':'TEMPORARY_OUTPUT'})
            project.addMapLayer(exten_cdr_i["OUTPUT"], True)


            exten_cdr = processing.run("native:fixgeometries", {'INPUT': exten_cdr_i["OUTPUT"],'METHOD':1,'OUTPUT':'TEMPORARY_OUTPUT'})
            project.addMapLayer(exten_cde_i["OUTPUT"], True)


            #Generates the intersection to verify common coverage
            inter_ef = processing.run("native:intersection", {'INPUT': exten_cde["OUTPUT"], 'OVERLAY': exten_cdr["OUTPUT"], 'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)            
            project.addMapLayer(inter_ef["OUTPUT"], True)


            # Delete unused layers
            project.removeMapLayer(exten_cde_i["OUTPUT"].id())
            project.removeMapLayer(exten_cdr_i["OUTPUT"].id())  
            project.removeMapLayer(exten_cdr["OUTPUT"].id())


            # Compute area of original evaluated layer extent
            area_int=0
            for feature_e in exten_cde["OUTPUT"].getFeatures():
                geom_e = feature_e.geometry()
                area_cde = (geom_e.area()) 
            project.removeMapLayer(exten_cde["OUTPUT"].id()) 

            if len(inter_ef["OUTPUT"])>0:
                inter = processing.run("native:polygonfromlayerextent", {'INPUT': inter_ef["OUTPUT"],'ROUND_TO':0,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                project.addMapLayer(inter["OUTPUT"], True)
                project.removeMapLayer(inter_ef["OUTPUT"].id()) 

                for feature_i in inter["OUTPUT"].getFeatures():
                    geom_i = feature_i.geometry()
                    area_int = (geom_i.area()) 
                    attrs = feature_i.attributes()
                    xmin.append(attrs[0])
                    ymin.append(attrs[1])
                    xmax.append(attrs[2])
                    ymax.append(attrs[3])

                celda4= QTableWidgetItem(str('{:,.2f}'.format(100*area_int/area_cde)) + "%")
                self.Tab_ver.setItem(i,4,celda4)
                if (100*(area_int/area_cde))>1:
                    fallo.append("n")
                else:
                    fallo.append("s")
                project.removeMapLayer(inter["OUTPUT"].id()) 
            else: 
                celda4= QTableWidgetItem("There is no common coverage area")
                self.Tab_ver.setItem(i,4,celda4)
                fallo.append("s")
                xmin.append(0)
                ymin.append(0)
                xmax.append(0)
                ymax.append(0)

        self.progressBar.setValue(50)

        # Calculate global bounding box from intersections
        x_min = min(xmin)
        y_min = min(ymin)
        x_max = max(xmax)
        y_max = max(ymax)

        # The coordinate reference system is set up.
        epsg=Layer_E[0].crs().toWkt()
        
        # Create a temporary layer in memory
        exten = QgsVectorLayer("Polygon?crs="+ epsg, "temp", "Memory")
        exten.startEditing()
        points = [[QgsPointXY(x_min,y_min),QgsPointXY(x_min,y_max),QgsPointXY(x_max,y_max),QgsPointXY(x_max,y_min),QgsPointXY(x_min,y_min)]]
        
        # Set feature
        feature = QgsFeature()
        
        # Set geometry
        feature.setGeometry(QgsGeometry.fromPolygonXY(points))
        
        # Area determination (remember: projection is not in meters)
        geom = feature.geometry()
        area= geom.area()
        
        # set attributes values 
        feature.setAttributes([1, area])
     
        exten.dataProvider().addFeature(feature)
        
        # stop editing and save changes
        exten.commitChanges()

        # style settings for the coverage polygon (transparent fill with red border)
        fill = QgsSimpleFillSymbolLayer()
        fill.setStrokeColor(Qt.red)
        fill.setStrokeWidth(0.5)
        fill.setColor(Qt.transparent)            
        symbol = QgsFillSymbol()
        symbol.changeSymbolLayer(0, fill)
        exten.setRenderer(QgsSingleSymbolRenderer(symbol))
        
        # Rename and add layer to group
        ren_ext=processing.run("native:renamelayer", {'INPUT': exten,'NAME': 'Assessment Coverage'}, feedback=feed)
        project.addMapLayer(ren_ext["OUTPUT"], False)
        migrupo.addLayer(ren_ext["OUTPUT"])

        self.progressBar.setValue(90)

        area_int=0
        features = exten.getFeatures()
        for feature in features:
            geom = feature.geometry()
            area_int = (geom.area()) 
        celda5= ("Assessment Coverage:" + str('{:,.2f}'.format(100*area_int/area_cde)) + "%")

        i=0
        for i in range((len(inter_cd)-1)):
            project.removeMapLayer(inter_cd[i].id()) 

        # Display the coverage polygon in the map canvas
        exten.selectAll()
        iface.mapCanvas().zoomToSelected(exten)
        canvas = iface.mapCanvas()
        canvas.zoomOut()
        exten.removeSelection() 
        global ext
        ext=exten

        self.progressBar.setValue(100)

        # Extract features from source layers within coverage area
        x=0
        fila = 0
        cant_sa=list()
        for x in range((len(Layer_E))):
            sel_s = processing.run("native:extractbylocation", {'INPUT':Layer_F[x],'PREDICATE':[0],'INTERSECT':ext,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context, feedback=feed)
            project.addMapLayer(sel_s['OUTPUT'], True)                    
            cant_s=len(sel_s['OUTPUT'])
            project.removeMapLayer(sel_s['OUTPUT'].id())

            celda4 = QTableWidgetItem(str(cant_s))
            self.Tab_ver.setItem(fila,3,celda4)
            fila +=1
            cant_sa.append(cant_s)

        self.Boton2.setEnabled(True)
        self.Boton2.setText("Next")

        # Disable next step if no features fall in coverage or if intersections failed
        sum_cant=0
        for x in cant_sa:
            sum_cant+=x
        if sum_cant==0:
            self.Boton2.setEnabled(False)
            self.Boton2.setText("Warning: No source datasets were found within the assessment coverage. Please RESTART")
            self.tabWidget.setTabEnabled(0,False)
            self.bt_restart.setEnabled(True)

        for x in fallo:
            if x=="s":
                self.Boton2.setEnabled(False)
                self.Boton2.setText("Warning: Reselect data sets to be evaluate")


    # Generates error vectors using shortestline, generates circular statistics and diagrams
    def paso3(self):
        # Enable third tab and switch to it
        self.tabWidget.setTabEnabled(2,True)
        self.tabWidget.setCurrentIndex(2)
        global dist
        global x
        
        # Create feedback and progress tracking for long operations
        self.progressBar.setValue(0)
        def progress_changed(progress):
            self.progressBar.setValue(int(progress))
        feed = QgsProcessingFeedback()
        feed.progressChanged.connect(progress_changed)

        global nom_cde
        nom_cde=list()
        nom_cde.clear()
        nom_cde.append("All")

        # The context is configured for use in geoprocesses that require working with invalid geometries.
        context = dataobjects.createContext()
        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        x=0
        lay_eval=0
        for x in range((len(Layer_E))):
            if Layer_E[x].geometryType()==0: # if the layer is ######## POINT ######
                Layer_E[x].removeSelection()
                self.progressBar.setValue(0)
                sel = processing.run("native:selectbylocation", {'INPUT':Layer_E[x],'PREDICATE':[6],'INTERSECT':ext,'METHOD':0}, feedback=feed)

                # Generate shortest lines between points (evaluation vs source)
                if Layer_F[x].geometryType()==0: # if the layer is  ######## POINT ######
                    short = processing.run("native:shortestline", {'SOURCE':sel['OUTPUT'],'DESTINATION':Layer_F[x],'METHOD':0,'NEIGHBORS':1,'DISTANCE':None,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                    #processing.run("native:createspatialindex", {'INPUT':short['OUTPUT']})
                    project.addMapLayer(short['OUTPUT'], True)
                    Layer_E[x].removeSelection()

                    self.progressBar.setValue(20)

                    # Validate geometry
                    short2 = processing.run("qgis:checkvalidity", {'INPUT_LAYER':short['OUTPUT'],'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT'})
                    #processing.run("native:createspatialindex", {'INPUT':short2['VALID_OUTPUT']})
                    project.addMapLayer(short2['VALID_OUTPUT'], True)


                    self.progressBar.setValue(40)

                    # Extract lines within coverage area
                    if short2['VALID_COUNT']>0:
                        dist = processing.run("native:extractbylocation", {'INPUT':short2['VALID_OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'OUTPUT':'TEMPORARY_OUTPUT'})
                        #processing.run("native:createspatialindex", {'INPUT':dist['OUTPUT']})
                        project.addMapLayer(dist['OUTPUT'], False)                    
                        
                        # Add layer
                        migrupo.addLayer(dist['OUTPUT'])

                        self.progressBar.setValue(50)
                        self.dist_Az()
                    project.removeMapLayer(short['OUTPUT'].id())
                    project.removeMapLayer(short2['VALID_OUTPUT'].id())


                self.progressBar.setValue(60)

                if Layer_F[x].geometryType()==2: # if the layer is  ######## POLYGON ######
                    # Use centroids of polygons as destination
                    cen_f = processing.run("native:centroids", {'INPUT':Layer_F[x],'ALL_PARTS':False,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)                 
                    #processing.run("native:createspatialindex", {'INPUT':cen_f['OUTPUT']})
                    project.addMapLayer(cen_f['OUTPUT'], True)
              
                    self.progressBar.setValue(30)

                    # Same process as above but using centroids
                    short = processing.run("native:shortestline", {'SOURCE':sel['OUTPUT'],'DESTINATION':cen_f['OUTPUT'],'METHOD':0,'NEIGHBORS':1,'DISTANCE':None,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                    #processing.run("native:createspatialindex", {'INPUT':short['OUTPUT']})
                    project.addMapLayer(short['OUTPUT'], True)
                    Layer_E[x].removeSelection()

                    self.progressBar.setValue(55)

                    short2 = processing.run("qgis:checkvalidity", {'INPUT_LAYER':short['OUTPUT'],'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT'})
                    #processing.run("native:createspatialindex", {'INPUT':short2['VALID_OUTPUT']})                    
                    project.addMapLayer(short2['VALID_OUTPUT'], True)


                    self.progressBar.setValue(88)

                    if short2['VALID_COUNT']>0:
                        dist = processing.run("native:extractbylocation", {'INPUT':short2['VALID_OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'OUTPUT':'TEMPORARY_OUTPUT'}, feedback=feed)
                        #processing.run("native:createspatialindex", {'INPUT':dist['OUTPUT']})
                        project.addMapLayer(dist['OUTPUT'], False)                    
                        migrupo.addLayer(dist['OUTPUT'])

                        self.progressBar.setValue(90)
                        self.dist_Az()

                    project.removeMapLayer(short['OUTPUT'].id())
                    project.removeMapLayer(short2['VALID_OUTPUT'].id())
                    project.removeMapLayer(cen_f['OUTPUT'].id()) 

            if Layer_E[x].geometryType()==1: # if the layer is  ######## LINE ######
                Layer_E[x].removeSelection()
                
                self.progressBar.setValue(0)
                # Select lines within 50m of reference layer
                sel_cer = processing.run("native:selectwithindistance", {'INPUT':Layer_E[x],'REFERENCE':Layer_F[x],'DISTANCE':50,'METHOD':0}, feedback=feed)


                # Convert selected lines to vertices
                ver = processing.run("native:extractvertices", {'INPUT':QgsProcessingFeatureSourceDefinition(Layer_E[x].id(), selectedFeaturesOnly=True, featureLimit=-1, geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid),'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                #processing.run("native:createspatialindex", {'INPUT':ver['OUTPUT']})
                project.addMapLayer(ver['OUTPUT'], True)
                sel_cer['OUTPUT'].removeSelection()

                self.progressBar.setValue(22)

                # Select vertices within extent
                sel = processing.run("native:selectbylocation", {'INPUT':ver['OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'METHOD':0})

                short = processing.run("native:shortestline", {'SOURCE':sel['OUTPUT'],'DESTINATION':Layer_F[x],'METHOD':0,'NEIGHBORS':1,'DISTANCE':None,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                #processing.run("native:createspatialindex", {'INPUT':short['OUTPUT']})
                project.addMapLayer(short['OUTPUT'], True)
                Layer_E[x].removeSelection()

                self.progressBar.setValue(42)

                short2 = processing.run("qgis:checkvalidity", {'INPUT_LAYER':short['OUTPUT'],'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT'})
                #processing.run("native:createspatialindex", {'INPUT':short2['VALID_OUTPUT']})
                project.addMapLayer(short2['VALID_OUTPUT'], True)


                self.progressBar.setValue(52)

                if short2['VALID_COUNT']>0:
                    dist = processing.run("native:extractbylocation", {'INPUT':short2['VALID_OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'OUTPUT':'TEMPORARY_OUTPUT'})

                    self.progressBar.setValue(72)

                    #processing.run("native:createspatialindex", {'INPUT':dist['OUTPUT']})
                    project.addMapLayer(dist['OUTPUT'], False)                    
                    migrupo.addLayer(dist['OUTPUT'])

                    self.progressBar.setValue(62)
                    self.dist_Az()

                self.progressBar.setValue(82)

                project.removeMapLayer(short['OUTPUT'].id())
                project.removeMapLayer(short2['VALID_OUTPUT'].id())
                project.removeMapLayer(ver['OUTPUT'].id())

            if Layer_E[x].geometryType()==2: # if the layer is  ######## POLYGON ######
                Layer_E[x].removeSelection()

                self.progressBar.setValue(25)
                
                # Get centroids of evaluated polygons
                cen = processing.run("native:centroids", {'INPUT':Layer_E[x],'ALL_PARTS':False,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)                 
                #processing.run("native:createspatialindex", {'INPUT':cen['OUTPUT']})
                project.addMapLayer(cen['OUTPUT'], True)


                self.progressBar.setValue(45)

                sel=processing.run("native:selectbylocation", {'INPUT':cen['OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'METHOD':0}, feedback=feed)

                if Layer_F[x].geometryType()==0: # if the layer is  ######## POINT ######
                    short = processing.run("native:shortestline", {'SOURCE':sel['OUTPUT'],'DESTINATION':Layer_F[x],'METHOD':0,'NEIGHBORS':1,'DISTANCE':None,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                    #processing.run("native:createspatialindex", {'INPUT':short['OUTPUT']})
                    project.addMapLayer(short['OUTPUT'], True)
                    Layer_E[x].removeSelection()

                    self.progressBar.setValue(65)

                    short2 = processing.run("qgis:checkvalidity", {'INPUT_LAYER':short['OUTPUT'],'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT'})
                    #processing.run("native:createspatialindex", {'INPUT':short2['VALID_OUTPUT']})
                    project.addMapLayer(short2['VALID_OUTPUT'], True)


                    self.progressBar.setValue(85)

                    if short2['VALID_COUNT']>0:
                        dist = processing.run("native:extractbylocation", {'INPUT':short2['VALID_OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'OUTPUT':'TEMPORARY_OUTPUT'})
                        #processing.run("native:createspatialindex", {'INPUT':dist['OUTPUT']})
                        project.addMapLayer(dist['OUTPUT'], False)                    
                        migrupo.addLayer(dist['OUTPUT'])

                        self.progressBar.setValue(91)
                        self.dist_Az()

                    project.removeMapLayer(short['OUTPUT'].id())
                    project.removeMapLayer(short2['VALID_OUTPUT'].id())
                    project.removeMapLayer(cen['OUTPUT'].id())                    
                        
                if Layer_F[x].geometryType()==2: # if the layer is  ######## POLYGON ######
                    cen_f = processing.run("native:centroids", {'INPUT':Layer_F[x],'ALL_PARTS':False,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)                 
                    #processing.run("native:createspatialindex", {'INPUT':cen_f['OUTPUT']})
                    project.addMapLayer(cen_f['OUTPUT'], True)

                    self.progressBar.setValue(27)
                    
                    short = processing.run("native:shortestline", {'SOURCE':sel['OUTPUT'],'DESTINATION':cen_f['OUTPUT'],'METHOD':0,'NEIGHBORS':1,'DISTANCE':None,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                    #processing.run("native:createspatialindex", {'INPUT':short['OUTPUT']})
                    project.addMapLayer(short['OUTPUT'], True)
                    Layer_E[x].removeSelection()

                    self.progressBar.setValue(47)

                    short2 = processing.run("qgis:checkvalidity", {'INPUT_LAYER':short['OUTPUT'],'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT'})
                    #processing.run("native:createspatialindex", {'INPUT':short2['VALID_OUTPUT']})
                    project.addMapLayer(short2['VALID_OUTPUT'], True)

                    self.progressBar.setValue(67)

                    if short2['VALID_COUNT']>0:
                        extrac = processing.run("native:extractbylocation", {'INPUT':short2['VALID_OUTPUT'],'PREDICATE':[6],'INTERSECT':ext,'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                        #processing.run("native:createspatialindex", {'INPUT':extrac['OUTPUT']})
                        project.addMapLayer(extrac['OUTPUT'], True)

                        self.progressBar.setValue(87)

                        envol = processing.run("native:convexhull", {'INPUT':Layer_E[x],'OUTPUT':'TEMPORARY_OUTPUT'}, context=context)
                        #processing.run("native:createspatialindex", {'INPUT':envol['OUTPUT']})
                        project.addMapLayer(envol['OUTPUT'], True)

                        self.progressBar.setValue(91)

                        processing.run("native:selectbylocation", {'INPUT':extrac['OUTPUT'],'PREDICATE':[6],'INTERSECT':envol['OUTPUT'],'METHOD':0}, context=context)
                        dist=processing.run("native:saveselectedfeatures", {'INPUT':extrac['OUTPUT'],'OUTPUT':'TEMPORARY_OUTPUT'})
                        #processing.run("native:createspatialindex", {'INPUT':dist['OUTPUT']})
                        project.addMapLayer(dist['OUTPUT'], False)                    
                        migrupo.addLayer(dist['OUTPUT'])
                        project.removeMapLayer(extrac['OUTPUT'].id())
                        project.removeMapLayer(envol['OUTPUT'].id())

                        self.progressBar.setValue(97)
                        self.dist_Az()

                    project.removeMapLayer(short['OUTPUT'].id())
                    project.removeMapLayer(short2['VALID_OUTPUT'].id())
                    project.removeMapLayer(cen['OUTPUT'].id())
                    project.removeMapLayer(cen_f['OUTPUT'].id())
                    
            # Final UI update for this dataset
            if short2['VALID_COUNT']>0:
                celda3 = QTableWidgetItem(str(len(dist['OUTPUT'])))
                lay_eval+=1
            else:
                celda3 = QTableWidgetItem('No error vectors')
            self.Tab_ver.setItem(x,5,celda3)

        # If at least one dataset has vectors, generate circular plots
        if lay_eval>0:
            self.cde.clear()
            if nom_cde[0]=="All":
                self.cde.addItems(list(nom_cde))
            else:
                nom_cde.insert(0, "All")
                self.cde.addItems(list(nom_cde))

            QApplication.processEvents()

            self.proc_data()

        else:
            # Show message if no vectors found
            texts = QGraphicsSimpleTextItem("No error vectors, Datasets have no positional error")
            texts.setPos(10,10)
            deg_medcolour2 = QColor(197, 197, 197)
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)
            self.bt_restart.setEnabled(True)

        # Disable all layer inputs after analysis
        self.b_undo.setEnabled(False)
        self.Layer_E1.setEnabled(False)
        self.Layer_F1.setEnabled(False)
        self.Layer_E2.setEnabled(False)
        self.Layer_F2.setEnabled(False)
        self.Layer_E3.setEnabled(False)
        self.Layer_F3.setEnabled(False)
        self.Layer_E4.setEnabled(False)
        self.Layer_F4.setEnabled(False)
        self.Layer_E5.setEnabled(False)
        self.Layer_F5.setEnabled(False)


    # calculation of distance and azimuth
    def dist_Az(self):
        self.progressBar.setValue(63)

        layer = dist["OUTPUT"]
        prov = layer.dataProvider()

        conteo=layer.fields().count() # Count the number of fields
        campos=list(range(conteo))

        layer.startEditing()

        prov.deleteAttributes(campos)
        layer.updateFields()

        new_fields = [
            QgsField("N_Eval", QVariant.Double),
            QgsField("E_Eval", QVariant.Double),
            QgsField("N_Source", QVariant.Double),
            QgsField("E_Source", QVariant.Double),
            QgsField("Delta_N", QVariant.Double),
            QgsField("Delta_E", QVariant.Double),
            QgsField("Distance", QVariant.Double),
            QgsField("Azimuth", QVariant.Double)
        ]    

        prov.addAttributes(new_fields)
        layer.updateFields()

        # Index of fields for avoid hardcoded
        idx_N_Eval = layer.fields().indexFromName("N_Eval")
        idx_E_Eval = layer.fields().indexFromName("E_Eval")
        idx_N_Source = layer.fields().indexFromName("N_Source")
        idx_E_Source = layer.fields().indexFromName("E_Source")
        idx_Delta_N = layer.fields().indexFromName("Delta_N")
        idx_Delta_E = layer.fields().indexFromName("Delta_E")
        idx_Distance = layer.fields().indexFromName("Distance")
        idx_Azimuth = layer.fields().indexFromName("Azimuth")

        features_to_update = {}

        total_features = layer.featureCount()
        
        cont=0
        for feature in layer.getFeatures():

            geom = feature.geometry()

            xm = geom.vertexAt(0).x()
            ym = geom.vertexAt(0).y()
            xt = geom.vertexAt(1).x()
            yt = geom.vertexAt(1).y()

            delta_n = (yt-ym)
            delta_e = (xt-xm)
            longi=geom.distanceToVertex(1)

            if delta_n==0 or delta_e==0:
                if delta_n==0:
                    if delta_e>0:
                        azimut = 90
                    else:
                        azimut = 270
                else:
                    if delta_n>0:
                        azimut = 0
                    else:
                        azimut = 180
            else:
                angle=(math.atan(delta_e/delta_n))*(180/math.pi)
                if delta_n>0 and delta_e>0:
                    azimut = angle
                if delta_n<0 and delta_e>0:
                    azimut = 180+angle
                if delta_n<0 and delta_e<0:
                    azimut = 180+angle
                if delta_n>0 and delta_e<0:
                    azimut = 360+angle

            attr_values = {
                idx_N_Eval: ym,
                idx_E_Eval: xm,
                idx_N_Source: yt,
                idx_E_Source: xt,
                idx_Delta_N: delta_n,
                idx_Delta_E: delta_e,
                idx_Distance: longi,
                idx_Azimuth: azimut
            }

            features_to_update[feature.id()] = attr_values

            #The progress bar is updated
            cont +=1
            if cont % max(1, total_features // 20) == 0:
                progress = 63 + int(35 * cont / total_features)
                self.progressBar.setValue(progress)

        # Actualización en bloque de atributos
        prov.changeAttributeValues(features_to_update)
        layer.commitChanges()
        
        self.progressBar.setValue(90)

        # error vectors are loaded
        nombre = "Error vectors " + (str(x+1))
        processing.run("native:renamelayer", {'INPUT': dist["OUTPUT"],'NAME': nombre})
        nom_cde.append(nombre)

        # Generates arrow symbols in vectors.
        ruta_estilo = os.path.join(os.path.dirname(__file__), r'scripts\rows.qml') 
        processing.run("native:setlayerstyle", {'INPUT':dist['OUTPUT'],'STYLE':ruta_estilo})
        
    # Function for redraw when a type of graphic is selected 
    def redraw(self):
        self.circular.clear()
        self.grafic.viewport().update()

        #Text wait for load graphics
        title = QGraphicsSimpleTextItem("Processing... wait")
        title.setPos(3,3)
        self.circular.addItem(title)

        #self.tabWidget.setCurrentIndex(2)
        if self.mod_hist_c.isChecked():
            self.progressBar.setValue(0)
            self.cde.setEnabled(False)
            self.t_datos()
            self.hist_mod()
        if self.Bt_asicur.isChecked():
            self.progressBar.setValue(0)
            self.cde.setEnabled(False)
            self.t_datos()
            self.asi_cur()
        if self.Bt_qplotu.isChecked():
            self.progressBar.setValue(0)
            self.cde.setEnabled(False)
            self.t_datos()
            self.qplotuni()
        if self.cir_dist_c.isChecked():
            self.progressBar.setValue(0)
            self.cde.setEnabled(True)
            self.cir_dist()
            self.t_datos()
        if self.cir_unit_c.isChecked():
            self.progressBar.setValue(0)
            self.cde.setEnabled(True)
            self.cir_unit()
            self.t_datos()
        if self.den_gra_c.isChecked():
            self.progressBar.setValue(0)
            self.cde.setEnabled(True)
            self.den_gra()
            self.t_datos()

        self.tabWidget.setCurrentIndex(2)

    # Function for generating the unit circle
    def proc_data(self):
        self.tabWidget.setTabEnabled(2,True)
        self.tabWidget.setTabEnabled(3,True)
        self.tabWidget.setTabEnabled(4,True)
        self.tabWidget.setCurrentIndex(2)
        self.red_mode_s.setEnabled(True)
        self.clas_mod.setEnabled(False)
        self.az_mean_c.setEnabled(True)
        self.des_cir_c.setEnabled(True)
        self.cde.setEnabled(True)

        # The graphic area is cleaned
        self.circular.clear()
        self.grafic.viewport().update()
        self.result=1

        #Text wait for load graphics
        title = QGraphicsSimpleTextItem("Processing... wait")
        title.setPos(3,3)
        self.circular.addItem(title)

        # Scene parameters
        ringcolour = self.Color_ring.color()
        ringcolour2 = self.Color_desv.color()
        viewprect = QRectF(self.grafic.viewport().rect())

        # Scene parameters
        ventana=viewprect
        self.grafic.setSceneRect(viewprect)

        left = self.grafic.sceneRect().left()
        right = self.grafic.sceneRect().right()
        width = self.grafic.sceneRect().width()
        top = self.grafic.sceneRect().top()
        bottom = self.grafic.sceneRect().bottom()
        height = self.grafic.sceneRect().height()

        numrings=self.anillos.value()

        size = min(width, height)

        padding = 15
        maxlength = (size / 2) - padding * 2

        # The scene geomatry of the center point
        start = QPointF(self.grafic.mapToScene(QPoint(int(left + (width / 2)),int(top + (height / 2)))))
        radius = maxlength

        act_cde = self.cde.currentText()

        list_aci_o1 = list()
        list_aci_e1 = list()
        list_lon1=list()

        c=dict()
        global lista_cde
        global data_v0
        global data_v1
        global data_v2
        global data_v3
        global data_v4
        global data_v5

        data_v0=list()
        data_v1=list()
        data_v2=list()
        data_v3=list()
        data_v4=list()
        data_v5=list()

        global azim_feat
        lon_feat=0

        self.progressBar.setValue(5)

        # If all datasets are graphed
        lista_cde = nom_cde
        if lista_cde[0]=="All":
            lista_cde.remove("All")

        data_v0.clear()
        data_v1.clear()
        data_v2.clear()
        data_v3.clear()
        data_v4.clear()
        data_v5.clear()

        max_total=0
        j=0

        for j in range(len(lista_cde)):
            cd_selec = project.mapLayersByName(lista_cde[j])[0]
            maxi_dist = cd_selec.maximumValue(6)
            if maxi_dist>max_total:
                max_total=maxi_dist

            list_aci_o1.clear()
            list_aci_e1.clear()
            list_lon1.clear()
            
            if len(cd_selec)>0:
                for i in cd_selec.getFeatures():
                    self.progressBar.setValue(int(30*((j+1)/(len(cd_selec)))))
                    attrs=i.attributes()

                    #Save attributes azimut y long in list
                    azim_feat = attrs[7]
                    list_aci_o1.append(azim_feat)

                    azim_feat_e = round(azim_feat,0)                    
                    list_aci_e1.append(azim_feat_e)

                    lon_feat = attrs[6]
                    list_lon1.append(lon_feat)

            if len(data_v0)==0:
                data_v0.append(list_aci_o1.copy())
                data_v0.append(list_aci_e1.copy())
                data_v0.append(list_lon1.copy())

            else:
                data_v0[0].extend(list_aci_o1.copy())
                data_v0[1].extend(list_aci_e1.copy())
                data_v0[2].extend(list_lon1.copy())

    
            if j==0:
                data_v1.append(list_aci_o1.copy())
                data_v1.append(list_aci_e1.copy())
                data_v1.append(list_lon1.copy())
            elif j==1:
                data_v2.append(list_aci_o1.copy())
                data_v2.append(list_aci_e1.copy())
                data_v2.append(list_lon1.copy())
            elif j==2:
                data_v3.append(list_aci_o1.copy())
                data_v3.append(list_aci_e1.copy())
                data_v3.append(list_lon1.copy())
            elif j==3:
                data_v4.append(list_aci_o1.copy())
                data_v4.append(list_aci_e1.copy())
                data_v4.append(list_lon1.copy())
            elif j==4:
                data_v5.append(list_aci_o1.copy())
                data_v5.append(list_aci_e1.copy())
                data_v5.append(list_lon1.copy())

        self.dataset()

    def dataset(self):

        global list_aci_o
        global list_aci_e
        global list_lon

        list_aci_o = list()
        list_aci_e = list()
        list_lon=list()

        act_cde = self.cde.currentText()

        if act_cde=="All" or act_cde=="":
            cont=0
            for i in data_v0:
                if cont==0:
                    list_aci_o=i
                if cont==1:
                    list_aci_e=i
                if cont==2:
                    list_lon=i
                cont+=1
        else:
            ind=lista_cde.index(act_cde)
            if ind==0:
                cont=0
                for i in data_v1:
                    if cont==0:
                        list_aci_o=i
                    if cont==1:
                        list_aci_e=i
                    if cont==2:
                        list_lon=i
                    cont+=1
            elif ind==1:
                cont=0
                for i in data_v2:
                    if cont==0:
                        list_aci_o=i
                    if cont==1:
                        list_aci_e=i
                    if cont==2:
                        list_lon=i
                    cont+=1
            elif ind==2:
                cont=0
                for i in data_v3:
                    if cont==0:
                        list_aci_o=i
                    if cont==1:
                        list_aci_e=i
                    if cont==2:
                        list_lon=i
                    cont+=1
            elif ind==3:
                cont=0
                for i in data_v4:
                    if cont==0:
                        list_aci_o=i
                    if cont==1:
                        list_aci_e=i
                    if cont==2:
                        list_lon=i
                    cont+=1
            elif ind==4:
                cont=0
                for i in data_v5:
                    if cont==0:
                        list_aci_o=i
                    if cont==1:
                        list_aci_e=i
                    if cont==2:
                        list_lon=i
                    cont+=1

        self.calculate_param()

    def calculate_param(self):
        if len(list_aci_o)>0:        
            max_total = max(list_lon)

            sen_az_t=0
            cos_az_t=0
            sen_az_t2=0
            cos_az_t2=0
            datos=0
            sum_dist = 0
            lon_max=0
            lon_feat_max=0   
            sum_este=0
            sum_norte=0
            sum_long=0

            for i in range(len(list_lon)):
                self.progressBar.setValue(int(50*((i+1)/(len(list_lon)))))
                azim_feat_e=list_aci_e[i]
                lon_feat=list_lon[i]
                azim_feat=list_aci_o[i]
                datos +=1
                sum_dist += lon_feat
                
                # Accumulate for Calculation of the mean azimuth
                cos_az = (math.cos(azim_feat*math.pi/180))
                cos_az_t = cos_az_t + cos_az
                sen_az = (math.sin(azim_feat*math.pi/180))
                sen_az_t = sen_az_t + sen_az

                #Accumulate for Calculation of Double Cosine and Double Sine
                cos_az2 = (math.cos(2*azim_feat*math.pi/180))
                cos_az_t2 = cos_az_t2 + cos_az2
                sen_az2 = (math.sin(2*azim_feat*math.pi/180))
                sen_az_t2 = sen_az_t2 + sen_az2


                # horizontal standard deviation calculation
                norte = (math.cos(azim_feat*math.pi/180))*lon_feat
                este = (math.sin(azim_feat*math.pi/180))*lon_feat
                sum_norte += norte
                sum_este += este
                sum_long +=lon_feat


            global az_med
            # Calculation of the mean azimuth
            if datos!=0:    
                if cos_az_t==0:
                    az_med=(math.pi/2)
                else:
                    az_med = math.atan(sen_az_t/cos_az_t)

                if cos_az_t==0 or sen_az_t==0:
                    if cos_az_t==0:
                        if sen_az_t>0:
                            az_med=(math.pi/2)
                        else:
                            az_med=(math.pi/2)+math.pi
                    else:
                        if cos_az_t>0:
                            az_med=0
                        else:
                            az_med=(math.pi)
                else:    
                    if cos_az_t>0 and sen_az_t>0:
                        az_med=az_med
                    if cos_az_t<0 and sen_az_t>0:
                        az_med=math.pi+az_med
                    if cos_az_t<0 and sen_az_t<0:
                        az_med=math.pi+az_med
                    if cos_az_t>0 and sen_az_t<0:
                        az_med=(2*math.pi)+az_med
            else:
                az_med=""

            #Calculation of the double mean azimuth 
            if datos!=0:
                if cos_az_t2==0:
                    az_med2=(math.pi/2)
                else:
                    az_med2 = math.atan(sen_az_t2/cos_az_t2)

                if cos_az_t2==0 or sen_az_t2==0:
                    if cos_az_t2==0:
                        if sen_az_t2>0:
                            az_med2=(math.pi/2)
                        else:
                            az_med2=(math.pi/2)+math.pi
                    else:
                        if cos_az_t2>0:
                            az_med2=0
                        else:
                            az_med2=(math.pi)
                else:    
                    if cos_az_t2>0 and sen_az_t2>0:
                        az_med2=az_med2
                    if cos_az_t2<0 and sen_az_t2>0:
                        az_med2=math.pi+az_med2
                    if cos_az_t2<0 and sen_az_t2<0:
                        az_med2=math.pi+az_med2
                    if cos_az_t2>0 and sen_az_t2<0:
                        az_med2=(2*math.pi)+az_med2
            else:
                az_med2=""


            # horizontal standard deviation calculation
            global norte_med
            global este_med
            global desv_sta_l
            global desv_sta_c
            global m2_desv
            global sum_out
            global az_med_t
            global az_median
            global az_mode
            
            if datos!=0:   
                norte_med=sum_norte/datos
                este_med=sum_este/datos
                long_med=sum_long/datos

                sum_de2=0
                sum_dn2=0
                sum_lon2=0

                # Information is extracted to calculate the azimuth and distance.
                for i in range(len(list_lon)):
                    self.progressBar.setValue(int(60*((i+1)/(len(list_lon)))))
                    lon_feat=list_lon[i]
                    azim_feat=list_aci_o[i]
                    
                    dnorte = (((math.cos(azim_feat*math.pi/180))*lon_feat)-norte_med)**2
                    deste = (((math.sin(azim_feat*math.pi/180))*lon_feat)-este_med)**2
                    d_long = (lon_feat-long_med)**2
                    sum_dn2 += dnorte
                    sum_de2 += deste
                    sum_lon2 +=d_long

                if datos-1!=0:
                    residual=(((sum_de2+sum_dn2))**0.5)
                    desv_sta_l=(((sum_lon2)/(datos-1))**0.5)
                    desv_sta_c=(0.5*(sum_de2+sum_dn2)/(datos-1))**0.5
                else:
                    desv_sta_l=0
                    residual=0
                    desv_sta_c=0

                resul_11 = f"Linear Standard Deviation: <br> <b>{desv_sta_l:.3f}</b>"
                self.dsh_t.setText(resul_11)

                resul_12 = f"Circular Standard Deviation: <br> <b>{desv_sta_c:.3f}</b>"
                self.dsc_t.setText(resul_12)


                # calculation of outlier potential 
                    # estimation of circular gross errors
                if datos-1!=0:
                    m2 = (2.5055+(4.6052*math.log10(datos-1)))**0.5
                else:
                    m2=0

                global m2_desv
                m2_desv = m2*desv_sta_c
                resul_12 = f"Potential Outlier (>): <b>{m2_desv:.3f}</b>"
                self.pot_out_t.setText(resul_12)

                # count of outliers
                sum_out=0
                for i in range(len(list_lon)):
                    self.progressBar.setValue(int(70*((i+1)/(len(list_lon)))))
                    lon_feat=list_lon[i]
                    azim_feat=list_aci_o[i]

                    dnorte = (((math.cos(azim_feat*math.pi/180))*lon_feat)-norte_med)**2
                    deste = (((math.sin(azim_feat*math.pi/180))*lon_feat)-este_med)**2
                    
                    res=(dnorte+deste)**0.5
                    if res>=m2_desv:
                        sum_out += 1

                resul_12 = f"Total Outlier: <b>{sum_out:.0f}</b>"
                self.tot_out_t.setText(resul_12)


                if sum_out>0:
                    self.rem_out.setEnabled(True)
                else:
                    self.rem_out.setEnabled(False)


            self.num_d.setText("Data Number: "+str(datos))

            # Draw the azimuth on the unit circle
            az_med_t = az_med*(180/math.pi)

            global des_cir
            global var_ang
            global cen_seg
            global mod_med
            global var_cir
            global desv_ang
            global desv_ang_med
            global disp_cir
            global par_k
            global curt
            global skew
            global emh

            numrings=self.anillos.value()
            ringcolour2 = self.Color_desv.color()

            # calculation of the Mean
            minutos, grados = math.modf(az_med_t)
            segundos, minutos = math.modf(minutos*60)
            segundos = round(segundos*60,2)
            cen_seg=str(round(segundos-int(segundos),2))[1:4]
            resul_1 = f"Mean Azimuth: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b>"
            self.az_mean_t.setText(resul_1)

            if self.cir_unit_c.isChecked():
                self.long_a.setText(str(round((1)/numrings,2)))
            else:
                self.long_a.setText(str(round((lon_feat_max)/numrings,2)))


            # calculation of the mean modulus
            mod_med = (((cos_az_t**2)+(sen_az_t**2))**0.5)/datos
            resul_2 = f"Length of Mean Vector: <b>{mod_med:.3f}</b>"
            self.mod_med_t.setText(resul_2)

            # calculation of the double mean modulus
            mod_med2 = (((cos_az_t2**2)+(sen_az_t2**2))**0.5)/datos


            # calculation of circular variance
            var_cir = 1 - mod_med
            resul_3 = f"Circular Variance: <b>{var_cir:.3f}</b>"
            self.var_cir_t.setText(resul_3)

            # calculation of angular variance
            var_ang = 2*(1 - mod_med)
            resul_13 = f"Angular Variance: <b>{var_ang:.3f}</b>"
            self.var_ang_t.setText(resul_13)

            # calculation of the circular standard deviation
            des_cir = (180/math.pi)*((-2*(math.log(1-var_cir))))**0.5
            minutos, grados = math.modf(des_cir)
            segundos, minutos = math.modf(minutos*60)
            segundos = round(segundos*60,2)
            cen_seg=str(round(segundos-int(segundos),2))[1:4]
            resul_4 = f"Circular Standard Deviation:<br> <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b>"
            self.des_cir_t.setText(resul_4)


            # Estimate the concentration parameter for a von Mises distribution
            if mod_med<0.53:
                par_k = (2*mod_med)+(mod_med**3)+((5/6)*mod_med**5)
            if mod_med>=0.53 and mod_med<0.85:
                par_k = (-0.4)+(1.39*mod_med)+(0.43/(1-mod_med))
            if mod_med>=0.85 and mod_med<0.90:
                par_k = 1/((2*(1-mod_med))+((1-mod_med)**2)-((1-mod_med)**3))
            if mod_med>=0.90 and mod_med<1:
                par_k = 1/(2*(1-mod_med))
            if mod_med>=1:
                par_k = float("inf")
            resul_4 = f"Von Mises Concentration Parameter:<br> <b>{par_k:.3f}</b>"
            self.par_k_t.setText(resul_4)

            # Calculation of Angular Standard Deviation
            sum_ang = 0
            for i in list_aci_o:
                sum_ang += math.pi-abs(math.pi-abs((i*math.pi/180)-az_med))

            desv_ang = sum_ang/datos
            desv_ang = desv_ang*180/math.pi
            minutos, grados = math.modf(desv_ang)
            segundos, minutos = math.modf(minutos*60)
            segundos = round(segundos*60,2)
            cen_seg=str(round(segundos-int(segundos),2))[1:4]
            resul_5 = f"Angular Standard Deviation:<br> <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b>"
            self.des_ang_t.setText(resul_5)

            # Calculation of Angular Dispersion - Mean Angular Deviation
            desv_ang_med = (180/math.pi)*(2*(1-mod_med))**0.5
            minutos, grados = math.modf(desv_ang_med)
            segundos, minutos = math.modf(minutos*60)
            segundos = round(segundos*60,2)
            cen_seg=str(round(segundos-int(segundos),2))[1:4]
            resul_6 = f"Mean Angular Deviation:<br> <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b>"
            self.des_angm_t.setText(resul_6)

            # Calculation of the Asymmetry Coefficient (skewness)
            if mod_med==1:
                skew = 0
            else:
                skew = (mod_med2*math.sin(az_med2-(2*az_med)))/(1-mod_med)**(3/2)
            
            resul_7 = f"Skewness Coefficient (Asimetry or Bias): <br> <b>{skew:.3f}</b>"
            self.skew_t.setText(resul_7)
            
            # Calculation of Kurtosis Measurements (or elevation)
            if mod_med==1:
                curt = float("inf")
            else:
                curt = ((mod_med2*math.cos(az_med2-(2*az_med)))-mod_med**4)/(1-mod_med)**2
            
            resul_8 = f"Kurtosis Coefficient (Peakedness): <br> <b>{curt:.3f}</b>"
            self.curt_t.setText(resul_8)

            # Calculation of circular dispersion 
            disp_cir = (1-mod_med2)/(2*mod_med**2)
            resul_9 = f"Circular Dispersion: <b>{disp_cir:.3f}</b>"
            self.disp_cir_t.setText(resul_9)


            #Statistics on the module
            #Calculation of the Horizontal Mean Error
            emh = sum_dist/datos
            resul_10 = f"Mean Error: <b>{emh:.3f}</b>"
            self.emh_t.setText(resul_10)


            #Calculation of the Mode
            if len(list_aci_o)>0:
                list_aci_ord = sorted(list_aci_o)  # lista ordenada en grados

                #Calculate Mode
                red=self.red_mode_s.value()
                clases=360*(10**red)
                x_red=list()
                x_red.clear()
                cont=0
                for i in list_aci_ord:
                    self.progressBar.setValue(int(80*((i+1)/(len(list_aci_ord)))))
                    x_red.append(round(i,red))
                frecuencias, extremos = np.histogram(x_red, bins=clases)
                f_moda=max(frecuencias)
                pos_max=0
                cont=0
                for i in frecuencias:
                    if i==f_moda: 
                        pos_max=cont
                        az_mode=(extremos[cont]+extremos[cont+1])/2
                    cont+=1
            else:
                az_mode=""  

            # calculation of the Mode
            if mod_med>=0.5:
                minutos, grados = math.modf(round(az_mode,red))
                segundos, minutos = math.modf(minutos*60)
                segundos = round(segundos*60,2)
                cen_seg=str(round(segundos-int(segundos),2))[1:4]
                resul_7 = f"Mode Azimuth: <br><b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b>"
            else:
                resul_7="Mode Azimuth: <br>Does not apply"
                self.red_mode_s.setEnabled(False)
            self.az_mode_t.setText(resul_7)

            #Calculation of the Median y Mode
            resul_7 = f"Median Azimuth: <b>Processing...</b>"
            self.az_median_t.setText(resul_7)

            if len(list_aci_o)>0:
                # Calculate Median
                val_dm=dict()
                
                list_aci_ord = sorted(list_aci_o)  # lista ordenada en grados
                n = len(list_aci_ord)
                block_size = 1000  # ajustar según memoria disponible

                val_dm_p = np.zeros(n)

                for i, angle_i_deg in enumerate(list_aci_ord):
                    self.progressBar.setValue(int(90*((i+1)/(len(list_aci_ord)))))
                    sum_val = 0
                    angle_i_rad = math.radians(angle_i_deg)  # convertir a radianes solo una vez
                    for inic in range(0, n, block_size):
                        end = min(inic + block_size, n)
                        block_deg = list_aci_ord[inic:end]
                        block_rad = np.radians(block_deg)  # conversión en bloque
                        diff = np.abs(math.pi - np.abs(block_rad - angle_i_rad))
                        sum_val += np.sum(diff)
                    val_dm_p[i] = math.pi - (sum_val / n)

                val_dm = {angle: val for angle, val in zip(list_aci_ord, val_dm_p)}

                mediana=""
                min_val_dm=val_dm[list_aci_ord[0]]

                for i in val_dm:
                    if min_val_dm>val_dm[i]:
                        min_val_dm=val_dm[i]
                        mediana=i
                num_med=0
                sum_med=0
                
                anterior=""
                for i in val_dm:
                    if min_val_dm==val_dm[i]:
                        sum_med+=i
                        num_med+=1
                        ant_val=anterior
                    anterior=i

                if num_med==1:
                    if (len(list_aci_ord) % 2) == 0:
                        cont=0
                        for i in list_aci_ord:
                            if sum_med==i:
                                cont+=1                
                        if cont==1:
                            az_median=((sum_med+ant_val)/2)
                        else:
                            az_median=(sum_med/num_med)
                    else:
                        az_median=(sum_med/num_med)
                else:
                    az_median=(sum_med/num_med)

            else:
                az_median=""


            # calculation of the Median
            minutos, grados = math.modf(az_median)
            segundos, minutos = math.modf(minutos*60)
            segundos = round(segundos*60,2)
            cen_seg=str(round(segundos-int(segundos),2))[1:4]
            resul_7 = f"Median Azimuth: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b>"
            self.az_median_t.setText(resul_7)

        else:
            datos=0
            self.rem_out.setEnabled(False)

            resul_1 = "Data Number: -"
            self.num_d.setText(resul_1)
            resul_1 = "Mean Azimuth: <b>-° -' -''</b>"
            self.az_mean_t.setText(resul_1)
            resul_7 = "Median Azimuth: <b>-° -' -''</b>"
            self.az_median_t.setText(resul_7)
            resul_7 = "Mode Azimuth: <b>-° -' -''</b>"
            self.az_mode_t.setText(resul_7)
            resul_2 = "Length of Mean Vector: <b>-</b>"
            self.mod_med_t.setText(resul_2)
            resul_3 = "Circular Variance: <b>-</b>"
            self.var_cir_t.setText(resul_3)
            resul_4 = "Circular Standard Deviation (Degree):<br> <b>-° -' -''</b>"
            self.des_cir_t.setText(resul_4)
            resul_13 = f"Angular Variance: <b>-</b>"
            self.var_ang_t.setText(resul_13)
            resul_4 = "Von Mises Concentration Parameter:<br> <b>-</b>"
            self.par_k_t.setText(resul_4)
            resul_5 = "Angular Standard Deviation:<br> <b>-° -' -''</b>"
            self.des_ang_t.setText(resul_5)
            resul_6 = "Mean Angular Deviation:<br> <b>-° -' -''</b>"
            self.des_angm_t.setText(resul_6)
            resul_7 = "Skewness Coefficient (Asimetry or bias): <br> <b>-</b>"
            self.skew_t.setText(resul_7)
            resul_8 = "Kurtosis Coefficient (Peakedness): <br> <b>-</b>"
            self.curt_t.setText(resul_8)
            resul_9 = "Circular Dispersion: <b>-''</b>"
            self.disp_cir_t.setText(resul_9)
            resul_10 = "Mean Error: <b>-</b>"
            self.emh_t.setText(resul_10)
            resul_11 = "Standard Deviation: <br> <b>-</b>"
            self.dsh_t.setText(resul_11)
            resul_11 = "Circular Standard Deviation: <br> <b>-</b>"
            self.dsc_t.setText(resul_11)
            resul_12 = "Potencial Outlier (>): <b>-</b>"
            self.pot_out_t.setText(resul_12)
            resul_12 = "Total Outlier: <b>-</b>"
            self.tot_out_t.setText(resul_12)

        self.progressBar.setValue(100)
        self.bt_restart.setEnabled(True)
        self.redraw()

    # Draw circle unit
    def cir_unit(self):
        self.result=1
        self.az_mean_c.setEnabled(True)
        self.des_cir_c.setEnabled(True)
        self.cde.setEnabled(True)

        if len(list_aci_o)>0:
            self.circular.clear()
            self.grafic.viewport().update()        
            
            max_total = max(list_lon)

            list_aci = list()
            list_aci.clear()
            sen_az_t=0
            cos_az_t=0
            sen_az_t2=0
            cos_az_t2=0
            datos=0
            sum_dist = 0
            lon_max=0
            lon_feat_max=0   
            sum_este=0
            sum_norte=0
            sum_long=0

            viewprect = QRectF(self.grafic.viewport().rect())
            ventana=viewprect
            self.grafic.setSceneRect(viewprect)

            ringcolour = self.Color_ring.color()
            ringcolour2 = self.Color_desv.color()
            left = self.grafic.sceneRect().left()
            right = self.grafic.sceneRect().right()
            width = self.grafic.sceneRect().width()
            top = self.grafic.sceneRect().top()
            bottom = self.grafic.sceneRect().bottom()
            height = self.grafic.sceneRect().height()

            numrings=self.anillos.value()

            self.long_a.setText(str(round((1)/numrings,2)))

            size = width
            if width > height:
                size = height
            padding = 15
            maxlength = (size / 2) - padding * 2
            center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
            # The scene geomatry of the center point
            start = QPointF(self.grafic.mapToScene(center))
            radius = maxlength

            for i in range(len(list_lon)):
                self.progressBar.setValue(int(50*((i+1)/(len(list_lon)))))
                azim_feat_e=list_aci_e[i]
                lon_feat=list_lon[i]
                azim_feat=list_aci_o[i]

                # count the times it appears 
                #c.clear()
                c = collections.Counter(list_aci)
                veces=c[azim_feat_e]
                list_aci.append(azim_feat_e)    

                lon = radius-(veces/0.5)
                if lon<0:
                    lon=0
                pos_y = (math.cos(azim_feat_e*math.pi/180))*lon
                pos_x = (math.sin(azim_feat_e*math.pi/180))*lon
                rel=100

                # Draw main circle and axes
                punto = QGraphicsEllipseItem(start.x()+pos_x-((radius/rel)/2), start.y()-pos_y-((radius/rel)/2),radius/rel, radius/rel)
                pt_colour = self.Color_dot.color()
                myPen = QPen(pt_colour)
                myPen.setWidth(2)
                myPen.setCapStyle(Qt.FlatCap)
                punto.setPen(myPen)
                brush = QBrush(QColor(pt_colour), style=Qt.SolidPattern)
                punto.setBrush(brush)
                self.circular.addItem(punto)

                datos +=1
                sum_dist += lon_feat
                

            self.progressBar.setValue(70)
            #Draw the rings in the graphical output
            for i in range(numrings):
                step = maxlength / numrings
                radius = step * (i + 1)
                circle = QGraphicsEllipseItem(start.x() - radius,start.y() - radius,radius * 2,radius * 2)
                circle.setPen(QPen(ringcolour))
                self.circular.addItem(circle)

            # Draw the azimuth on the unit circle
            az_med_t = az_med*(180/math.pi)

            lon_max=radius
                
            pos_y = (math.cos(az_med_t*math.pi/180))*lon_max
            pos_x = (math.sin(az_med_t*math.pi/180))*lon_max
            
            # Draw the azimuth mean on the unit circle
            if self.az_mean_c.checkState():
                linea_az = QGraphicsLineItem(start.x(), start.y(), start.x()+pos_x, start.y()-pos_y)
                az_medcolour = self.Color_mean.color()
                myPen = QPen(az_medcolour)
                myPen.setWidth(2)
                myPen.setCapStyle(Qt.FlatCap)
                linea_az.setPen(myPen)
                self.circular.addItem(linea_az)

            self.progressBar.setValue(80)

            # Draw the standard deviation in the graphical output
            az_med_i=az_med_t-des_cir
            if az_med_i<0:
                az_med_i=360+az_med_i
            az_med_s=az_med_t+des_cir
            if az_med_s>360:
                az_med_s=az_med_s-360

            #Draw the circular standard deviation in pie chart format.
            trans=(self.trans_desv.value())/100
            if self.des_cir_c.isChecked():       
                circle2 = QGraphicsEllipseItem(start.x() - radius,start.y() - radius,radius * 2,radius * 2)
                circle2.setStartAngle(int((360-az_med_i+90-(des_cir*2))*16))
                circle2.setSpanAngle(int((des_cir*2)*16))   
                circle2.setPen(QPen(ringcolour2))
                ringcolour2.setAlphaF(trans)
                circle2.setBrush((ringcolour2))
                self.circular.addItem(circle2)

            # Info aditional for circular
            # Draw the sectors on the unit circle
            sect=self.section_a.value()
            deg_sec=360/sect
            self.deg_a.setText(str(round(deg_sec,0))+"°")

            self.progressBar.setValue(90)

            for i in range(sect):
                ang=i*deg_sec
                pos_y = (math.cos(ang*math.pi/180))*(lon_max*1.05)
                pos_x = (math.sin(ang*math.pi/180))*(lon_max*1.05)
                linea_deg = QGraphicsLineItem(start.x(), start.y(), start.x()+pos_x, start.y()-pos_y)            
                deg_medcolour2 = self.Color_bin.color()
                myPen2 = QPen(deg_medcolour2)
                myPen2.setWidth(1)
                myPen2.setCapStyle(Qt.FlatCap)
                linea_deg.setPen(myPen2)
                self.circular.addItem(linea_deg)

                tex=int(deg_sec*i)
                text1 = QGraphicsSimpleTextItem(str(tex))
                pos_y = (math.cos(ang*math.pi/180))*(lon_max*1.1)
                pos_x = (math.sin(ang*math.pi/180))*(lon_max*1.1)            
                text1.setPos(start.x()+pos_x-8, start.y()-pos_y-8)

                rect = text1.boundingRect()
                if   ang <= 5:   # Arriba
                    text1.setTransformOriginPoint(10*rect.width(), 10*rect.height())
                if      5 < ang < 22.5   or 337.5 <= ang <= 360:   # Arriba
                    text1.setTransformOriginPoint(rect.width() / 2, rect.height())
                elif  22.5 <= ang < 67.5:                            # Arriba-derecha
                    text1.setTransformOriginPoint(0, rect.height())
                elif  67.5 <= ang < 112.5:                           # Derecha puro
                    text1.setTransformOriginPoint(0, rect.height() / 2)
                elif 112.5 <= ang < 157.5:                           # Abajo-derecha
                    text1.setTransformOriginPoint(0, 0)
                elif 157.5 <= ang < 202.5:                           # Abajo
                    text1.setTransformOriginPoint(rect.width() / 2, 0)
                elif 202.5 <= ang < 247.5:                           # Abajo-izquierda
                    text1.setTransformOriginPoint(rect.width(), 0)
                elif 247.5 <= ang < 292.5:                           # Izquierda puro
                    text1.setTransformOriginPoint(rect.width(), rect.height() / 2)
                elif 292.5 <= ang < 337.5:                           # Arriba-izquierda
                    text1.setTransformOriginPoint(rect.width(), rect.height())
        
                rotation = ang
                if 90 < ang <= 270:
                    rotation += 180  # Voltear el texto si está en el lado izquierdo
                
                text1.setRotation(rotation)

                self.circular.addItem(text1)

            #Draw the sectors on the unit circle
            for i in range(numrings):
                step = maxlength / numrings
                radius = step * (i + 1)

                text=round((i + 1)/numrings,1)

                text2 = QGraphicsSimpleTextItem(str(text))
                pos=((2**0.5)/2)*radius
                text2.setPos(start.x() + pos,start.y() + pos)
                self.circular.addItem(text2)

            if sum_out>0:
                self.rem_out.setEnabled(True)
        
        else:
            datos=0
            self.rem_out.setEnabled(False)
            text2 = QGraphicsSimpleTextItem(str("No Data"))
            text2.setPos(start.x(),start.y())
            self.circular.addItem(text2) 

        #Text configuration in graphic output
        title = QGraphicsSimpleTextItem("Unit circle graph")
        title.setPos(10,10)
        self.circular.addItem(title)
        
        self.progressBar.setValue(100)
        self.bt_restart.setEnabled(True)


    def cir_dist(self):
        self.result=1
        self.az_mean_c.setEnabled(True)
        self.des_cir_c.setEnabled(True)
        self.cde.setEnabled(True)
        
        if len(list_aci_o)>0:
            self.circular.clear()
            self.grafic.viewport().update()        
            
            max_total = max(list_lon)

            list_aci = list()
            list_aci.clear()
            sen_az_t=0
            cos_az_t=0
            sen_az_t2=0
            cos_az_t2=0
            datos=0
            sum_dist = 0
            lon_max=0
            lon_feat_max=0   
            sum_este=0
            sum_norte=0
            sum_long=0

            viewprect = QRectF(self.grafic.viewport().rect())
            ventana=viewprect
            self.grafic.setSceneRect(viewprect)


            ringcolour = self.Color_ring.color()
            ringcolour2 = self.Color_desv.color()
            left = self.grafic.sceneRect().left()
            right = self.grafic.sceneRect().right()
            width = self.grafic.sceneRect().width()
            top = self.grafic.sceneRect().top()
            bottom = self.grafic.sceneRect().bottom()
            height = self.grafic.sceneRect().height()

            numrings=self.anillos.value()

            size = width
            if width > height:
                size = height
            padding = 15
            maxlength = (size / 2) - padding * 2
            center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
            # The scene geomatry of the center point
            start = QPointF(self.grafic.mapToScene(center))
            radius = maxlength

            for i in range(len(list_lon)):
                self.progressBar.setValue(int(50*((i+1)/(len(list_lon)))))
                azim_feat_e=list_aci_e[i]
                lon_feat=list_lon[i]
                azim_feat=list_aci_o[i]

                lon = lon_feat*(radius/max_total)
                if lon_max<lon:
                    lon_max=lon
                    lon_feat_max=lon_feat
                pos_y = (math.cos(azim_feat*math.pi/180))*lon
                pos_x = (math.sin(azim_feat*math.pi/180))*lon

                # Draw main line
                linea = QGraphicsLineItem(start.x(), start.y(), start.x()+pos_x, start.y()-pos_y)
                ln_medcolour = self.Color_line.color()
                myPen = QPen(ln_medcolour)
                myPen.setWidth(2)
                myPen.setCapStyle(Qt.FlatCap)
                linea.setPen(myPen)
                self.circular.addItem(linea)

                datos +=1
                sum_dist += lon_feat

            self.long_a.setText(str(round((lon_feat_max)/numrings,2)))

            # Draw the common elements over the graphic
            #Draw the rings in the graphical output
            for i in range(numrings):
                step = maxlength / numrings
                radius = step * (i + 1)
                circle = QGraphicsEllipseItem(start.x() - radius,start.y() - radius,radius * 2,radius * 2)
                circle.setPen(QPen(ringcolour))
                self.circular.addItem(circle)

            # Draw the azimuth on the unit circle
            az_med_t = az_med*(180/math.pi)

            
            pos_y = (math.cos(az_med_t*math.pi/180))*lon_max
            pos_x = (math.sin(az_med_t*math.pi/180))*lon_max
            
            # Draw the azimuth mean on the unit circle
            if self.az_mean_c.checkState():
                linea_az = QGraphicsLineItem(start.x(), start.y(), start.x()+pos_x, start.y()-pos_y)
                az_medcolour = self.Color_mean.color()
                myPen = QPen(az_medcolour)
                myPen.setWidth(2)
                myPen.setCapStyle(Qt.FlatCap)
                linea_az.setPen(myPen)
                self.circular.addItem(linea_az)

            self.progressBar.setValue(70)

            # Draw the standard deviation in the graphical output
            az_med_i=az_med_t-des_cir
            if az_med_i<0:
                az_med_i=360+az_med_i
            az_med_s=az_med_t+des_cir
            if az_med_s>360:
                az_med_s=az_med_s-360

            #Draw the circular standard deviation in pie chart format.
            trans=(self.trans_desv.value())/100
            if self.des_cir_c.isChecked():       
                circle2 = QGraphicsEllipseItem(start.x() - radius,start.y() - radius,radius * 2,radius * 2)
                circle2.setStartAngle(int((360-az_med_i+90-(des_cir*2))*16))
                circle2.setSpanAngle(int((des_cir*2)*16))   
                circle2.setPen(QPen(ringcolour2))
                ringcolour2.setAlphaF(trans)
                circle2.setBrush((ringcolour2))
                self.circular.addItem(circle2)

            if sum_out>0:
                self.rem_out.setEnabled(True)

        else:
            datos=0
            self.rem_out.setEnabled(False)

            text2 = QGraphicsSimpleTextItem(str("No Data"))
            text2.setPos(start.x(),start.y())
            self.circular.addItem(text2) 

        title = QGraphicsSimpleTextItem("Distance and azimuth distribution graph")
        title.setPos(10,10)
        self.circular.addItem(title)

        self.progressBar.setValue(80)
        
        # Info aditional for circular
        # Draw the sectors on the unit circle
        
        sect=self.section_a.value()
        deg_sec=360/sect
        self.deg_a.setText(str(round(deg_sec,0))+"°")

        for i in range(sect):
            ang=i*deg_sec
            pos_y = (math.cos(ang*math.pi/180))*(lon_max*1.05)
            pos_x = (math.sin(ang*math.pi/180))*(lon_max*1.05)
            linea_deg = QGraphicsLineItem(start.x(), start.y(), start.x()+pos_x, start.y()-pos_y)            
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_deg.setPen(myPen2)
            self.circular.addItem(linea_deg)

            tex=int(deg_sec*i)
            text1 = QGraphicsSimpleTextItem(str(tex))
            pos_y = (math.cos(ang*math.pi/180))*(lon_max*1.1)
            pos_x = (math.sin(ang*math.pi/180))*(lon_max*1.1)            
            text1.setPos(start.x()+pos_x-8, start.y()-pos_y-8)

            rect = text1.boundingRect()
            if   ang <= 5:   # Arriba
                text1.setTransformOriginPoint(10*rect.width(), 10*rect.height())
            if      5 < ang < 22.5   or 337.5 <= ang <= 360:   # Arriba
                text1.setTransformOriginPoint(rect.width() / 2, rect.height())
            elif  22.5 <= ang < 67.5:                            # Arriba-derecha
                text1.setTransformOriginPoint(0, rect.height())
            elif  67.5 <= ang < 112.5:                           # Derecha puro
                text1.setTransformOriginPoint(0, rect.height() / 2)
            elif 112.5 <= ang < 157.5:                           # Abajo-derecha
                text1.setTransformOriginPoint(0, 0)
            elif 157.5 <= ang < 202.5:                           # Abajo
                text1.setTransformOriginPoint(rect.width() / 2, 0)
            elif 202.5 <= ang < 247.5:                           # Abajo-izquierda
                text1.setTransformOriginPoint(rect.width(), 0)
            elif 247.5 <= ang < 292.5:                           # Izquierda puro
                text1.setTransformOriginPoint(rect.width(), rect.height() / 2)
            elif 292.5 <= ang < 337.5:                           # Arriba-izquierda
                text1.setTransformOriginPoint(rect.width(), rect.height())
    
            rotation = ang
            if 90 < ang <= 270:
                rotation += 180  # Voltear el texto si está en el lado izquierdo
            
            text1.setRotation(rotation)

            self.circular.addItem(text1)

        self.progressBar.setValue(90)
        #Draw the sectors on the unit circle
        for i in range(numrings):
            step = maxlength / numrings
            radius = step * (i + 1)
            
            text=round((i + 1)*lon_feat_max/numrings,1)

            text2 = QGraphicsSimpleTextItem(str(text))
            pos=((2**0.5)/2)*radius
            text2.setPos(start.x() + pos,start.y() + pos)
            self.circular.addItem(text2)

        self.progressBar.setValue(100)
        self.bt_restart.setEnabled(True)
    

    #Intesnsify color    
    def valor_a_color(self, v, primer_cuartil):
        # v debe estar normalizado en [0,255]
        pt_colour1 = self.Color_d1.color()
        pt_colour2 = self.Color_d2.color()

        if primer_cuartil==0:
            primer_cuartil=1

        if v < 50:
            # Without color
            return QColor(255, 255, 255, 0)  
        #elif v < primer_cuartil:
        elif 50 <= v < 200:
            # Interpolation lineal beetwen pt_colour1 y pt_colour2 for v 
            #ratio_linear = v / primer_cuartil
            ratio_linear = v / 200
            k = 1  # factor of acceleration
            ratio = (np.exp(k * ratio_linear) - 1) / (np.exp(k) - 1)
            r = int(pt_colour1.red() + ratio * (pt_colour2.red() - pt_colour1.red()))
            g = int(pt_colour1.green() + ratio * (pt_colour2.green() - pt_colour1.green()))
            b = int(pt_colour1.blue() + ratio * (pt_colour2.blue() - pt_colour1.blue()))
            a = int(pt_colour1.alpha() + ratio * (pt_colour2.alpha() - pt_colour1.alpha()))
            return QColor(r, g, b, a)
        else:
            # final Color pt_colour2 
            return pt_colour2


    #Draw graphic de density map
    def den_gra(self):
        self.result=1
        self.az_mean_c.setEnabled(True)
        self.des_cir_c.setEnabled(True)
        self.cde.setEnabled(True)

        if len(list_aci_o)>0:
            self.circular.clear()
            self.grafic.viewport().update()

            max_total = max(list_lon)

            list_aci = list()
            list_aci.clear()
            sen_az_t=0
            cos_az_t=0
            sen_az_t2=0
            cos_az_t2=0
            datos=0
            sum_dist = 0
            lon_max=0
            lon_feat_max=0   
            sum_este=0
            sum_norte=0
            sum_long=0

            viewprect = QRectF(self.grafic.viewport().rect())
            ventana=viewprect
            self.grafic.setSceneRect(viewprect)

            ringcolour = self.Color_ring.color()
            ringcolour2 = self.Color_desv.color()
            left = self.grafic.sceneRect().left()
            right = self.grafic.sceneRect().right()
            width = self.grafic.sceneRect().width()
            top = self.grafic.sceneRect().top()
            bottom = self.grafic.sceneRect().bottom()
            height = self.grafic.sceneRect().height()

            numrings=self.anillos.value()
            
            size = width
            if width > height:
                size = height
            padding = 15
            maxlength = (size / 2) - padding * 2
            center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
            # The scene geomatry of the center point
            start = QPointF(self.grafic.mapToScene(center))
            radius = maxlength
            lon_max=radius


            for i in range(len(list_lon)):
                self.progressBar.setValue(int(50*((i+1)/(len(list_lon)))))
                azim_feat_e=list_aci_e[i]
                lon_feat=list_lon[i]
                azim_feat=list_aci_o[i]

                lon = lon_feat*(radius/max_total)
                if lon_max<lon:
                    lon_max=lon
                    lon_feat_max=lon_feat
                pos_y = (math.cos(azim_feat*math.pi/180))*lon
                pos_x = (math.sin(azim_feat*math.pi/180))*lon
                rel=100

                """            
                # Scene parameters
                rect = QGraphicsEllipseItem(start.x()+pos_x-(0.5*radius/(rel*0.05)), start.y()-pos_y-(0.5*radius/(rel*0.05)),radius/(rel*0.05), radius/(rel*0.05))
                grad = QRadialGradient(start.x()+pos_x, start.y()-pos_y, (radius/2))
                pt_colour1 = self.Color_d1.color()
                pt_colour1.setAlphaF(0.1)
                pt_colour2 = self.Color_d2.color()
                pt_colour2.setAlphaF(0.1)
                pt_colour3 = self.Color_d2.color()
                pt_colour3.setAlphaF(0)
                grad.setColorAt(0, pt_colour1)
                grad.setColorAt(1, pt_colour2)
                brush = QBrush(grad)
                rect.setPen(pt_colour3)
                rect.setBrush(brush)
                self.circular.addItem(rect)

                """
                punto = QGraphicsEllipseItem(start.x()+pos_x, start.y()-pos_y,radius/rel, radius/rel)
                pt_colour = self.Color_dot.color()
                myPen = QPen(pt_colour)
                myPen.setWidth(1)
                myPen.setCapStyle(Qt.FlatCap)
                punto.setPen(myPen)
                brush = QBrush(QColor(pt_colour), style=Qt.SolidPattern)
                punto.setBrush(brush)
                self.circular.addItem(punto)

                datos +=1
                sum_dist += lon_feat

            try:
                #Start Raster
                #anc_grilla=int(2*radius)
                anc_grilla=10    
                grilla = np.zeros((anc_grilla, anc_grilla), dtype=int)
                centro = anc_grilla // 2
                for lon, az in zip(list_lon, list_aci_o):
                    theta = np.radians(az)
                    x = centro + int(np.sin(theta) * lon * (centro/max_total))
                    y = centro - int(np.cos(theta) * lon * (centro/max_total))
                    if x==anc_grilla:
                        x-=1
                    if y==anc_grilla:
                        y-=1
                    if 0 <= x < anc_grilla and 0 <= y < anc_grilla:
                        grilla[y, x] += 1
                
                # --- Preparar datos dispersos para interpolación ---
                y_idxs, x_idxs = np.nonzero(grilla)
                values = grilla[y_idxs, x_idxs]

                # Crear rejilla regular para interpolar (igual tamaño)
                grid_x, grid_y = np.mgrid[0:anc_grilla, 0:anc_grilla]

                # Aplicar interpolación cúbica
                interp_grid = griddata(
                    points=(x_idxs, y_idxs), 
                    values=values, 
                    xi=(grid_x, grid_y), 
                    method='linear'
                )

                interp_grid=np.transpose(interp_grid)

                # Llenar valores NaN resultantes por 0 para evitar errores
                interp_grid = np.nan_to_num(interp_grid, nan=0)


                # --- Normalización logarítmica ---
                norm = np.log1p(np.maximum(interp_grid, 0))
                ptp_val = np.ptp(norm)
                if ptp_val == 0 or np.isnan(ptp_val):
                    ptp_val = 1  # evita NaN

                norm = 255 * (norm - np.min(norm)) / ptp_val
                norm = np.clip(norm, 0, 255).astype(np.uint8)
                """

                norm = interp_grid.astype(np.uint8)
                """
                # --- Crear imagen QImage (igual que antes) ---
                h, w = norm.shape
                img = QImage(w, h, QImage.Format_RGB32)

                primer_cuartil = int(np.quantile(norm, 0.999))

                # Aquí código para asignar colores a los pixeles, si tienes la función valor_a_color, úsala:
                for i in range(h):
                    self.progressBar.setValue(int(60*((i+1)/(h))))
                    for j in range(w):
                        v = norm[i, j]
                        color = self.valor_a_color(v, primer_cuartil)  # O cualquier función que tengas para el color
                        img.setPixel(j, i, color.rgb())

                # Convertir a imagen
                pixmap = QPixmap.fromImage(img)

                nuevo_ancho = int((radius)/anc_grilla)*25
                nuevo_alto = int((radius)/anc_grilla)*25
                
                pixmap_esc = pixmap.scaled(
                    nuevo_ancho,
                    nuevo_alto,
                    Qt.KeepAspectRatio,         # Opcional: mantiene la proporción original
                    Qt.SmoothTransformation     # Opcional: calidad de escalado suave
                )

                # Mostrar en QGraphicsScene:
                item = QGraphicsPixmapItem(pixmap_esc)
                item.setOpacity(0.4)  # Opcional, para superponer otros gráficos

                raster_width = pixmap_esc.width()
                raster_height = pixmap_esc.height()

                # Calcular la esquina superior izquierda para centrar la imagen
                pos_x = start.x() - nuevo_ancho / 2 - (anc_grilla*2)
                pos_y = start.y() - nuevo_alto / 2 - (anc_grilla*2)

                item.setPos(pos_x, pos_y)
                item.setZValue(2)
                self.circular.addItem(item)
                # End raster
                # 
            except:
                texts = QGraphicsSimpleTextItem("Cannot display density scheme")
                pos=25
                texts.setPos(start.x() - pos,start.y() + radius + pos)
                color = QColor(0, 0, 0)
                myPen2 = QPen(color)
                texts.setPen(myPen2)
                self.circular.addItem(texts)
            else:
                texts = QGraphicsSimpleTextItem("Density scheme is shown")
                pos=25
                texts.setPos(start.x() - pos,start.y() + radius + pos)
                color = QColor(0, 0, 0)
                myPen2 = QPen(color)
                texts.setPen(myPen2)
                self.circular.addItem(texts)

            self.progressBar.setValue(70)

            if sum_out>0:
                self.rem_out.setEnabled(True)

                #Draw a probability circle of the outliers
                
                circ=m2_desv*(radius/max_total)
                circle = QGraphicsEllipseItem(start.x() - circ, start.y() - circ, circ*2, circ*2)
                circle.setPen(QPen(ringcolour))
                self.circular.addItem(circle)

                texts = QGraphicsSimpleTextItem("Outlier")
                pos=((2**0.5)/2)*circ*1.1
                texts.setPos(start.x() + pos,start.y() + pos)
                deg_medcolour2 = QColor(0, 0, 0)
                myPen2 = QPen(deg_medcolour2)
                texts.setPen(myPen2)
                self.circular.addItem(texts)
            else:
                self.rem_out.setEnabled(False)

            # Horizontal
            linea_deg = QGraphicsLineItem(start.x()-radius, start.y(), start.x()+radius, start.y())            
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_deg.setPen(myPen2)
            self.circular.addItem(linea_deg)

            # Vertical
            linea_deg = QGraphicsLineItem(start.x(), start.y()-radius, start.x(), start.y() +radius)            
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_deg.setPen(myPen2)
            self.circular.addItem(linea_deg)

            # Donw
            linea_deg = QGraphicsLineItem(start.x()-radius, start.y()+radius, start.x()+radius, start.y()+radius)            
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_deg.setPen(myPen2)
            self.circular.addItem(linea_deg)

            #Up
            linea_deg = QGraphicsLineItem(start.x()-radius, start.y()-radius, start.x()-radius, start.y()+radius)            
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_deg.setPen(myPen2)
            self.circular.addItem(linea_deg)

            # Text Horizontal
            texts = QGraphicsSimpleTextItem("0")
            pos=5
            texts.setPos(start.x()-pos/2,start.y()+radius + pos)
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)

            # Text Vertical
            texts = QGraphicsSimpleTextItem("0")
            pos=10
            texts.setPos(start.x()-radius-pos,start.y()-pos)
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)

            # Texto Vertical Donw
            texts = QGraphicsSimpleTextItem(str(int(-max_total)))
            pos=5
            texts.setPos(start.x()-radius-pos*2,start.y()+radius-pos)
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)

            # Text Vertical Up
            texts = QGraphicsSimpleTextItem(str(int(max_total)))
            pos=5
            texts.setPos(start.x()-radius-pos*2,start.y()-radius-pos/2)
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)

            # Text Horizontal Right
            texts = QGraphicsSimpleTextItem(str(int(max_total)))
            pos=5
            texts.setPos(start.x()+radius+pos*1.5,start.y()+radius+pos)
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)

            # Text Horizontal Down
            texts = QGraphicsSimpleTextItem(str(int(-max_total)))
            pos=5
            texts.setPos(start.x()-radius-pos*1.5,start.y()+radius+pos)
            deg_medcolour2 = self.Color_bin.color()
            myPen2 = QPen(deg_medcolour2)
            texts.setPen(myPen2)
            self.circular.addItem(texts)

            self.progressBar.setValue(80)

            az_med_t = az_med*(180/math.pi)

            lon_max=radius
                
            pos_y = (math.cos(az_med_t*math.pi/180))*lon_max
            pos_x = (math.sin(az_med_t*math.pi/180))*lon_max
            
            # Draw the azimuth on the unit circle
            if self.az_mean_c.checkState():
                linea_az = QGraphicsLineItem(start.x(), start.y(), start.x()+pos_x, start.y()-pos_y)
                az_medcolour = self.Color_mean.color()
                myPen = QPen(az_medcolour)
                myPen.setWidth(2)
                myPen.setCapStyle(Qt.FlatCap)
                linea_az.setPen(myPen)
                self.circular.addItem(linea_az)


            # Draw the standard deviation in the graphical output
            az_med_i=az_med_t-des_cir
            if az_med_i<0:
                az_med_i=360+az_med_i
            az_med_s=az_med_t+des_cir
            if az_med_s>360:
                az_med_s=az_med_s-360


            self.progressBar.setValue(90)
            #Draw the circular standard deviation in pie chart format.
            trans=(self.trans_desv.value())/100
            if self.des_cir_c.isChecked():       
                circle2 = QGraphicsEllipseItem(start.x() - radius,start.y() - radius,radius * 2,radius * 2)
                circle2.setStartAngle(int((360-az_med_i+90-(des_cir*2))*16))
                circle2.setSpanAngle(int((des_cir*2)*16))   
                circle2.setPen(QPen(ringcolour2))
                ringcolour2.setAlphaF(trans)
                circle2.setBrush((ringcolour2))
                self.circular.addItem(circle2)

        else:
            datos=0
            self.rem_out.setEnabled(False)
            text2 = QGraphicsSimpleTextItem(str("No Data"))
            text2.setPos(start.x(),start.y())
            self.circular.addItem(text2) 

        #Text configuration in graphic output
        title = QGraphicsSimpleTextItem("Density graph")
        title.setPos(10,10)
        self.circular.addItem(title)

        self.progressBar.setValue(100)
        self.bt_restart.setEnabled(True)

    # Function to reinitialize the plugin
    def rest(self):
        self.circular.clear()
        self.grafic.viewport().update()

        #Text wait for load graphics
        title = QGraphicsSimpleTextItem("Processing... wait")
        title.setPos(3,3)
        self.circular.addItem(title)

        self.progressBar.setValue(0)
        # Reset the plugin UI and clear all variables and inputs
        self.Layer_E1.setCurrentIndex(-1)
        self.Layer_F1.setCurrentIndex(-1)
        self.Layer_E2.setCurrentIndex(-1)
        self.Layer_F2.setCurrentIndex(-1)
        self.Layer_E3.setCurrentIndex(-1)
        self.Layer_F3.setCurrentIndex(-1)        
        self.Layer_E4.setCurrentIndex(-1)
        self.Layer_F4.setCurrentIndex(-1)
        self.Layer_E5.setCurrentIndex(-1)
        self.Layer_F5.setCurrentIndex(-1)

        Layer_E1 = self.Layer_E1.currentLayer()
        Layer_F1 = self.Layer_F1.currentLayer()
        Layer_E2 = self.Layer_E2.currentLayer()
        Layer_F2 = self.Layer_F2.currentLayer()
        Layer_E3 = self.Layer_E3.currentLayer()
        Layer_F3 = self.Layer_F3.currentLayer()
        Layer_E4 = self.Layer_E4.currentLayer()
        Layer_F4 = self.Layer_F4.currentLayer()
        Layer_E5 = self.Layer_E5.currentLayer()
        Layer_F5 = self.Layer_F5.currentLayer()

        # Disable all layers and buttons
        self.Layer_E1.setEnabled(True)
        self.Layer_F1.setEnabled(True)
        self.Layer_E2.setEnabled(False)
        self.Layer_F2.setEnabled(False)
        self.Layer_E3.setEnabled(False)
        self.Layer_F3.setEnabled(False)
        self.Layer_E4.setEnabled(False)
        self.Layer_F4.setEnabled(False)
        self.Layer_E5.setEnabled(False)
        self.Layer_F5.setEnabled(False)

        root2 = QgsProject.instance().layerTreeRoot()
        grupo2 = (root2.findGroup("Temporal"))

        for child in grupo2.children():
            capa=QgsProject.instance().mapLayersByName(child.name())
            QgsProject.instance().removeMapLayer(capa[0].id())

        # Clear tables
        #self.cde.clear()
        self.data.clear()
        if len(imagen)>0:
            # Clear previous graphical
            imagen.clear()
        
        self.bt_restart.setEnabled(False)
        self.Boton1.setEnabled(False)
        self.tabWidget.setTabEnabled(0,True)
        self.tabWidget.setTabEnabled(1,False)
        self.tabWidget.setTabEnabled(2,False)
        self.tabWidget.setTabEnabled(3,False)
        self.tabWidget.setTabEnabled(4,False)
        self.tabWidget.setCurrentIndex(0)
        var_rest="SI"

        # Deletes upload information from uploaded data sets
        self.Tab_start.clear()

        # Clears loading information from the comparison between data sets
        self.Tab_ver.clear()

        resul_1 = "Data Number: -"
        self.num_d.setText(resul_1)
        resul_1 = "Mean Azimuth: <b>-° -' -''</b>"
        self.az_mean_t.setText(resul_1)
        resul_7 = "Median Azimuth: <b>-° -' -''</b>"
        self.az_median_t.setText(resul_7)
        resul_7 = "Mode Azimuth: <b>-° -' -''</b>"
        self.az_mode_t.setText(resul_7)
        resul_2 = "Length of Mean Vector: <b>-</b>"
        self.mod_med_t.setText(resul_2)
        resul_3 = "Circular Variance: <b>-</b>"
        self.var_cir_t.setText(resul_3)
        resul_4 = "Circular Standard Deviation (Degree):<br> <b>-° -' -''</b>"
        self.des_cir_t.setText(resul_4)
        resul_13 = f"Angular Variance: <b>-</b>"
        self.var_ang_t.setText(resul_13)
        resul_4 = "Von Mises Concentration Parameter:<br> <b>-</b>"
        self.par_k_t.setText(resul_4)
        resul_5 = "Angular Standard Deviation:<br> <b>-° -' -''</b>"
        self.des_ang_t.setText(resul_5)
        resul_6 = "Mean Angular Deviation:<br> <b>-° -' -''</b>"
        self.des_angm_t.setText(resul_6)
        resul_7 = "Skewness Coefficient (Asimetry or bias): <br> <b>-</b>"
        self.skew_t.setText(resul_7)
        resul_8 = "Kurtosis Coefficient (Peakedness): <br> <b>-</b>"
        self.curt_t.setText(resul_8)
        resul_9 = "Circular Dispersion: <b>-''</b>"
        self.disp_cir_t.setText(resul_9)
        resul_10 = "Mean Error: <b>-</b>"
        self.emh_t.setText(resul_10)
        resul_11 = "Standard Deviation: <br> <b>-</b>"
        self.dsh_t.setText(resul_11)
        resul_11 = "Circular Standard Deviation: <br> <b>-</b>"
        self.dsc_t.setText(resul_11)
        resul_12 = "Potencial Outlier (>): <b>-</b>"
        self.pot_out_t.setText(resul_12)
        resul_12 = "Total Outlier: <b>-</b>"
        self.tot_out_t.setText(resul_12)


    # Function to remove outliers
    def rem_outliers(self):
        self.circular.clear()
        self.grafic.viewport().update()

        #Text wait for load graphics
        title = QGraphicsSimpleTextItem("Processing... wait")
        title.setPos(3,3)
        self.circular.addItem(title)

        act_cde = self.cde.currentText()
        if act_cde=="All":
            for j in range(len(lista_cde)):
                self.progressBar.setValue(int(100*((j+1)/(len(lista_cde)))))
                cd_selec = project.mapLayersByName(lista_cde[j])[0]
                for i in cd_selec.getFeatures():
                    attrs=i.attributes()
                    lon_feat = attrs[6]
                    azim_feat = attrs[7]
                    dnorte = (((math.cos(azim_feat*math.pi/180))*lon_feat)-norte_med)**2
                    deste = (((math.sin(azim_feat*math.pi/180))*lon_feat)-este_med)**2
                    res=(dnorte+deste)**0.5
                    if res>=m2_desv:
                        cd_selec.dataProvider().deleteFeatures([i.id()])
                        cd_selec.updateFeature(i)

        else:
            cd_selec = project.mapLayersByName(str(act_cde))[0]
            for i in cd_selec.getFeatures():
                attrs=i.attributes()
                lon_feat = attrs[6]
                azim_feat = attrs[7]
                dnorte = (((math.cos(azim_feat*math.pi/180))*lon_feat)-norte_med)**2
                deste = (((math.sin(azim_feat*math.pi/180))*lon_feat)-este_med)**2
                res=(dnorte+deste)**0.5
                if res>=m2_desv:
                    cd_selec.dataProvider().deleteFeatures([i.id()])
                    cd_selec.updateFeature(i)

        self.proc_data()
        
        self.b_undo.setEnabled(True)


    # Function to reinitialize the plugin, return all data without eliminating outliers
    def f_undo(self):
        self.circular.clear()
        self.grafic.viewport().update()

        #Text wait for load graphics
        title = QGraphicsSimpleTextItem("Processing... wait")
        title.setPos(3,3)
        self.circular.addItem(title)

        self.cde.clear()

        root2 = QgsProject.instance().layerTreeRoot()
        grupo2 = (root2.findGroup("Temporal"))

        for child in grupo2.children():
            capa=QgsProject.instance().mapLayersByName(child.name())
            if "Error" in capa[0].name():
                QgsProject.instance().removeMapLayer(capa[0].id())

        self.paso3()

    # Function to graph the module histogram
    def hist_mod(self):
        self.result=1
        self.clas_mod.setEnabled(True)
        self.red_mode_s.setEnabled(False)
        clas=self.clas_mod.value()
        act_cde = self.cde.currentText()
        self.az_mean_c.setEnabled(False)
        self.des_cir_c.setEnabled(False)
        self.cde.setEnabled(True)

        self.progressBar.setValue(10)
        self.circular.clear()
        self.grafic.viewport().update()

        cant=len(list_lon)
        datos=cant

        self.num_d.setText("Data Number: "+str(datos))

        viewprect = QRectF(self.grafic.viewport().rect())
        ventana=viewprect
        self.grafic.setSceneRect(viewprect)
        
        left = self.grafic.sceneRect().left()
        right = self.grafic.sceneRect().right()
        width = right - left
        top = self.grafic.sceneRect().top()
        bottom = self.grafic.sceneRect().bottom()
        height = (bottom - top)

        numrings=self.anillos.value()

        size = width
        if width > height:
            size = height
        padding = 15
        maxlength = (size / 2) - padding * 2
        center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
        # The scene geomatry of the center point
        start = QPointF(self.grafic.mapToScene(center))
        radius = maxlength

        if cant>0:
            lon_feat_max=max(list_lon)
            rang=lon_feat_max/clas

            frecuencias, extremos = np.histogram(list_lon, bins=clas)

            size = width
            if width > height:
                size = height
            padding = 15
            maxlength = (size / 2) - padding * 2

            center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
            # The scene geomatry of the center point
            start = QPointF(self.grafic.mapToScene(center))

            ancho=maxlength
            height = (bottom - top)*0.90
            alto=height-(height*0.02)
            alto2=(height/2.1)

            x0=0
            y0=2*alto2
            t=0
            x=0
            y=0
            points=[]
            points.clear()

            max_frec=max(frecuencias)

            for i in frecuencias:
                self.progressBar.setValue(int(50*((t+1)/(len(frecuencias)))))

                x = t*2*ancho/clas
                y = frecuencias[t]*(2*alto2)/max_frec

                linea_quan = QGraphicsLineItem(start.x()-ancho+x0, start.y()-y0+alto2, start.x()-ancho+x, start.y()-y+alto2)            
                colour = self.Color_line.color()
                myPen2 = QPen(colour)
                myPen2.setWidth(1)
                myPen2.setCapStyle(Qt.FlatCap)
                linea_quan.setPen(myPen2)
                self.circular.addItem(linea_quan)
                x0=x
                y0=y
                t +=1

                linea_frec = QGraphicsLineItem(start.x()-ancho+x, start.y()+alto2, start.x()-ancho+x, start.y()-y+alto2)            
                colour = self.Color_dot.color()
                myPen2 = QPen(colour)
                myPen2.setWidth(int(4+(1/(clas/100))))
                myPen2.setCapStyle(Qt.FlatCap)
                linea_frec.setPen(myPen2)
                self.circular.addItem(linea_frec)

                points.append(QPointF(start.x()-ancho+x, start.y()-y+alto2))

            """

            #It is required one slice draw
            x1 = np.array([p.x() if hasattr(p, 'x') else p[0] for p in points])
            y1 = np.array([p.y() if hasattr(p, 'y') else p[1] for p in points])

            # Domin new fpr interpolation smoth
            xnew = np.linspace(x1[0], x1[-1], 20)
            spl = make_interp_spline(x1, y1, k=3)
            ynew = spl(xnew)

            # Create new QPainterPath smoth
            smooth_path = QPainterPath(QPointF(xnew[0], ynew[0]))
            for xx, yy in zip(xnew[1:], ynew[1:]):
                smooth_path.lineTo(QPointF(xx, yy))

            # Draw smoth
            item_path = QGraphicsPathItem(smooth_path)
            colour = self.Color_line.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(2)
            item_path.setPen(myPen2)
            item_path.setZValue(2)
            self.circular.addItem(item_path)
            """    

            # Draw the Vertical Lines on the graph
            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2, start.x()-ancho, start.y()-alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+(x/4), start.y()+alto2, start.x()-ancho+(x/4), start.y()-alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+x, start.y()+alto2, start.x()-ancho+x, start.y()-alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+(3*x/4), start.y()+alto2, start.x()-ancho+(3*x/4), start.y()-alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+(x/2), start.y()+alto2, start.x()-ancho+(x/2), start.y()-alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            # Draw the horizontal lines on the graph
            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2, start.x()-ancho+x, start.y()+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()-alto2, start.x()-ancho+x, start.y()-alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y(), start.x()-ancho+x, start.y())            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+(alto2/2), start.x()-ancho+x, start.y()+(alto2/2))            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)        

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()-(alto2/2), start.x()-ancho+x, start.y()-(alto2/2))            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)  

            # Generate the texts in the grid in the graph
            text2 = QGraphicsSimpleTextItem(str(0))
            text2.setPos(start.x() - ancho,start.y()+8+alto2)
            self.circular.addItem(text2)     

            text2 = QGraphicsSimpleTextItem(str(int(extremos[-1])))
            text2.setPos(start.x() - ancho + x -10,start.y()+8+alto2)
            self.circular.addItem(text2)     

            text2 = QGraphicsSimpleTextItem(str(int(extremos[-1]/4)))
            text2.setPos(start.x() - ancho + (x/4)-10,start.y()+8+alto2)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(int(extremos[-1]/2)))
            text2.setPos(start.x() - ancho + (x/2)-10,start.y()+8+alto2)
            self.circular.addItem(text2)     

            text2 = QGraphicsSimpleTextItem(str(int(extremos[-1]*0.75)))
            text2.setPos(start.x() - ancho + (3*x/4)-10,start.y()+8+alto2)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str("Distance"))
            text2.setPos(start.x(),start.y()+alto2+18)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(0))
            text2.setPos(start.x() - ancho - 20 ,start.y()+alto2)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(int(max_frec*0.25)))
            text2.setPos(start.x() - ancho - 20 ,start.y()+(alto2/2))
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(int(max_frec*0.5)))
            text2.setPos(start.x() - ancho - 20 ,start.y())
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(int(max_frec*0.75)))
            text2.setPos(start.x() - ancho - 20 ,start.y()-(alto2/2))
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(max_frec))
            text2.setPos(start.x() - ancho - 20 ,start.y()-alto2)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str("Frecuency"))
            text2.setPos(start.x() - ancho - 30 ,start.y()-20)
            text2.setRotation(270)
            self.circular.addItem(text2) 

            self.progressBar.setValue(80)

            if sum_out>0:
                self.rem_out.setEnabled(True)
        else:
            text2 = QGraphicsSimpleTextItem(str("No Data"))
            text2.setPos(start.x(),start.y())
            self.circular.addItem(text2) 
            self.rem_out.setEnabled(False)

            resul_1 = "Data Number: -"
            self.num_d.setText(resul_1)
            resul_1 = "Mean Azimuth: <b>-° -' -''</b>"
            self.az_mean_t.setText(resul_1)
            resul_7 = "Median Azimuth: <b>-° -' -''</b>"
            self.az_median_t.setText(resul_7)
            resul_7 = "Mode Azimuth: <b>-° -' -''</b>"
            self.az_mode_t.setText(resul_7)
            resul_2 = "Length of Mean Vector: <b>-</b>"
            self.mod_med_t.setText(resul_2)
            resul_3 = "Circular Variance: <b>-</b>"
            self.var_cir_t.setText(resul_3)
            resul_4 = "Circular Standard Deviation (Degree):<br> <b>-° -' -''</b>"
            self.des_cir_t.setText(resul_4)
            resul_13 = f"Angular Variance: <b>-</b>"
            self.var_ang_t.setText(resul_13)
            resul_4 = "Von Mises Concentration Parameter:<br> <b>-</b>"
            self.par_k_t.setText(resul_4)
            resul_5 = "Angular Standard Deviation:<br> <b>-° -' -''</b>"
            self.des_ang_t.setText(resul_5)
            resul_6 = "Mean Angular Deviation:<br> <b>-° -' -''</b>"
            self.des_angm_t.setText(resul_6)
            resul_7 = "Skewness Coefficient (Asimetry or bias): <br> <b>-</b>"
            self.skew_t.setText(resul_7)
            resul_8 = "Kurtosis Coefficient (Peakedness): <br> <b>-</b>"
            self.curt_t.setText(resul_8)
            resul_9 = "Circular Dispersion: <b>-''</b>"
            self.disp_cir_t.setText(resul_9)
            resul_10 = "Mean Error: <b>-</b>"
            self.emh_t.setText(resul_10)
            resul_11 = "Standard Deviation: <br> <b>-</b>"
            self.dsh_t.setText(resul_11)
            resul_11 = "Circular Standard Deviation: <br> <b>-</b>"
            self.dsc_t.setText(resul_11)
            resul_12 = "Potencial Outlier (>): <b>-</b>"
            self.pot_out_t.setText(resul_12)
            resul_12 = "Total Outlier: <b>-</b>"
            self.tot_out_t.setText(resul_12)

        title = QGraphicsSimpleTextItem("Distance Histogram")
        title.setPos(10,10)
        self.circular.addItem(title)
        self.progressBar.setValue(100)

    # Function to graph the asimetric and kurtosis
    def asi_cur(self):
        self.result=1
        act_cde = self.cde.currentText()
        self.circular.clear()
        self.grafic.viewport().update()
        
        self.az_mean_c.setEnabled(False)
        self.des_cir_c.setEnabled(False)
        self.cde.setEnabled(True)

        datos=len(list_aci_e)

        self.progressBar.setValue(10)
        
        self.num_d.setText("Data Number: "+str(datos))

        # Draw the azimuth on the unit circle
        az_med_t = az_med*(180/math.pi)

        if len(list_aci_e)>0:
            az_max=max(list_aci_e)
            az_min=min(list_aci_e)

            clas=360

            frecuencias, extremo = np.histogram(list_aci_e, bins=clas, range=(0,360))

            extremos = np.round(extremo, decimals=0)

            max_frec=max(frecuencias)

            viewprect = QRectF(self.grafic.viewport().rect())
            ventana=viewprect
            self.grafic.setSceneRect(viewprect)

            left = self.grafic.sceneRect().left()
            right = self.grafic.sceneRect().right()
            width = right - left
            top = self.grafic.sceneRect().top()
            bottom = self.grafic.sceneRect().bottom()
            height = bottom - top

            size = width
            if width > height:
                size = height
            padding = 15
            maxlength = (size / 2) - padding * 2

            ancho=maxlength
            alto=(height/2.5)
            alto2=2*alto

            center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
            # The scene geomatry of the center point
            start = QPointF(self.grafic.mapToScene(center))

            self.progressBar.setValue(30)

            self.circular.clear()
            self.grafic.viewport().update()
            
            linea_base = QGraphicsLineItem(start.x()-ancho, start.y()+alto, start.x()+ancho, start.y()+alto)            
            colour2 = self.Color_bin.color()
            myPen2 = QPen(colour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_base.setPen(myPen2)
            linea_base.setZValue(2)
            self.circular.addItem(linea_base)

            linea_base = QGraphicsLineItem(start.x()-ancho, start.y()-alto2+alto, start.x()+ancho, start.y()-alto2+alto)            
            colour2 = self.Color_bin.color()
            myPen2 = QPen(colour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_base.setPen(myPen2)
            linea_base.setZValue(2)
            self.circular.addItem(linea_base)

            linea_base = QGraphicsLineItem(start.x()-ancho, start.y()+alto, start.x()-ancho, start.y()-alto2+alto)            
            colour2 = self.Color_bin.color()
            myPen2 = QPen(colour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_base.setPen(myPen2)
            linea_base.setZValue(2)
            self.circular.addItem(linea_base)

            linea_base = QGraphicsLineItem(start.x()+ancho, start.y()+alto, start.x()+ancho, start.y()-alto2+alto)            
            colour2 = self.Color_bin.color()
            myPen2 = QPen(colour2)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_base.setPen(myPen2)
            linea_base.setZValue(2)
            self.circular.addItem(linea_base)



            inic_h=int(az_med_t)-180
            if inic_h<0:
                inic_h=360+inic_h

            fin_h=inic_h-1

            list_x=list()
            list_x.clear()
            for i in range(0,359):
                if (inic_h+i)<=359:
                    list_x.append(inic_h+i)
                else:
                    list_x.append((inic_h+i)-360)

            lista_ext = extremos.tolist()
            lista_ext.pop(0)
            list_fre=frecuencias.tolist()
            points=[]
            points.clear()

            cont=0
            for i in list_x:
                self.progressBar.setValue(int(70*((cont+1)/(len(extremos)))))

                x = -((ancho*cont/180)-ancho)

                if i in lista_ext:
                    pos = lista_ext.index(i)
                    y = list_fre[pos]*alto2/max_frec

                    linea_frec = QGraphicsLineItem(start.x()-x, start.y()+alto, start.x()-x, start.y()-y+alto)            
                    colour = self.Color_dot.color()
                    myPen2 = QPen(colour)
                    myPen2.setWidth(1)
                    myPen2.setCapStyle(Qt.FlatCap)
                    linea_frec.setPen(myPen2)
                    self.circular.addItem(linea_frec)

                    points.append(QPointF(start.x()-x, start.y()-y+alto))

                    if i==int(az_med_t):
                        linea_mean = QGraphicsLineItem(start.x()-x, start.y()+alto, start.x()-x, start.y()-alto)            
                        colour2 = self.Color_mean.color()
                        myPen2 = QPen(colour2)
                        myPen2.setWidth(2)
                        myPen2.setCapStyle(Qt.FlatCap)
                        linea_mean.setPen(myPen2)
                        linea_mean.setZValue(2)
                        self.circular.addItem(linea_mean)

                        text2 = QGraphicsSimpleTextItem(str(int(az_med_t)))
                        text2.setPos(start.x()-4-x,start.y()+8+alto)
                        self.circular.addItem(text2)
                cont+=1

            x = np.array([p.x() if hasattr(p, 'x') else p[0] for p in points])
            y = np.array([p.y() if hasattr(p, 'y') else p[1] for p in points])

            # Domin new fpr interpolation smoth
            xnew = np.linspace(x[0], x[-1], 20)
            spl = make_interp_spline(x, y, k=3)
            ynew = spl(xnew)

            # Create new QPainterPath smoth
            smooth_path = QPainterPath(QPointF(xnew[0], ynew[0]))
            for xx, yy in zip(xnew[1:], ynew[1:]):
                smooth_path.lineTo(QPointF(xx, yy))

            # Draw smoth
            item_path = QGraphicsPathItem(smooth_path)
            colour = self.Color_line.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(2)
            item_path.setPen(myPen2)
            item_path.setZValue(2)
            self.circular.addItem(item_path)

            text2 = QGraphicsSimpleTextItem(str(inic_h))
            text2.setPos(start.x()-ancho-4,start.y()+8+alto)
            self.circular.addItem(text2)

            pos=int(len(list_x)/4)
            text2 = QGraphicsSimpleTextItem(str(list_x[pos]))
            text2.setPos(start.x()-(ancho/2)-4,start.y()+8+alto)
            self.circular.addItem(text2)

            pos=int(len(list_x)*0.75)
            text2 = QGraphicsSimpleTextItem(str(list_x[pos]))
            text2.setPos(start.x()+(ancho/2)-4,start.y()+8+alto)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem(str(fin_h))
            text2.setPos(start.x()+ancho-4,start.y()+8+alto)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem("Direction (deg)")
            text2.setPos(start.x()-30,start.y()+20+alto)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem("Frequency")
            text2.setPos(start.x()-ancho-30,start.y())
            text2.setRotation(270)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem("0")
            rect = text2.boundingRect()
            text2.setTransformOriginPoint(0, rect.height()/2)
            text2.setPos(start.x()-ancho-8-rect.width(), start.y()+alto-5)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem(str(max_frec))
            rect = text2.boundingRect()
            text2.setTransformOriginPoint(0, rect.height()/2)
            text2.setPos(start.x()-ancho-8-rect.width(), start.y()-alto2+alto-5)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem(str(int(max_frec/2)))
            rect = text2.boundingRect()
            text2.setTransformOriginPoint(0, rect.height()/2)
            text2.setPos(start.x()-ancho-8-rect.width(), start.y()-alto2/2+alto-5)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem(str(int(max_frec/4)))
            rect = text2.boundingRect()
            text2.setTransformOriginPoint(0, rect.height()/2)
            text2.setPos(start.x()-ancho-8-rect.width(), start.y()-alto2/4+alto-5)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem(str(int(max_frec*3/4)))
            rect = text2.boundingRect()
            text2.setTransformOriginPoint(0, rect.height()/2)
            text2.setPos(start.x()-ancho-8-rect.width(), start.y()-alto2*3/4+alto-5)
            self.circular.addItem(text2)

            self.progressBar.setValue(90)

            if sum_out>0:
                self.rem_out.setEnabled(True)

        else:
            text2 = QGraphicsSimpleTextItem(str("No data"))
            text2.setPos(start.x(),start.y())
            self.circular.addItem(text2)
            self.rem_out.setEnabled(False)

            resul_1 = "Data Number: -"
            self.num_d.setText(resul_1)
            resul_1 = "Mean Azimuth: <b>-° -' -''</b>"
            self.az_mean_t.setText(resul_1)
            resul_7 = "Median Azimuth: <b>-° -' -''</b>"
            self.az_median_t.setText(resul_7)
            resul_7 = "Mode Azimuth: <b>-° -' -''</b>"
            self.az_mode_t.setText(resul_7)
            resul_2 = "Length of Mean Vector: <b>-</b>"
            self.mod_med_t.setText(resul_2)
            resul_3 = "Circular Variance: <b>-</b>"
            self.var_cir_t.setText(resul_3)
            resul_4 = "Circular Standard Deviation (Degree):<br> <b>-° -' -''</b>"
            self.des_cir_t.setText(resul_4)
            resul_13 = f"Angular Variance: <b>-</b>"
            self.var_ang_t.setText(resul_13)
            resul_4 = "Von Mises Concentration Parameter:<br> <b>-</b>"
            self.par_k_t.setText(resul_4)
            resul_5 = "Angular Standard Deviation:<br> <b>-° -' -''</b>"
            self.des_ang_t.setText(resul_5)
            resul_6 = "Mean Angular Deviation:<br> <b>-° -' -''</b>"
            self.des_angm_t.setText(resul_6)
            resul_7 = "Skewness Coefficient (Asimetry or bias): <br> <b>-</b>"
            self.skew_t.setText(resul_7)
            resul_8 = "Kurtosis Coefficient (Peakedness): <br> <b>-</b>"
            self.curt_t.setText(resul_8)
            resul_9 = "Circular Dispersion: <b>-''</b>"
            self.disp_cir_t.setText(resul_9)
            resul_10 = "Mean Error: <b>-</b>"
            self.emh_t.setText(resul_10)
            resul_11 = "Standard Deviation: <br> <b>-</b>"
            self.dsh_t.setText(resul_11)
            resul_11 = "Circular Standard Deviation: <br> <b>-</b>"
            self.dsc_t.setText(resul_11)
            resul_12 = "Potencial Outlier (>): <b>-</b>"
            self.pot_out_t.setText(resul_12)
            resul_12 = "Total Outlier: <b>-</b>"
            self.tot_out_t.setText(resul_12)

        title = QGraphicsSimpleTextItem("Skewness and Kurtosis (azimuth)")
        title.setPos(10,10)
        self.circular.addItem(title)
        self.progressBar.setValue(100)

    # Function to graph the qplot
    def qplotuni(self):
        self.result=1
        act_cde = self.cde.currentText()
        self.circular.clear()
        self.grafic.viewport().update()

        self.az_mean_c.setEnabled(False)
        self.des_cir_c.setEnabled(False)
        self.cde.setEnabled(True)

        lis_az=np.deg2rad(list_aci_o)
        self.progressBar.setValue(10)

        lis_az_ord=sorted(lis_az)
        cant=len(lis_az_ord)
        datos=cant
        self.num_d.setText("Data Number: "+str(datos))
        
        if cant>0:
            viewprect = QRectF(self.grafic.viewport().rect())
            ventana=viewprect
            self.grafic.setSceneRect(viewprect)

            left = self.grafic.sceneRect().left()
            right = self.grafic.sceneRect().right()
            width = right - left
            top = self.grafic.sceneRect().top()
            bottom = self.grafic.sceneRect().bottom()
            height = (bottom - top)

            size = width
            if width > height:
                size = height
            padding = 15
            maxlength = (size / 2) - padding * 2

            ancho=maxlength/1.05
            height = (bottom - top)*0.85
            alto=height-height*0.02
            alto2=(height/1.8)

            center = QPoint(int(left + (width / 2)),int(top + (height / 2)))
            # The scene geomatry of the center point
            start = QPointF(self.grafic.mapToScene(center))

            x0=0
            y0=0
            t=1
            x=0
            y=0

            for i in lis_az_ord:
                self.progressBar.setValue(int(70*((t+1)/(len(lis_az_ord)))))

                x = (2*ancho)*(t/(cant+1))
                y = alto*(i/(2*math.pi))

                linea_quan = QGraphicsLineItem(start.x()-ancho+x0, start.y()-y0+alto2, start.x()-ancho+x, start.y()-y+alto2)            
                colour = self.Color_line.color()
                myPen2 = QPen(colour)
                myPen2.setWidth(2)
                myPen2.setCapStyle(Qt.FlatCap)
                linea_quan.setPen(myPen2)
                self.circular.addItem(linea_quan)
                x0=x
                y0=y
                t +=1

            # Generate Uniform Trend Lines on the Chart
            linea_ten = QGraphicsLineItem(start.x()-ancho, start.y()+alto2, start.x()-ancho+x, start.y()-y+alto2)            
            colour = self.Color_mean.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(2)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_ten.setPen(myPen2)
            self.circular.addItem(linea_ten)

            # Generate Vertical Lines in the Chart
            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2, start.x()-ancho, start.y()-y+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+(x/4), start.y()+alto2, start.x()-ancho+(x/4), start.y()-y+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+x, start.y()+alto2, start.x()-ancho+x, start.y()-y+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+(3*x/4), start.y()+alto2, start.x()-ancho+(3*x/4), start.y()-y+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho+(x/2), start.y()+alto2, start.x()-ancho+(x/2), start.y()-y+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            # Generate horizontal lines in the graph
            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2, start.x()-ancho+x, start.y()+alto2)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2-(y/2), start.x()-ancho+x, start.y()+alto2-(y/2))            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2-y, start.x()-ancho+x, start.y()+alto2-y)            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2-(3*y/4), start.x()-ancho+x, start.y()+alto2-(3*y/4))            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)        

            linea_cua = QGraphicsLineItem(start.x()-ancho, start.y()+alto2-(y/4), start.x()-ancho+x, start.y()+alto2-(y/4))            
            colour = self.Color_bin.color()
            myPen2 = QPen(colour)
            myPen2.setWidth(1)
            myPen2.setCapStyle(Qt.FlatCap)
            linea_cua.setPen(myPen2)
            self.circular.addItem(linea_cua)  

            self.progressBar.setValue(80)

            # generate horizontal grid texts
            text2 = QGraphicsSimpleTextItem(str(0))
            text2.setPos(start.x() - ancho,start.y()+8+alto2)
            self.circular.addItem(text2)     

            text2 = QGraphicsSimpleTextItem(str(1))
            text2.setPos(start.x() - ancho + x,start.y()+8+alto2)
            self.circular.addItem(text2)     

            text2 = QGraphicsSimpleTextItem(str(0.50))
            text2.setPos(start.x() - ancho + (x/2)-10,start.y()+8+alto2)
            self.circular.addItem(text2)     

            text2 = QGraphicsSimpleTextItem(str(0.25))
            text2.setPos(start.x() - ancho + (x/4)-10,start.y()+8+alto2)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(0.75))
            text2.setPos(start.x() - ancho + (3*x/4)-10,start.y()+8+alto2)
            self.circular.addItem(text2) 

            # generate vertical grid texts
            text2 = QGraphicsSimpleTextItem(str(0))
            text2.setPos(start.x() - ancho - 20 ,start.y()+alto2-8)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(0.25))
            text2.setPos(start.x() - ancho - 20 ,start.y()+alto2-(y/4)-8)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(0.50))
            text2.setPos(start.x() - ancho - 20 ,start.y()+alto2-(y/2)-8)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(0.75))
            text2.setPos(start.x() - ancho - 20 ,start.y()+alto2-(3*y/4)-8)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem(str(1))
            text2.setPos(start.x() - ancho - 20 ,start.y()+alto2-y-8)
            self.circular.addItem(text2) 

            text2 = QGraphicsSimpleTextItem("Theoretical")
            text2.setPos(start.x()-30,start.y()+20+alto2)
            self.circular.addItem(text2)

            text2 = QGraphicsSimpleTextItem("Data")
            text2.setPos(start.x()-ancho-30,start.y())
            text2.setRotation(270)
            self.circular.addItem(text2)

            if sum_out>0:
                self.rem_out.setEnabled(True)

        else:
            text2 = QGraphicsSimpleTextItem(str("No Data"))
            text2.setPos(start.x(),start.y())
            self.circular.addItem(text2) 
            self.rem_out.setEnabled(False)

            resul_1 = "Data Number: -"
            self.num_d.setText(resul_1)
            resul_1 = "Mean Azimuth: <b>-° -' -''</b>"
            self.az_mean_t.setText(resul_1)
            resul_7 = "Median Azimuth: <b>-° -' -''</b>"
            self.az_median_t.setText(resul_7)
            resul_7 = "Mode Azimuth: <b>-° -' -''</b>"
            self.az_mode_t.setText(resul_7)
            resul_2 = "Length of Mean Vector: <b>-</b>"
            self.mod_med_t.setText(resul_2)
            resul_3 = "Circular Variance: <b>-</b>"
            self.var_cir_t.setText(resul_3)
            resul_4 = "Circular Standard Deviation (Degree):<br> <b>-° -' -''</b>"
            self.des_cir_t.setText(resul_4)
            resul_4 = "Von Mises Concentration Parameter:<br> <b>-</b>"
            self.par_k_t.setText(resul_4)
            resul_13 = f"Angular Variance: <b>-</b>"
            self.var_ang_t.setText(resul_13)
            resul_5 = "Angular Standard Deviation:<br> <b>-° -' -''</b>"
            self.des_ang_t.setText(resul_5)
            resul_6 = "Mean Angular Deviation:<br> <b>-° -' -''</b>"
            self.des_angm_t.setText(resul_6)
            resul_7 = "Skewness Coefficient (Asimetry or bias): <br> <b>-</b>"
            self.skew_t.setText(resul_7)
            resul_8 = "Kurtosis Coefficient (Peakedness): <br> <b>-</b>"
            self.curt_t.setText(resul_8)
            resul_9 = "Circular Dispersion: <b>-''</b>"
            self.disp_cir_t.setText(resul_9)
            resul_10 = "Mean Error: <b>-</b>"
            self.emh_t.setText(resul_10)
            resul_11 = "Standard Deviation: <br> <b>-</b>"
            self.dsh_t.setText(resul_11)
            resul_11 = "Circular Standard Deviation: <br> <b>-</b>"
            self.dsc_t.setText(resul_11)
            resul_12 = "Potencial Outlier (>): <b>-</b>"
            self.pot_out_t.setText(resul_12)
            resul_12 = "Total Outlier: <b>-</b>"
            self.tot_out_t.setText(resul_12)

        title = QGraphicsSimpleTextItem("Qplot Uniform Quantiles (azimuth)")
        title.setPos(10,10)
        self.circular.addItem(title)

        self.progressBar.setValue(100)

    # Function to download data to table tab
    def t_datos(self):

        self.result=1

        act_cde = self.cde.currentText()
        list_mod=list()
        list_mod.clear()
        list_aci=list()
        list_aci.clear()
        list_ne=list()
        list_ne.clear()
        list_ee=list()
        list_ee.clear()
        list_nr=list()
        list_nr.clear()
        list_er=list()
        list_er.clear()
        list_dn=list()
        list_dn.clear()
        list_de=list()
        list_de.clear()

        self.data.clear()
        # Clear table before inserting new data
        self.data.clearContents()
        self.data.setSortingEnabled(True)

        if len(act_cde)>0:
            if act_cde=="All":
                for j in range(len(lista_cde)):
                    self.progressBar.setValue(int(100*((j+1)/(len(lista_cde)))))
                    cd_selec = project.mapLayersByName(lista_cde[j])[0]
                    for i in cd_selec.getFeatures():
                        attrs=i.attributes()
                        c1 = attrs[0]
                        c2 = attrs[1]
                        c3 = attrs[2]
                        c4 = attrs[3]
                        c5 = attrs[4]
                        c6 = attrs[5]
                        c7 = attrs[6]
                        c8 = attrs[7]
                        list_ne.append(c1) 
                        list_ee.append(c2) 
                        list_nr.append(c3) 
                        list_er.append(c4) 
                        list_dn.append(c5) 
                        list_de.append(c6) 
                        list_mod.append(c7)
                        list_aci.append(c8)

            else:
                cd_selec = project.mapLayersByName(str(act_cde))[0]
                for i in cd_selec.getFeatures():
                    attrs=i.attributes()
                    c1 = attrs[0]
                    c2 = attrs[1]
                    c3 = attrs[2]
                    c4 = attrs[3]
                    c5 = attrs[4]
                    c6 = attrs[5]
                    c7 = attrs[6]
                    c8 = attrs[7]

                    list_ne.append(c1) 
                    list_ee.append(c2) 
                    list_nr.append(c3) 
                    list_er.append(c4) 
                    list_dn.append(c5) 
                    list_de.append(c6) 
                    list_mod.append(c7)
                    list_aci.append(c8)                    

            self.data.setRowCount(len(list_mod))
            self.data.setColumnCount(8)            
            self.data.setHorizontalHeaderItem(0, QTableWidgetItem("North Evaluated"))
            self.data.setHorizontalHeaderItem(1, QTableWidgetItem("East Evaluated"))
            self.data.setHorizontalHeaderItem(2, QTableWidgetItem("North Source"))
            self.data.setHorizontalHeaderItem(3, QTableWidgetItem("East Source"))
            self.data.setHorizontalHeaderItem(4, QTableWidgetItem("Δ North"))
            self.data.setHorizontalHeaderItem(5, QTableWidgetItem("Δ East"))
            self.data.setHorizontalHeaderItem(6, QTableWidgetItem("Distance"))
            self.data.setHorizontalHeaderItem(7, QTableWidgetItem("Azimuth"))
            data = QTableWidget()
            self.data.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
            
            x=0
            for i in list_aci:
                dist_red=round(list_mod[x],3)
                celda1 = QTableWidgetItem()
                celda1.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                if dist_red!=0:
                    celda1.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_mod[x])
                else:
                    celda1.setData(QtCore.Qt.DisplayRole, f"{list_mod[x]:.2e}")

                celda2 = QTableWidgetItem()
                celda2.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda2.setData(QtCore.Qt.DisplayRole, "%0.10f"% list_aci[x])

                celda3 = QTableWidgetItem()
                celda3.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda3.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_ne[x])

                celda4 = QTableWidgetItem()
                celda4.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda4.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_ee[x])

                celda5 = QTableWidgetItem()
                celda5.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda5.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_nr[x])

                celda6 = QTableWidgetItem()
                celda6.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda6.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_er[x])

                celda7 = QTableWidgetItem()
                celda7.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda7.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_dn[x])

                celda8 = QTableWidgetItem()
                celda8.setTextAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
                celda8.setData(QtCore.Qt.DisplayRole, "%0.3f"% list_de[x])

                self.data.setItem(x,0,celda3)
                self.data.setItem(x,1,celda4)
                self.data.setItem(x,2,celda5)
                self.data.setItem(x,3,celda6)
                self.data.setItem(x,4,celda7)
                self.data.setItem(x,5,celda8)
                self.data.setItem(x,6,celda1)
                self.data.setItem(x,7,celda2)
                x +=1 

    # function to Resize the viewport
    def resizeEvent(self, event):
        # self.showInfo("resizeEvent")
        if self.result is not None or var_rest!="":
            self.redraw()
        super().resizeEvent(event)

    # function to Download the points data.
    def hab_desc(self):
        if self.data_csv.filePath!="":
            self.descarga.setEnabled(True)

    # function to Download the points data.
    def desc_data(self):
        self.result=1
        act_cde = self.cde.currentText()
        
        # Prepare path and write CSV
        ruta=self.data_csv.filePath()
        self.data_csv.setSelectedFilter(".csv")

        csv_archivo = str(ruta)+".csv"

        fic = open(csv_archivo,'a')
        fic.close()
    
        f = open (csv_archivo, 'w')
        linea = "N_Eval,E_Eval,N_Source,E_Source,Delta_N,Delta_E,Distance,Azimuth\n"
        f.write(linea)

        if act_cde=="All":
            for j in range(len(lista_cde)):
                self.progressBar.setValue(int(100*((j+1)/(len(lista_cde)))))
                cd_selec = project.mapLayersByName(lista_cde[j])[0]
                for i in cd_selec.getFeatures():
                    attrs=i.attributes()
                    c1 = attrs[0]
                    c2 = attrs[1]
                    c3 = attrs[2]
                    c4 = attrs[3]
                    c5 = attrs[4]
                    c6 = attrs[5]
                    c7 = attrs[6]
                    c8 = attrs[7]
                    linea = f"{c1},{c2},{c3},{c4},{c5},{c6},{c7},{c8}\n"
                    f.write(linea)
        else:
            cd_selec = project.mapLayersByName(str(act_cde))[0]
            for i in cd_selec.getFeatures():
                attrs=i.attributes()
                c1 = attrs[0]
                c2 = attrs[1]
                c3 = attrs[2]
                c4 = attrs[3]
                c5 = attrs[4]
                c6 = attrs[5]
                c7 = attrs[6]
                c8 = attrs[7]
                linea = f"{c1},{c2},{c3},{c4},{c5},{c6},{c7},{c8}\n"
                f.write(linea)
        f.close()

        self.label_31.setText("<font style='color:#297500'><b>Successful download</b></font>")
        self.data_csv.setFilePath("")
        self.descarga.setEnabled(False) 

    # Download the results report
    def hab_info(self):
        if self.file_info.filePath!="":
            self.gen_info.setEnabled(True)

    # Function to generate the report
    def informe(self):
        fecha_info=self.fecha.date()
        ano=fecha_info.year()
        mes=fecha_info.month()
        dia=fecha_info.day()
        proj=self.project_t.toPlainText()
        self.result=1
        act_cde = self.cde.currentText()
        ruta=self.file_info.filePath()
        self.file_info.setSelectedFilter(".html")
        ruta_i=os.path.dirname(ruta)

        info_archivo = str(ruta)+".html"

        if len(imagen)>0:
            if not os.path.exists(ruta_i+'/Imagenes'):
                os.mkdir(ruta_i+'/Imagenes')
            j=1
            for i in imagen:
                nom_imag=ruta_i+'/Imagenes/graficas'+str(j)+'.svg'
                with open(nom_imag, "w", encoding="utf-8") as archivo:
                    archivo.write(i)
                j +=1

        fic = open(info_archivo,'a')
        fic.close()
    
        f = open (info_archivo, 'w')
        linea = "<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n<title>Quality Report - Qpositional</title>\n"
        linea += "<style type='text/css'>\nbody {font-family: arial; margin: 5%;min-height: 100vh; max-width: 80%}\n"
        linea += "table {border: 2px solid blue; border-collapse: collapse; font-family: arial; width: 80%;}\n"
        linea += "td {padding: 5px;text-align: center;}"
        linea += "font.over {text-decoration: overline;}"
        linea += "</style></head>\n<body>\n"
        linea += "<center><h2><i>QPositional</i></h2></center></p>\n"
        linea += "<b>Date:</b> "+str(dia)+"/"+str(mes)+"/"+str(ano)+"</p>\n"
        linea += "<b>Project:</b> "+proj+"</p>\n"


        linea +="<center><b>Summary</b></center></p>\n"

        linea += "<center><table border=1><tr><th>Dataset Evaluated</th><th>Dataset Source</th></tr>\n"
        fila = 0
        for registro in Layer_E:
            celda1 = registro.name()
            celda2 = Layer_F[fila].name()
            linea += f"<tr><td>{celda1}</td><td>{celda2}</td></tr>\n"
            fila +=1 
        
        linea += "</table></center></p>\n"

        linea +="</p>"
        linea +="<b><i>Circular Statistics (Azimuth)</i></b></p>\n"
        linea +="<b>Central Tendency</b><br>\n"

        minutos, grados = math.modf(az_med_t)
        segundos, minutos = math.modf(minutos*60)
        segundos = round(segundos*60,2)
        cen_seg=str(round(segundos-int(segundos),2))[1:4]

        linea += f"Mean Azimuth: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b><br>\n"
        linea += "<i>The direction <font class='over'>&theta;</font> of the vector resultant of &theta;<sub>1</sub>,..., &theta;<sub>n</sub> and is known as the mean direction (Fisher, 2000).</i><p>\n"

        minutos, grados = math.modf(az_median)
        segundos, minutos = math.modf(minutos*60)
        segundos = round(segundos*60,2)
        cen_seg=str(round(segundos-int(segundos),2))[1:4]

        linea += f"Median Azimuth: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b><br>\n"
        linea += "<i>The sample median on the circle is defined as follows: Suppose we are given a set of sample points on the unit circle. Any point P such that:<br>" 
        linea += "<b>1.</b> Half of the sample points are on each side of the diameter of the P point.<br>"
        linea += "<b>2.</b> The majority of the sample points are nearer to P. that is, the P point has minimum value obtained by the Angular Standard Deviation (Mardia median).<br>"
        linea += "Like in a linear case, for a sample of an odd size the median is an actual observation while for a sample of an even size the median is the midpoint (circular mean) of two consecutive observations. (Ratanaruamkam, S. (2006).</i><p>\n"

        red=self.red_mode_s.value()
        minutos, grados = math.modf(round(az_mode,red))
        segundos, minutos = math.modf(minutos*60)
        segundos = round(segundos*60,2)
        cen_seg=str(round(segundos-int(segundos),2))[1:4]

        linea += f"Mode Azimuth: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b><br>\n"
        linea += "<i>The sample modal direction  is the direction corresponding to the maximum concentration of the data. (More generally, any direction corresponding to a local maximum concentration of the data is a modal direction.).<br>"
        linea += "The  mode has been determined from the rose diagram as the midpoint of the cell with largest frequency. However, the modal group can vary considerably in a rose diagram, depending on the locations of cell boundaries "
        linea += "and on the amount of smoothing (classes numer), although this method also depends on rounding of continuous data. (Fisher, 2000).<br>"
        linea += "In this case, consider than the modal direction has been calculate for <font class='over'>R</font> > 0.5 (See Length of Mean Vector).</i><p>\n"

        linea +="<b>Dispersion</b><br>\n"
        linea += f"Length of Mean Vector: <b>{mod_med:.3f}</b><br>\n"
        linea += "<i>Range (0,1), <font class='over'>R</font> = 1 implies that all the data points are coincident. However, <font class='over'>R</font> = 0 does not imply uniform dispersion around the circle (Fisher, 2000).</i></p>\n"

        linea +=f"Circular Variance: <b>{var_cir:.3f}</b><br>\n"
        linea += "<i>Range (0,1), the smaller the value of the circular variance, the more concentrated the distribution. However, V = 1 does not necessarily imply a maximally dispersed distribution (Fisher, 2000).</i></p>\n"

        minutos, grados = math.modf(des_cir)
        segundos, minutos = math.modf(minutos*60)
        segundos = round(segundos*60,2)
        cen_seg=str(round(segundos-int(segundos),2))[1:4]
        linea += f"Circular Standard Deviation: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b><br>\n"
        linea += "<i>The square root of the sample circular variance by analogy with the linear standard deviation (Fisher, 2000).</i></p>\n"

        linea += f"Angular Variance: <b>{var_ang:.3f}</b><br>\n"
        linea += "<i>This can be considered a measure of dispersion, it's the analogy with the linear variance (Robert P. Mahan, 1991).</i><p>\n"

        minutos, grados = math.modf(desv_ang_med)
        segundos, minutos = math.modf(minutos*60)
        segundos = round(segundos*60,2)
        cen_seg=str(round(segundos-int(segundos),2))[1:4]
        linea += f"Mean Angular Deviation: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b><br>\n"
        linea +="<i>Taking the positive square root of angular variance. We can convert the angular deviation into degrees (Robert P. Mahan, 1991).<i><p>\n"

        minutos, grados = math.modf(desv_ang)
        segundos, minutos = math.modf(minutos*60)
        segundos = round(segundos*60,2)
        cen_seg=str(round(segundos-int(segundos),2))[1:4]
        linea += f"Angular Standard Deviation: <b>{grados:.0f}° {int(minutos):02d}' {int(segundos):02d}"+cen_seg+"''</b><br>\n"
        linea += "<i>This dispersion measure, corresponding to an angular measurement of the shortest arc that covers all the data, can be associated with the direction of the median (Fischer, 2000).</i></p>"


        linea += f"Circular Dispersion: <b>{disp_cir:.3f}</b><br>\n"
        linea += "<i>The circular dispersion plays an important role in calculating a confidence interval for a mean direction, and in comparing and combining several sample mean directions (Fisher, 2000).</i></p>\n"

        linea += f"Von Mises Concentration Parameter: <b>{par_k:.3f}</b><br>\n"
        linea += "<i>This is a symmetric unimodal distribution which is the most common model for unimodal samples of circular data (Fisher,2000).</i></p>\n"

        linea +="<b>Shape</b><br>\n"
        linea += f"Kurtosis Coefficient (Peakedness):  <b>{curt:.3f}</b><br>\n"
        linea += "<i>Data from a unimodal symmetric distribution such as the von Mises will tend to have sample kurtosis values around zero; more peaked distributions will tend to have positive sample kurtosis (Fisher, 2000).</i></p>\n"
        
        linea += f"Skewness Coefficient (Asimetry or Bias):  <b>{skew:.3f}</b><br>\n"
        linea += "<i>Measures for skewness and kurtosis are meaningful only for unimodal distributions.</i><p>\n"

        linea +="<b>Linear Statistics (Distance)</b></p>\n"
        linea += f"Mean Error: <b>{emh:.3f}</b><br>\n"
        linea += "It`s the arithmetical mean of the error distances.<p>"

        linea += f"Linear Standard Deviation:  <b>{desv_sta_l:.3f}</b><br>\n"
        linea += "<i>The Linear Standard Deviation of measured differences (Distance) between the tested product and the reference source, this represents a confidence level of 68.27% (Cihangir Akşit, E. 2010).</i></p>"
        
        linea += f"Circular Standard Deviation:  <b>{desv_sta_c:.3f}</b><br>\n"
        linea += "<i>This deviation considers a certain percentage of the error in the two axes E (X) and N (Y) of the error vectors, estimated for both components together, This represents a confidence level of 39.35% (Cihangir Akşit, E. 2010).</i></p>"
        
        linea += f"Potencial Outlier (>): <b>{m2_desv:.3f}</b><br>\n" 
        linea += "<i>A residual is considered to be a potential outlier (ie not part of the representative data set) if the absolute value of the residual is larger than a defined value. This value equates to the standard deviation of the observation multiplied by a statistical factor, M (Cihangir Akşit, E. 2010).</i></p>"
        
        linea += f"Total Outlier: <b>{sum_out:.0f}</b><br>\n"
        linea += "<i>The number of error vectors than their potential outlier is larger than the defined value.</i></p>"

        if self.idt.isChecked():
            linea += "<center><b>Error Vector</b></center></p>\n"
            linea += "<center><table border=1><tr><th>North Evaluated</th><th>East Evaluated</th><th>North Source</th><th>East Source</th><th>Δ North</th><th>Δ East</th><th>Distance</th><th>Azimuth</th></tr>\n"
            if act_cde=="All":
                for j in range(len(lista_cde)):
                    self.progressBar.setValue(int(100*((j+1)/(len(lista_cde)))))
                    cd_selec = project.mapLayersByName(lista_cde[j])[0]
                    for i in cd_selec.getFeatures():
                        attrs=i.attributes()
                        c1 = attrs[0]
                        c2 = attrs[1]
                        c3 = attrs[2]
                        c4 = attrs[3]
                        c5 = attrs[4]
                        c6 = attrs[5]
                        c7 = attrs[6]
                        dist_red=round(c7,3)
                        linea += f"<tr><td>{c1:.3f}</td><td>{c2:.3f}</td><td>{c3:.3f}</td><td>{c4:.3f}</td><td>{c5:.3f}</td><td>{c6:.3f}</td>"
                        if dist_red!=0:                        
                            linea += f"<td>{c7:.3f}"
                        else:
                            linea += f"<td>{c7:.2e}"
                        c8 = attrs[7]
                        linea += f"</td><td>{c8:.10f}</td></tr>\n"

            else:
                cd_selec = project.mapLayersByName(str(act_cde))[0]
                for i in cd_selec.getFeatures():
                    attrs=i.attributes()
                    c1 = attrs[0]
                    c2 = attrs[1]
                    c3 = attrs[2]
                    c4 = attrs[3]
                    c5 = attrs[4]
                    c6 = attrs[5]
                    c7 = attrs[6]
                    dist_red=round(c7,3)
                    linea += f"<tr><td>{c1:.3f}</td><td>{c2:.3f}</td><td>{c3:.3f}</td><td>{c4:.3f}</td><td>{c5:.3f}</td><td>{c6:.3f}</td>"
                    if dist_red!=0:                        
                        linea += f"<td>{c7:.3f}"
                    else:
                        linea += f"<td>{c7:.2e}"
                    c8 = attrs[7]
                    linea += f"</td><td>{c8:.10f}</td></tr>\n"

            linea += "</table></center></p>\n"

        if self.ilg.isChecked():
            if len(imagen)>0:
                j=1
                for n in imagen:
                    pixmap = ruta_i+'/Imagenes/graficas'+str(j)+'.svg'
                    linea += f"<img src='{pixmap}' /><br>\n"
                    j +=1

        linea += "</p><b><i>References</i></b><br>"
        linea += "Fisher, N. I. (2000). Statistical analysis of circular data (Transferred to digital printing). Cambridge, Mass.: Cambridge University Press.<br>"
        linea += "Mahan, R. P. (1991). Circular Statistical Methods: Applications in Spatial and Temporal Performance Analysis. United States Army Research Institute for the Behavioral and Social Sciences, Special Report 16.<br>"
        linea += "Cihangir Akşit, E. (2010). Evaluation of Land Maps, Aeronautical Charts and Digital Topographic Data. NATO.<br>"
        linea += "Ratanaruamkam, S. (2006). New Estimators of a Circular Median. Western Michigan University.<br>"

        f.write(linea)
        f.close()

        self.label_32.setText("<font style='color:#297500'><b>Successful download</b></font>")
        self.file_info.setFilePath("")
        self.gen_info.setEnabled(False)


    # Function to changed text 
    def camb_text(self):
        self.label_32.setText("") 
        self.label_31.setText("")        

    # Copy the graphical output to the clipboard
    def clip(self):
        width, height = 900, 900
        svg_bytes = QByteArray()
        buffer = QBuffer(svg_bytes)
        buffer.open(QBuffer.WriteOnly)
        svgGen = QSvgGenerator()
        svgGen.setOutputDevice(buffer)
        svgGen.setSize(QSize(width, height))
        svgGen.setViewBox(QRect(0, 0, width, height))
        svgGen.setResolution(100)

        painter = QPainter(svgGen)
        self.circular.render(painter)
        painter.end()
        
        buffer.close()
        svg_string = bytes(svg_bytes).decode('utf-8')     

        imagen.append(svg_string)
        self.ins_imag()
        
    # Save to SVG
    def saveassvg(self, location=None):
        savename = location
        settings = QSettings()
        key = '/UI/lastShapefileDir'
        if not isinstance(savename, basestring):
            outDir = settings.value(key)
            filter = 'SVG (*.svg)'
            savename, _filter = QFileDialog.getSaveFileName(self,"Save to SVG",outDir, filter)
            savename = unicode(savename)
        svgGen = QSvgGenerator()
        svgGen.setFileName(savename)
        width, height = 900, 900
        svgGen.setSize(QSize(int(width), int(height)))
        svgGen.setViewBox(QRect(0, 0, width, height))
        svgGen.setResolution(100)

        painter = QPainter(svgGen)
        self.circular.render(painter)
        painter.end()

        if savename:
            outDir = os.path.dirname(savename)
            settings.setValue(key, outDir)

    # Function to copy imagen in Clipboard
    def ins_imag(self):
        if len(imagen)>0:
            cant=len(imagen)
            self.ilg.setEnabled(True)
            text2=f"Include {cant} Graphics (Clipboard)"
            self.ilg.setText(text2)

    def cerrar(self):
        # Close the dialog window
        self.close()