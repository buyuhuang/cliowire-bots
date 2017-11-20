from clioServer import credentials, getPulses, postPulses
from mastodon import Mastodon
import sys
import os
import json
import copy
import io

APP_NAME = 'MapBot'
BOT_LOGIN = 'viaccoz'
BOT_PSWD = 'reallygoodpassword'
HASH_MARKER = '#geoCoords'
FINAL_PULSE = 'Today, {} pulses were geoparsed and then added to the map of GeoPulses !'

GEOJSON_FILEPATH = 'data/geopulses.json'

GEOJSON_PRE = "{\"type\": \"FeatureCollection\",\"generator\": \"overpass-turbo\",\"copyright\": \"2017, EPFL \",\"timestamp\": \"2017-11-20T13:03:02Z\",\"features\": ["

GEOJSON_POST = "]}"

def main(args):

    credentials.checkIfCredentials(APP_NAME)

    cliowireConn = credentials.log_in(APP_NAME, BOT_LOGIN, BOT_PSWD)

    #geopulses = []
    #eopulses.append({"id": 1, "content":"#geoCoords(12.3404, 45.4337) DHstudents went to #GeoEntity (Venice https://en.wikipedia.org/wiki/Venice)"})
    #geopulses.append({"id": 2, "content":"#geoCoords(2.3522, 48.8566) #GeoEntity (Paris https://en.wikipedia.org/wiki/Paris) is a nice city"})
    geopulses = getPulses.retrieve(hashtag=HASH_MARKER)

    toWrite = ''


    for p in geopulses:
        toWrite += jsonParse(p)
        toWrite += ','

    #remove trailing comma
    toWrite = toWrite[:-1]
    f = writeGeoPulses(GEOJSON_FILEPATH, toWrite)
    f.close()

    postPulses.post_content(cliowireConn, FINAL_PULSE.format(nmbOfPulses))


def writeGeoPulses(filepath, pulsesToWrite):
    if os.path.isfile(filepath):
        #TODO write
        pass
    else:
        f = open(filepath, 'w+')
        f.write(GEOJSON_PRE+pulsesToWrite+GEOJSON_POST)
        return f


def contentBreakDown(content):
    '''
        Convention of the geoPulse : format (in regex like descritpion)
        "#geoCoords(<coord1>, <coord2>) <content>? [#GeoEntity <nameOfGeoEntity> | (<nameOfGeoEntity> <uriOfGeoEntity>)]+? <content>?"
        Example :
        "#geoCoords(12.3404, 45.4337) DHstudents went to #GeoEntity (Venice https://en.wikipedia.org/wiki/Venice)"
    '''
    tokens = content.split( )
    #will stoke processed version of the tokens, to reconstruct the original text
    purifiedContent = []
    #we take as principle that every content given in this function, is a content of a geoPulse, with all its convention respected. So the first two tokens should be the coordinates. If this is not the case, an exception is raised.
    if not tokens[0].startswith(HASH_MARKER):
        raise Exception("MapBot received a pulse that was not geoparsed ! The operation was aborted.")
    lng = tokens[0][len(HASH_MARKER)+1:-1]
    lat = tokens[1][:-1]
    coordinates = [float(lng), float(lat)]
    tokens = tokens[2:]
    entities = []
    i = 1
    nmbToks = len(tokens)
    while i < nmbToks:
        currTok = copy.deepcopy(tokens[i])
        precedingTok = tokens[i-1]
        if precedingTok == '#GeoEntity':
            i += 1
            #if the geoEntity is also a named entities, need to remove the first open parenthesis.
            if currTok[0] == '(':
                currTok = currTok[1:]
                #We need to skip the uri as well.
                i += 1
            entities.append(currTok)
            purifiedContent.append(currTok)
        elif(precedingTok[0] == '(' and currTok.startswith('http')):
            #we encountered a named entities which did not trigger the geoparsing, need to add to entities list.
            purifiedContent.append(precedingTok[1:])
            entities.append(precedingTok[1:])
            i += 1
        else:
            #otherwise we just let the content as it is.
            purifiedContent.append(precedingTok)
            #with the weird way to scan all the tokey, those lines needed to be to avoid edge cases.
            if i == nmbToks - 1 and currTok != '#GeoEntity':
                purifiedContent.append(currTok)
        i += 1

    return ' '.join(purifiedContent), entities, coordinates

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
