from __future__ import (absolute_import, division, print_function)

from branca.element import CssLink, Figure, JavascriptLink, MacroElement

from jinja2 import Template

import folium

import os

import json

from math import modf


CW_URL = "<a href=\"https://cliowire.dhlab.epfl.ch/web/statuses/{}\">{}</a>\n"


def coordToFloat(decim, unit):
    res = 1
    if decim[0] == 'm' or decim[0] == 'M':
        res *= -1
        decim = decim[1:]
    return res * float(str(decim + '.' + unit))

def sizeToHexaColor(max, size):
    maxHexaVal = int(0xFFFFFF)
    actualHexVal = int((size/max) * maxHexaVal)
    return '#'+repr(hex(actualHexVal))


def coordsToHashtag(coords):
    prelude = "#p"
    for index in range(len(coords)):
        minus = ''
        c = coords[index]
        if c < 0:
            c = -c
            minus = 'M'
        sep = modf(c)
        first = int(sep[1])
        sec = str(10000 + (10000 * round(sep[0], 4)))[1:-2]
        toAdd = minus+str(first)+'_'+sec
        prelude += toAdd
        if index == 0:
            prelude += '_'
    return prelude

class Search(MacroElement):
    """
    Adds a search tool to your map.

    Parameters
    ----------
    data: str/JSON
        GeoJSON strings
    search_zoom: int
        zoom level when searching features, default 12
    search_label: str
        label to index the search, default 'name'
    geom_type: str
        geometry type, default 'Point'
    position: str
        Change the position of the search bar, can be:
        'topleft', 'topright', 'bottomright' or 'bottomleft',
        default 'topleft'

    See https://github.com/stefanocudini/leaflet-search for more information.

    """
    def __init__(self, data, search_zoom=12, search_label='name', geom_type='Point', position='topleft'):
        super(Search, self).__init__()
        self.position = position
        self.data = data
        self.search_label = search_label
        self.search_zoom = search_zoom
        self.geom_type = geom_type

        self._template = Template("""
        {% macro script(this, kwargs) %}

            var {{this.get_name()}} = new L.GeoJSON({{this.data}});

            {{this._parent.get_name()}}.addLayer({{this.get_name()}});

            var searchControl = new L.Control.Search({
                layer: {{this.get_name()}},
                propertyName: '{{this.search_label}}',
            {% if this.geom_type == 'Point' %}
                initial: false,
                zoom: {{this.search_zoom}},
                position:'{{this.position}}',
                hideMarkerOnCollapse: true
            {% endif %}
            {% if this.geom_type == 'Polygon' %}
                marker: false,
                moveToLocation: function(latlng, title, map) {
                var zoom = {{this._parent.get_name()}}.getBoundsZoom(latlng.layer.getBounds());
                    {{this._parent.get_name()}}.setView(latlng, zoom); // access the zoom
                }
            {% endif %}
                });
                searchControl.on('search:locationfound', function(e) {

                    e.layer.setStyle({fillColor: '#3f0', color: '#0f0'});
                    if(e.layer._popup)
                        e.layer.openPopup();

                }).on('search:collapsed', function(e) {

                    {{this.get_name()}}.eachLayer(function(layer) {   //restore feature color
                        {{this.get_name()}}.resetStyle(layer);
                    });
                });
            {{this._parent.get_name()}}.addControl( searchControl );

        {% endmacro %}
        """)  # noqa

    def render(self, **kwargs):
        super(Search, self).render()

        figure = self.get_root()
        assert isinstance(figure, Figure), ('You cannot render this Element '
                                            'if it is not in a Figure.')

        figure.header.add_child(
            JavascriptLink('https://cdn.jsdelivr.net/npm/leaflet-search@2.3.6/dist/leaflet-search.min.js'),  # noqa
            name='Leaflet.Search.js'
        )

        figure.header.add_child(
            CssLink('https://cdn.jsdelivr.net/npm/leaflet-search@2.3.6/dist/leaflet-search.min.css'),  # noqa
            name='Leaflet.Search.css'
        )

with open(os.path.join('data', 'geopulses.json')) as f:
    pulses = json.loads(f.read())
#generating map on which to add infos
m = folium.Map()

lat_max = -91
lat_min = 91
long_max = -181
long_min = 181

#adding a search bar, and indexing the pulses according to their name entities.
Search(pulses, search_label='entities', search_zoom=12).add_to(m)


#adding a marker with popup to the place of the pulses.
mightyDict = {}
for pulse in pulses['features']:
    p = pulse['properties']
    coord = pulse['geometry']['coordinates']
    invCoord = coordsToHashtag([coord[1], coord[0]])
    md_value = [p['pulseid'],p['content']]

    lat = coord[1]
    long = coord[0]
    if lat>lat_max:
        lat_max = lat
    if lat<lat_min:
        lat_min = lat
    if long>long_max:
        long_max = long
    if long<long_min:
        long_min = long

    if not invCoord in mightyDict:
        mightyDict[invCoord] = []

    mightyDict[invCoord].append(md_value)


maxNmb = 0
for k,v in mightyDict.items():
    valLen = len(v)
    if valLen > maxNmb:
        maxNmb = valLen

for k, v in mightyDict.items():
    nmbItem = 0
    content = ''
    for p in v:
        nmbItem += 1
        content += '\n' + repr(nmbItem) + ' : ' + CW_URL.format(repr(p[0]), p[1])

    removeP = k[2:]
    undSS = removeP.split('_')
    lng = coordToFloat(undSS[0], undSS[1])
    lat = coordToFloat(undSS[2], undSS[3])
    content = repr(nmbItem)+ ' elements under this coordinate.\n'+content
    folium.Marker([lng, lat], popup=content).add_to(m)

m.fit_bounds([[lat_min, long_min],[lat_max, long_max]])

m.save('MapAppTest.html')
