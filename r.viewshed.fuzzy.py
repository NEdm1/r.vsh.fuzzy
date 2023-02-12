#!/usr/bin/env python

############################################################################
#
# MODULE:    r.viewshed.fuzzy
# AUTHOR(S): Nagy Edmond
# PURPOSE:	 Script for generating fuzzy viewshed raster maps from
#                points and DEM input.
# COPYRIGHT: (C) 2019 by Nagy Edmond, and the GRASS Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
############################################################################

#%module
#% description: Creates fuzzy viewshed raster maps from a DEM and input points using r.viewshed and r.grow.distance.
#% keyword: raster
#% keyword: r.viewshed
#% keyword: r.grow.distance
#%end

#%option G_OPT_V_INPUT
#% key: vect
#% description: Input observer vector points
#% required: yes
#%end

#%option G_OPT_R_INPUT
#% key: rast
#% description: Input DEM raster
#% required: yes
#%end

#%option G_OPT_R_OUTPUT
#% key: output
#% description: Output raster pattern name (eg. "example_cat2", example = user name)
#% required: yes
#%end

#%option
#% key: twidth
#% type: double
#% description: Target width (in m)
#%answer: 1.0
#% required : yes
#%end

#%option
#% key: varc
#% type: double
#% description: The visual arc (in minutes)
#%answer: 1.0
#% required : yes
#%end

#%option
#% key: dist_b1
#% type: integer
#% description: Distance between observer and b1 (in m)
#%answer: 1000
#% required : yes
#%end

#%flag
#% key: c
#% description: Consider the curvature of the earth (current ellipsoid)
#%end

#%flag
#% key: r
#% description: Consider the effect of atmospheric refraction
#%end

#%option
#% key: observer_elevation
#% type: double
#% description: Height of observer
#%answer: 1.75
#% required : no
#%end

#%option
#% key: target_elevation
#% type: double
#% description: Height of targets
#%answer: 1.75
#% required : no
#%end

#%option
#% key: max_distance
#% type: double
#% description: Maximum visibility radius. By default infinity (-1)
#%answer: -1
#% required : no
#%end

#%option
#% key: memory
#% type: integer
#% description: Amount of memory to use (in MB)
#%answer: 500
#% required : no
#%end

#%option
#% key: refraction_coeff
#% type: double
#% description: Refraction coefficient (with flag -r)
#%answer: 0.14286
#% options: 0.0-1.0
#% required : no
#%end

#%option
#% key: decay_form_denom
#% type: double
#% description: The denominator of the decay formula
#%answer: 2.0
#% required : no
#%end

import sys
import math
import grass.script as grass
from grass.pygrass.modules.shortcuts import raster as r


def main():
    options, flags = grass.parser()
    
    # setup input variables
    rast = options["rast"]
    vect = options["vect"]
    tWidth = options["twidth"]
    vArc = options["varc"]
    dtoB1 = options["dist_b1"]
	
    viewshed_options = {}
    for option in ('observer_elevation', 'target_elevation', 'max_distance', 'memory', 'refraction_coeff'):
        viewshed_options[option] = options[option]

    dnm = options["decay_form_denom"]
    out = options["output"]

    # setup flagstring
    flagstring = ''
    if flags['r']:
        flagstring += 'r'
    if flags['c']:
        flagstring += 'c'

    # see if the input is valid
    if (int(grass.vector_info_topo(map=vect)['points']) < 1):
        grass.error(_("There are no point features in the input."))

    else:
        # get the input vector points
        points = grass.read_command("v.out.ascii", flags='r', input=vect, type="point", format="point", separator=",").strip()

        # read the input points and parse them
        pointList = []
        for line in points.splitlines():
            if line:
                pointList.append(line.strip().split(','))

        # get the distance between observer and crossover point (sum of b1 and b2), and between b1 and b2
        dtoB2 = float(tWidth)*round(1/(2*math.tan((math.radians(float(vArc)/60))/2)))
        dB1toB2 = dtoB2-float(dtoB1)

        # create fuzzy viewsheds for each point
        for point in pointList:
            # create distance raster around the point
            grass.run_command("v.to.rast", overwrite=True, input=vect, output="tempPtRast", use="cat", cats=point[-1])
            grass.run_command("r.grow.distance", overwrite=True, input="tempPtRast", distance="tempPtDist", flags="m")

            # reclassify the distance raster
            r.mapcalc("%s = 1 / (1 + %f * pow(((if(%s <= %i, null(), %s)) - %i) / %f, 2))" % ("tempPtReclsDist", float(dnm), "tempPtDist", int(dtoB1), "tempPtDist", int(dtoB1), dB1toB2), overwrite=True)
            grass.run_command("r.null", map="tempPtReclsDist", null="1.0")
            
            # run viewshed
            grass.run_command("r.viewshed", overwrite=True, input=rast, flags=flagstring+'b', output="tempViewshPoint"+point[-1], coordinates=point[0]+","+point[1], **viewshed_options)

            # obtain fuzzy viewshed map
            r.mapcalc("%s = %s * %s" % (out+"_cat"+point[-1], "tempPtReclsDist", "tempViewshPoint"+point[-1]), overwrite=True)

        # remove leftovers
        grass.run_command("g.remove", quiet=True, flags='f', type='raster', pattern="temp*")

    return

if __name__ == "__main__":
    options, flags = grass.parser()
    sys.exit(main())
