from clioServer import credentials, postPulses
from mastodon import Mastodon
import sys
import os
import json
import copy
import io
import re

APP_NAME = 'MapBot'
BOT_LOGIN = 'cedric.viaccoz@gmail.com'
BOT_PSWD = 'fdh123456'
HASH_MARKER = 'geocoding'
FINAL_PULSE = 'Today, {0} pulses were geoparsed and then added to the map of GeoPulses !'

GEOJSON_FILEPATH = 'data/geopulses.json'

GEOJSON_PRE = "{\"type\": \"FeatureCollection\",\"generator\": \"overpass-turbo\",\"copyright\": \"2017, EPFL \",\"timestamp\": \"2017-11-20T13:03:02Z\",\"features\": ["

GEOJSON_POST = "]}"

def main(args):

    credentials.checkIfCredentials(APP_NAME)

    cliowireConn = credentials.log_in(APP_NAME, BOT_LOGIN, BOT_PSWD)

    geopulses = cliowireConn.timeline_hashtag(HASH_MARKER, local=True)

    toWrite = ''

    nmbOfPulses = len(geopulses)

    if nmbOfPulses > 0:
        for p in geopulses:
            cleanContent = cleanHTTP(p['content'])
            toWrite += jsonParse(cleanContent, p['id'])
            toWrite += ','

        #remove trailing comma
        toWrite = toWrite[:-1]
        f = writeGeoPulses(GEOJSON_FILEPATH, toWrite)
        f.close()

        postPulses.post_content(cliowireConn, [FINAL_PULSE.format(nmbOfPulses)])
    else:
        print("No new geopulses were detected on the platform.\nNo actions were performed on the map.")


def cleanHTTP(content):
    #Remove href balises, but keep the url
    cleanHref = re.compile('<a[^>]+href=\"(.*?)\"[^>]*>')
    #Remove every other http balises
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanHref, '', content)
    cleantext = re.sub(cleanr, '', cleantext)
    return cleantext

def writeGeoPulses(filepath, pulsesToWrite):
    if os.path.isfile(filepath):
        #this way of doing might not be feasible once the file gets too big.
        #really need a way to erase two last char of a JSON file.
        f = open(filepath, 'r')
        data = f.readlines()
        data[0] = data[0][:-len(GEOJSON_POST)]
        data[0] += ','
        data[0] += pulsesToWrite
        data[0] += GEOJSON_POST
        f.close()
        f = open(filepath, 'w')
        f.write(data[0])
        return f
    else:
        f = open(filepath, 'w+')
        f.write(GEOJSON_PRE+pulsesToWrite+GEOJSON_POST)
        return f


def contentBreakDown(content):
    '''
    takes the content of the pulse (cleaned from all the HTTP useless scraps), and produces
    the content without the hashtags refering to the geocoding part, then the list of entities
    and finally the tuples of geocoordinate (latitude and longitude)
    '''
    tokens = content.split(' ')
    filteredContent = []
    entities = []
    coordinates = []
    for t in tokens:
        if t.startswith('#p'):
            removeP = t[2:]
            undSS = removeP.split('_')
            if len(undSS) != 4:
                raise Exception('The coordinate in this geocoded pulse : \"{}\" were malformed'.format(content))
            lng = float(str(undSS[0] + '.' + undSS[1]))
            lat = float(str(undSS[2] + '.' + undSS[3]))
            coordinates.append(lng)
            coordinates.append(lat)
        elif t.startswith('#') and not t == '#geocoding':
            entities.append(t[1:])
            filteredContent.append(t)
        elif t != '#geocoding':
            filteredContent.append(t)

    purifiedContent = ' '.join(filteredContent)
    return purifiedContent, entities, coordinates

def jsonParse(pulse, pulseId):
    content, entities, coordinates = contentBreakDown(pulse)
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

#main(sys.argv)
