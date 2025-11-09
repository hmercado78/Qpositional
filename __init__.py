# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qpositional
                                 A QGIS plugin
 assessment the positional quality of geographic data
                              -------------------
        begin                : 2023-05-21
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
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Qpositional class from file Qpositional.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .Qpositional import Qpositional
    return Qpositional(iface)
