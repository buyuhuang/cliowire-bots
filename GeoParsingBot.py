import os, sys
from clioServer import credentials
from cliowireUtils import Pulse, PulseIterator


APP_NAME = 'GeoParsingBot'
DATA_FOLDER = 'data/'
METADATA_FILE=APP_NAME + '_metadata.info'
BOT_LOGIN = 'albanemimosa@gmail.com'
BOT_PSWD = 'fdh654321'

class GeoPulse():
    def __init__(self, pulse, WGIS, coords):
        self.pulse = pulse
        self.WGIS = WGIS
        self.coords = coords

def main(args):
    #think to not parse geocoords
    last_id = 0
    if os.path.isfile(METADATA_FILE):
       f = open(METADATA_FILE, 'r')
       last_id = int(f.readline())
       f.close()

    credentials.checkIfCredentials(APP_NAME)

    cliowireConn = credentials.log_in(APP_NAME, BOT_LOGIN, BOT_PSWD)

    CWIter = PulseIterator(cliowireConn, oldest_id=last_id)

    for batch in CWIter:
        for toot in batch:
            pulse = tootToPulse
            coords = geoParse(pulse)




def geoParse(pulse):
    #TODO
    pass
