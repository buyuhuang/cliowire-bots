import os, sys
import overpy
import json
from clioServer import credentials, postPulses, cliowireUtils as cU
import subprocess

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
        self.geoEntities = []
        self.coords = []
        self.osmids = []

    def setEntity(self, ent):
        self.geoEntities.append(ent)

    def setEntities(self, entities):
        self.geoEntities = entities

    def setOSMID(self, osmid):
        self.omsid.append(osmid)

    def setOSMIDs(self, osmids):
        self.omsids = osmids

    #returns a new
    def toJson(self):
        return {
            'id':self.id,
            'content': self.pulse.content,
            'entities': self.geoEntities
            'coords': self.coords
            'osmids': self.osmids
        }


news_source = AccountGeoInfos(12,'le_temps_scrapbot',[6.143158, 46.204391], 'fr')
sec_sources = AccountGeoInfos(13,'secondary_sources_bot', [12.4923,41.8903], 'en')

sources = [news_source, sec_sources]

INTER_JSON_FILE = "pulsesRead.json"


def getCoords(osmid, api):
    osmtype = 'Node'
    if osmid < 0:
        omstype = 'Rel'
        osmid = -osmid

    query = "{}({});(._;>;);out{};"
    if osmtype=='Rel':
        query.format('relation', osmid, ' center')
    else:
        query.format('node', osmid)

    res = api.query(query)
    if osmtype == 'Rel':
        rel = res.relations[0]
        return [rel.center_lon, rel.center_lat]
    else:
        node = res.nodes[0]
        return [node.lon, node.lat]

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

    #now need to retrieve the source name from the file of metadata chosen.
    source_name = file_name.replace('_infos', '')
    isSrc = lambda x: x.account_name == source_name
    correct_account = None
    for s in sources:
        if isSrc(s):
            correct_account = s

    if correct_account == None:
        raise Exception('wrong file of metadata chosen, please select or create a metadata file corresponding to the correct source.')
        sys.exit(1)


    credentials.checkIfCredentials(file_name)

    cliowireConn = credentials.log_in(file_name, bot_login, bot_pswd)

    CWIter = cU.PulseIterator(cliowireConn, oldest_id=last_id)
    data = {}
    data['pulses'] = []
    for batch in CWIter:
        for toot in batch:
            pulse = cU.Pulse.tootToPulse(toot)
            if not pulse.hashtags.contains('geocoding'):
                data.append(GeoPulse(pulse).toJson())

    with open(INTER_JSON_FILE, 'w') as outfile:
        json.dump(data, outfile)

    subprocess.call("./geoparsepy-1/geoparsing {} {} {} {}".format(INTER_JSON_FILE, s.lang, s.focus_point[0], s.focus_point[1]))

    with open(INTER_JSON_FILE, 'w') as json_file:
        data = json.load(json_file)
        for p in data['pulses']:
            for index in range(len(p['entities'])):
                coords = getCoords(p['coords'][index])
                newContent = p['content'] + ' #'+p['entities']+ ' '+coordsToHashtag(coords)
                cliowireConn.status_post(newContent, in_reply_to_id=p['id'])



main(sys.argv)
