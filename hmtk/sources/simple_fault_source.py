#!/usr/bin/env/python
# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# LICENSE
#
# Copyright (c) 2010-2013, GEM Foundation, G. Weatherill, M. Pagani,
# D. Monelli.
#
# The Hazard Modeller's Toolkit is free software: you can redistribute
# it and/or modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either version
# 3 of the License, or (at your option) any later version.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake. If not, see <http://www.gnu.org/licenses/>
#
# DISCLAIMER
# 
# The software Hazard Modeller's Toolkit (hmtk) provided herein
# is released as a prototype implementation on behalf of
# scientists and engineers working within the GEM Foundation (Global
# Earthquake Model).
#
# It is distributed for the purpose of open collaboration and in the
# hope that it will be useful to the scientific, engineering, disaster
# risk and software design communities.
#
# The software is NOT distributed as part of GEM's OpenQuake suite
# (http://www.globalquakemodel.org/openquake) and must be considered as a
# separate entity. The software provided herein is designed and implemented
# by scientific staff. It is not developed to the design standards, nor
# subject to same level of critical review by professional software
# developers, as GEM's OpenQuake software suite.
#
# Feedback and contribution to the software is welcome, and can be
# directed to the hazard scientific staff of the GEM Model Facility
# (hazard@globalquakemodel.org).
#
# The Hazard Modeller's Toolkit (hmtk) is therefore distributed WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.
#
# The GEM Foundation, and the authors of the software, assume no
# liability for use of the software.

# -*- coding: utf-8 -*-

'''
Defines the :class hmtk.sources.simple_fault_source.mtkSimpleFaultSource, which 
represents the hmtk defition of a simple fault source. This extends the :class:
nrml.models.SimpleFaultSource
'''
import warnings
import numpy as np
from math import fabs
from openquake.nrmllib import models
from openquake.hazardlib.geo.point import Point
from openquake.hazardlib.geo.line import Line
from openquake.hazardlib.geo.surface.simple_fault import SimpleFaultSurface
import hmtk.sources.source_conversion_utils as conv


class mtkSimpleFaultSource(object):
    '''
    New class to describe the mtk Simple fault source object
    
    :param str identifier: 
        ID code for the source
    :param str name:
        Source name
    :param str trt:
        Tectonic region type
    :param geometry:
        Instance of :class: nhlib.geo.surface.simple_fault.SimpleFaultSource
    :param float dip:
        Dip of the fault surface
    :param float upper_depth:
        Upper seismogenic depth (km)
    :param float lower_depth: 
        Lower seismogenic depth (km)
    :param str mag_scale_rel:
        Magnitude scaling relationsip
    :param float rupt_aspect_ratio:
        Rupture aspect ratio
    :param mfd:
        Magnitude frequency distribution as instance of 
        :class: nrml.models.IncrementalMFD or 
        :class: nrml.models.TGRMFD
    :param  float rake:
        Rake of fault
    :param catalogue: 
        Earthquake catalogue associated to source as instance of 
        hmtk.seismicity.catalogue.Catalogue object
    '''
    
    
    def __init__(self, identifier, name, trt=None, geometry=None, dip=None,
                 upper_depth=None, lower_depth = None, mag_scale_rel=None, 
                 rupt_aspect_ratio=None, mfd=None, rake=None):
        '''
        Instantiate class with just the basic attributes identifier and name
        '''
        self.typology = 'SimpleFault'
        self.id = identifier
        self.name = name 
        self.trt = trt
        self.geometry = geometry
        self.fault_trace = None
        self.upper_depth = upper_depth
        self.lower_depth = lower_depth
        self.mag_scale_rel = mag_scale_rel
        self.rupt_aspect_ratio = rupt_aspect_ratio
        self.mfd = mfd
        self.rake = rake
        # Check that input dip is between 0 and 90 degrees
        if dip:
            assert((dip > 0.) and (dip <= 90.))
        self.dip = dip
        self.catalogue = None
        
    def _check_seismogenic_depths(self, upper_depth, lower_depth):
        
        '''
        Checks the seismic depths for physical consistency
        :param float upper_depth:
            Upper seismogenic depth (km)
            
        :param float lower_depth:
            Lower seismogenic depth (km)
        '''
        # Simple check on depths
        if upper_depth:
            if upper_depth < 0.:
                raise ValueError('Upper seismogenic depth must be greater than'
                                 ' or equal to 0.0!')
            else:
                self.upper_depth = upper_depth
        else:
            self.upper_depth = 0.0
        
        if not lower_depth:
            raise ValueError('Lower seismogenic depth must be defined for '
                             'simple fault source!')
        if lower_depth < self.upper_depth:
                raise ValueError('Lower seismogenic depth must take a greater' 
                                 ' value than upper seismogenic depth')

        self.lower_depth = lower_depth
    
    
    def create_geometry(self, input_geometry, dip, upper_depth, lower_depth, 
                        mesh_spacing=1.0):
        '''
        If geometry is defined as a numpy array then create instance of 
        nhlib.geo.line.Line class, otherwise if already instance of class
        accept class
        
        :param input_geometry:
            Trace (line) of the fault source as either
            i) instance of nhlib.geo.line.Line class
            ii) numpy.ndarray [Longitude, Latitude]
        
        :param float dip:
            Dip of fault surface (in degrees)
            
        :param float upper_depth:
            Upper seismogenic depth (km)
        
        :param float lower_depth:
            Lower seismogenic depth (km)
            
        :param float mesh_spacing:
            Spacing of the fault mesh (km) {default = 1.0}
        '''
        assert((dip > 0.) and (dip <= 90.))
        self.dip = dip
        self._check_seismogenic_depths(upper_depth, lower_depth)
        
        if not isinstance(input_geometry, Line):
            if not isinstance(input_geometry, np.ndarray):
                raise ValueError('Unrecognised or unsupported geometry '
                                 'definition')
            else:
                self.fault_trace = Line([Point(row[0], row[1]) for row in 
                                      input_geometry])
        else:
            self.fault_trace = input_geometry
        # Build fault surface
        self.geometry = SimpleFaultSurface.from_fault_data(self.fault_trace, 
                                                           self.upper_depth, 
                                                           self.lower_depth, 
                                                           self.dip, 
                                                           mesh_spacing)


    def select_catalogue(self, selector, distance, 
                         distance_metric='joyner-boore', upper_eq_depth=None, 
                         lower_eq_depth=None):
        '''
        Selects earthquakes within a distance of the fault
        :param selector:
            Populated instance of hmtk.seismicity.selector.CatalogueSelector
        
        :param distance:
            Distance from point (km) for selection
        
        :param str distance_metric
            Choice of fault source distance metric 'joyner-boore' or 'rupture'
        
        :param float upper_eq_depth:
            Upper hypocentral depth of hypocentres to be selected
        
        :param float lower_eq_depth:
            Lower hypocentral depth of hypocentres to be selected
        
        '''
        if selector.catalogue.get_number_events() < 1:
            raise ValueError('No events found in catalogue!') 

        # rupture metric is selected and dip != 90 or 'rupture'
        if ('rupture' in distance_metric) and (fabs(self.dip - 90) > 1E-5):
            # Use rupture distance
            self.catalogue = selector.within_rupture_distance(
                self.geometry,
                distance,
                upper_depth=upper_eq_depth,
                lower_depth=lower_eq_depth)
        else:
            # Use Joyner-Boore distance
            self.catalogue = selector.within_joyner_boore_distance(
                self.geometry,
                distance,
                upper_depth=upper_eq_depth,
                lower_depth=lower_eq_depth)
        
        if self.catalogue.get_number_events() < 5:
            # Throw a warning regarding the small number of earthquakes in
            # the source!
            warnings.warn('Source %s (%s) has fewer than 5 events' 
                %(self.id, self.name))


    def create_oqnrml_source(self, use_defaults=False):
        '''
        Turns source into instance of the :class: 
        openquake.nrmllib.model.SimpleFaultSource
        :param bool use_defaults:
            If set to True, will use default values for rupture aspect ratio
            and magnitude scaling relation. If False, will raise value error
            if this information is missing
        '''
        if not isinstance(self.rake, float):
            raise ValueError('Cannot render fault source - rake is missing!')
        simple_geometry = models.SimpleFaultGeometry(
            wkt=conv.simple_trace_to_wkt_linestring(self.fault_trace),
            dip=self.dip,
            upper_seismo_depth=self.upper_depth,
            lower_seismo_depth=self.lower_depth)

        return models.SimpleFaultSource(
            self.id,
            self.name,
            self.trt,
            simple_geometry, 
            conv.render_mag_scale_rel(self.mag_scale_rel, use_defaults), 
            conv.render_aspect_ratio(self.rupt_aspect_ratio, use_defaults),
            conv.render_mfd(self.mfd),
            self.rake)
