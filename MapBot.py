from clioServer import credentials, getPulses, postPulses
from mastodon import Mastodon
import sys
import os

APP_NAME = 'MapBot'
BOT_LOGIN = 'viaccoz'
BOT_PSWD = 'reallygoodpassword'
HASH_MARKER = '#geoCoords'
FINAL_PULSE = 'Today, {0} pulses were geoparsed and then added to the map of GeoPulses !'

def main(args):

    credentials.checkIfCredentials(APP_NAME)

    cliowireConn = credentials.log_in(APP_NAME, BOT_LOGIN, BOT_PSWD)

    geopulses = getPulses.retrieve(hashtag=HASH_MARKER)

    geoJsonFile = getGeoPulsesFile()

    toWrite = ''

    for p in geopulses:
        pJson = jsonParse(p)
        toWrite.append(pJson)

    geoJsonFile.write(toWrite)

    postPulses.post_content(cliowireConn, FINAL_PULSE.format(len(geopulses)))




def getGeoPulsesFile():
    #TODO open the file of geoJson entities in append mode, if it does no exist,


"""
Format of the geopulse (in JSON):
{
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [12.3404, 45.4337]
    },
    "properties": {
        "pulseid": "99018727713161107",
        "content": "DHstudents went to Venice",
        "entities": ["Venice", "DHstudents"]
    }
}
"""
def jsonParse(pulse):
    #TODO fetch the coordinate from the pulse, detect named entities, and write it in the geoJsonPulse format.

main(sys.argv)
