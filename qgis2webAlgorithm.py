# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Process2Web
                                 A QGIS plugin
 Processing plugin for qgis2web
                              -------------------
        begin                : 2017-04-03
        copyright            : (C) 2017 by Tom Chadwin
        email                : tom.chadwin@nnpa.org.uk
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

from numbers import Number
from collections import OrderedDict
import traceback
from qgis.core import (QgsProject,
                       QgsMapLayer,
                       QgsVectorLayer,
                       QgsMessageLog)
from qgis.utils import iface

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import (ParameterVector,
                                        ParameterRaster,
                                        ParameterBoolean,
                                        ParameterString,
                                        ParameterNumber)
from processing.tools import dataobjects
from writerRegistry import (WRITER_REGISTRY)
from exporter import (EXPORTER_REGISTRY)
from olwriter import (OpenLayersWriter)
from leafletWriter import (LeafletWriter)
from configparams import getDefaultParams

defaultParams = getDefaultParams()


class exportProject(GeoAlgorithm):
    """This is an example algorithm that takes a vector layer and
    creates a new one just with just those features of the input
    layer that are selected.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the GeoAlgorithm class.
    """

    def defineCharacteristics(self):
        """Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # The name that the user will see in the toolbox
        self.name = 'Export project'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to webmap'

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""

        writer = WRITER_REGISTRY.createWriterFromProject()
        (writer.layers, writer.groups, writer.popup,
         writer.visible, writer.json,
         writer.cluster) = self.getLayersAndGroups()
        exporter = EXPORTER_REGISTRY.createFromProject()
        write_folder = exporter.exportDirectory()
        writer.write(iface, write_folder)

    def getLayersAndGroups(self):
        root_node = QgsProject.instance().layerTreeRoot()
        tree_layers = root_node.findLayers()
        layers = []

        for tree_layer in tree_layers:
            layer = tree_layer.layer()
            if (layer.type() != QgsMapLayer.PluginLayer and
                    root_node.findLayer(layer.id()).isVisible()):
                try:
                    if layer.type() == QgsMapLayer.VectorLayer:
                        testDump = layer.rendererV2().dump()
                    layers.append(layer)
                except:
                    QgsMessageLog.logMessage(traceback.format_exc(),
                                             "qgis2web",
                                             level=QgsMessageLog.CRITICAL)

        popup = []
        visible = []
        json = []
        cluster = []
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                layerPopups = getPopup(layer)
            else:
                layerPopups = []
            popup.append(OrderedDict(layerPopups))
            visible.append(layer.customProperty("qgis2web/Visible", True))
            json.append(layer.customProperty("qgis2web/Encode to JSON", True))
            cluster.append(layer.customProperty("qgis2web/Cluster", 0) == 2)

        return (layers[::-1],
                {},
                popup[::-1],
                visible[::-1],
                json[::-1],
                cluster[::-1])


class exportVector(GeoAlgorithm):
    """This is an example algorithm that takes a vector layer and
    creates a new one just with just those features of the input
    layer that are selected.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the GeoAlgorithm class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT_LAYER = 'OUTPUT_LAYER'
    INPUT_LAYER = 'INPUT_LAYER'

    def defineCharacteristics(self):
        """Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # The name that the user will see in the toolbox
        self.name = 'Export vector layer'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to webmap'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterString("MAP_FORMAT", "Map format",
                                          "OpenLayers"))

        self.addParameter(ParameterVector(self.INPUT_LAYER,
                                          self.tr('Input vector layer'),
                                          ParameterVector.VECTOR_TYPE_ANY,
                                          False))

        self.addParameter(ParameterBoolean("VISIBLE", "Visible", True))
        self.addParameter(ParameterBoolean("CLUSTER", "Cluster", False))

        for group, settings in defaultParams.iteritems():
            for param, value in settings.iteritems():
                if isinstance(value, bool):
                    self.addParameter(ParameterBoolean(param, param, value))
                elif isinstance(value, Number):
                    self.addParameter(ParameterNumber(param, param, value))
                elif isinstance(value, basestring):
                    self.addParameter(ParameterString(param, param, value))

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""

        # The first thing to do is retrieve the values of the parameters
        # entered by the user
        inputMapFormat = self.getParameterValue("MAP_FORMAT")
        inputFilename = self.getParameterValue(self.INPUT_LAYER)
        inputVisible = self.getParameterValue("VISIBLE")
        inputCluster = self.getParameterValue("CLUSTER")

        inputExporter = self.getParameterValue("Exporter")
        inputLib = self.getParameterValue("Mapping library location")
        inputJSON = self.getParameterValue("Minify GeoJSON files")
        inputPrecision = self.getParameterValue("Precision")
        inputExtent = self.getParameterValue("Extent")
        inputMaxZoom = self.getParameterValue("Max zoom level")
        inputMinZoom = self.getParameterValue("Min zoom level")
        inputRestrict = self.getParameterValue("Restrict to extent")
        inputAddress = self.getParameterValue("Add address search")
        inputLayersList = self.getParameterValue("Add layers list")
        inputGeolocate = self.getParameterValue("Geolocate user")
        inputHighlight = self.getParameterValue("Highlight on hover")
        inputLayerSearch = self.getParameterValue("Layer search")
        inputCRS = self.getParameterValue("Match project CRS")
        inputMeasure = self.getParameterValue("Measure tool")
        inputHover = self.getParameterValue("Show popups on hover")
        inputTemplate = self.getParameterValue("Template")

        # Input layers vales are always a string with its location.
        # That string can be converted into a QGIS object (a
        # QgsVectorLayer in this case) using the
        # processing.getObjectFromUri() method.
        vectorLayer = dataobjects.getObjectFromUri(inputFilename)

        if inputMapFormat.lower() == "leaflet":
            writer = LeafletWriter()
        else:
            writer = OpenLayersWriter()

        writer.params = defaultParams
        writer.params["Data export"]["Exporter"] = inputExporter
        writer.params["Data export"]["Mapping library location"] = inputLib
        writer.params["Data export"]["Minify GeoJSON files"] = inputJSON
        writer.params["Data export"]["Precision"] = inputPrecision
        writer.params["Scale/Zoom"]["Extent"] = inputExtent
        writer.params["Scale/Zoom"]["Max zoom level"] = inputMaxZoom
        writer.params["Scale/Zoom"]["Min zoom level"] = inputMinZoom
        writer.params["Scale/Zoom"]["Restrict to extent"] = inputRestrict
        writer.params["Appearance"]["Add address search"] = inputAddress
        writer.params["Appearance"]["Add layers list"] = inputLayersList
        writer.params["Appearance"]["Geolocate user"] = inputGeolocate
        writer.params["Appearance"]["Highlight on hover"] = inputHighlight
        writer.params["Appearance"]["Layer search"] = inputLayerSearch
        writer.params["Appearance"]["Match project CRS"] = inputCRS
        writer.params["Appearance"]["Measure tool"] = inputMeasure
        writer.params["Appearance"]["Show popups on hover"] = inputHover
        writer.params["Appearance"]["Template"] = inputTemplate
        writer.params["Appearance"][
            "Base layer"] = WRITER_REGISTRY.getBasemapsFromProject()
        writer.layers = [vectorLayer]
        writer.groups = {}
        writer.popup = [OrderedDict(getPopup(vectorLayer))]
        writer.visible = [inputVisible]
        writer.json = [True]
        writer.cluster = [inputCluster]
        exporter = EXPORTER_REGISTRY.createFromProject()
        write_folder = exporter.exportDirectory()
        writer.write(iface, write_folder)


class exportRaster(GeoAlgorithm):
    """This is an example algorithm that takes a vector layer and
    creates a new one just with just those features of the input
    layer that are selected.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the GeoAlgorithm class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT_LAYER = 'OUTPUT_LAYER'
    INPUT_LAYER = 'INPUT_LAYER'

    def defineCharacteristics(self):
        """Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # The name that the user will see in the toolbox
        self.name = 'Export raster layer'

        # The branch of the toolbox under which the algorithm will appear
        self.group = 'Export to webmap'

        # We add the input vector layer. It can have any kind of geometry
        # It is a mandatory (not optional) one, hence the False argument
        self.addParameter(ParameterString("MAP_FORMAT", "Map format",
                                          "OpenLayers"))

        self.addParameter(ParameterRaster(self.INPUT_LAYER,
                                          self.tr('Input raster layer'),
                                          False))

        self.addParameter(ParameterBoolean("VISIBLE", "Visible", True))

        for group, settings in defaultParams.iteritems():
            for param, value in settings.iteritems():
                if isinstance(value, bool):
                    self.addParameter(ParameterBoolean(param, param, value))
                elif isinstance(value, Number):
                    self.addParameter(ParameterNumber(param, param, value))
                elif isinstance(value, basestring):
                    self.addParameter(ParameterString(param, param, value))

    def processAlgorithm(self, progress):
        """Here is where the processing itself takes place."""

        # The first thing to do is retrieve the values of the parameters
        # entered by the user
        inputMapFormat = self.getParameterValue("MAP_FORMAT")
        inputFilename = self.getParameterValue(self.INPUT_LAYER)
        inputVisible = self.getParameterValue("VISIBLE")

        inputExporter = self.getParameterValue("Exporter")
        inputLib = self.getParameterValue("Mapping library location")
        inputJSON = self.getParameterValue("Minify GeoJSON files")
        inputPrecision = self.getParameterValue("Precision")
        inputExtent = self.getParameterValue("Extent")
        inputMaxZoom = self.getParameterValue("Max zoom level")
        inputMinZoom = self.getParameterValue("Min zoom level")
        inputRestrict = self.getParameterValue("Restrict to extent")
        inputAddress = self.getParameterValue("Add address search")
        inputLayersList = self.getParameterValue("Add layers list")
        inputGeolocate = self.getParameterValue("Geolocate user")
        inputHighlight = self.getParameterValue("Highlight on hover")
        inputLayerSearch = self.getParameterValue("Layer search")
        inputCRS = self.getParameterValue("Match project CRS")
        inputMeasure = self.getParameterValue("Measure tool")
        inputHover = self.getParameterValue("Show popups on hover")
        inputTemplate = self.getParameterValue("Template")

        # Input layers vales are always a string with its location.
        # That string can be converted into a QGIS object (a
        # QgsVectorLayer in this case) using the
        # processing.getObjectFromUri() method.
        rasterLayer = dataobjects.getObjectFromUri(inputFilename)

        if inputMapFormat.lower() == "leaflet":
            writer = LeafletWriter()
        else:
            writer = OpenLayersWriter()

        writer.params = defaultParams
        writer.params["Data export"]["Exporter"] = inputExporter
        writer.params["Data export"]["Mapping library location"] = inputLib
        writer.params["Data export"]["Minify GeoJSON files"] = inputJSON
        writer.params["Data export"]["Precision"] = inputPrecision
        writer.params["Scale/Zoom"]["Extent"] = inputExtent
        writer.params["Scale/Zoom"]["Max zoom level"] = inputMaxZoom
        writer.params["Scale/Zoom"]["Min zoom level"] = inputMinZoom
        writer.params["Scale/Zoom"]["Restrict to extent"] = inputRestrict
        writer.params["Appearance"]["Add address search"] = inputAddress
        writer.params["Appearance"]["Add layers list"] = inputLayersList
        writer.params["Appearance"]["Geolocate user"] = inputGeolocate
        writer.params["Appearance"]["Highlight on hover"] = inputHighlight
        writer.params["Appearance"]["Layer search"] = inputLayerSearch
        writer.params["Appearance"]["Match project CRS"] = inputCRS
        writer.params["Appearance"]["Measure tool"] = inputMeasure
        writer.params["Appearance"]["Show popups on hover"] = inputHover
        writer.params["Appearance"]["Template"] = inputTemplate
        writer.params["Appearance"][
            "Base layer"] = WRITER_REGISTRY.getBasemapsFromProject()
        writer.layers = [rasterLayer]
        writer.groups = {}
        writer.popup = [False]
        writer.visible = [inputVisible]
        writer.json = [False]
        writer.cluster = [False]
        exporter = EXPORTER_REGISTRY.createFromProject()
        write_folder = exporter.exportDirectory()
        writer.write(iface, write_folder)


def getPopup(layer):
    options = []
    layerPopups = []
    fields = layer.pendingFields()
    for f in fields:
        fieldIndex = fields.indexFromName(unicode(f.name()))
        formCnf = layer.editFormConfig()
        editorWidget = formCnf.widgetType(fieldIndex)
        if editorWidget == QgsVectorLayer.Hidden or \
           editorWidget == 'Hidden':
            continue
        options.append(f.name())
    for option in options:
        custProp = layer.customProperty("qgis2web/popup/" + option)
        pair = (option, custProp)
        layerPopups.append(pair)
    return layerPopups