import os, sys
from clioServer import credentials, postPulses, cliowireUtils as cU

#This class is meant to hold information that relate to the account that will get his pulses geoparsed
class AccountGeoInfos:
    def __init__(self, id, account_name, focus_point, lang):
        self.id = id
        self.account_name = account_name
        self.focus_point = focus_point
        self.lang = lang

#misleading class name, it's a class that bridge the pulse read, and the pulse that will be geocoded.
class GeoPulse:
    def __init__(self, pulse):
        self.pulse = pulse
        self.geoEntities = None
        self.coords = []

    def setEntity(self, ent):
        self.geoEntities = ent

    def setCoords(lat, lng):
        #the coords need to be reversed, because Leaflet.js.
        self.coords.append(lng)
        self.coords.append(lat)

    #returns a new
    def duplicate:
        return GeoPulse(self.pulse)


news_source = AccountGeoInfos(12,'Le_temps_scrapbot',[0.0000,0.0000], 'fr')
sec_sources = AccountGeoInfos(13,'secondary_sources_bot', [0.0000,0.0000], 'en')

sources = [news_source, sec_sources]


def main(args):
    #think to not parse geocoords
    bot_login, bot_pswd, last_id, file_name = None, None, None, None #BATMAAAAAAAN
    try:
        bot_login, bot_pswd, last_id = cU.retrieveBotsMetadata(args[1:])
    except Exception as exc:
        #print the error message for the user to understand what atrocity he did
        print('\n'+str(exc)+'\n')
        sys.exit(1)

    #this should not produce an index out of bound error, since it is checked in the try catch above.
    file_name = args[1]
    credentials.checkIfCredentials(file_name)

    cliowireConn = credentials.log_in(file_name, bot_login, bot_pswd)

    CWIter = cU.PulseIterator(cliowireConn, oldest_id=last_id)
    toGeoParse = []
    for batch in CWIter:
        for toot in batch:
            if toot
            pulse = cU.Pulse.tootToPulse(toot)
            if not pulse.hashtags.contains('geocoding'):
                toGeoParse.append(pulse)
