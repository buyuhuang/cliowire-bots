from clioServer import credentials, getPulses, postPulses
from mastodon import Mastodon
import sys
import os
import json

APP_NAME = 'MapBot'
BOT_LOGIN = 'viaccoz'
BOT_PSWD = 'reallygoodpassword'
HASH_MARKER = '#geoCoords'
FINAL_PULSE = 'Today, {} pulses were geoparsed and then added to the map of GeoPulses !'

GEOJSON_PRE = "{\"type\": \"FeatureCollection\",\"generator\": \"overpass-turbo\",\"copyright\": \"2017, EPFL \",\"timestamp\": \"2017-11-20T13:03:02Z\",\"features\": ["

GEOJSON_POST = "]}"

def main(args):

    credentials.checkIfCredentials(APP_NAME)

    cliowireConn = credentials.log_in(APP_NAME, BOT_LOGIN, BOT_PSWD)

    geopulses = getPulses.retrieve(hashtag=HASH_MARKER)

    geoJsonFile = openGeoPulsesFile()

    toWrite = ''


    for p in geopulses:
        pJson = jsonParse(p)
        toWrite.append(pJson+',')

    nmbOfPulses = len(geopulses)

    if nmbOfPulses >0:
        toWrite = toWrite[:-1]
    geoJsonFile.write(toWrite.append(GEOJSON_POST))

    postPulses.post_content(cliowireConn, FINAL_PULSE.format(nmbOfPulses))




def openGeoPulsesFile():
    #TODO open the file of geoJson entities in append mode (which means it ), if it does no exist, create it.
    pass

def contentBreakDown(content):
    #TODO : parse content to extract the coordinates, the named entities, and a clean version of the pulse's content (without balises, and named entitities URL)
    pass

def jsonParse(pulse):
    content, entities, coordinates = contentBreakDown(pulse["content"])
    pulseId = str(pulse["id"])
    #this below is the jsonGeoPulse format we're using. Coordinates must be a list/array of 2 floats, entities a list/array of string, everything else Strings.
    return json.dumps({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates
        },
        "properties": {
            "pulseid": pulseId,
            "content": content,
            "entities": entities
        }
    })

main(sys.argv)
