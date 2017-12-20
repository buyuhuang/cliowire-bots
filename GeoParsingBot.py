import os, sys
import overpy
import json
from clioServer import credentials, postPulses, cliowireUtils as cU
import subprocess
from math import modf

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

    #returns a new
    def toJson(self):
        return {
            'id':self.pulse.id,
            'content': cU.cleanHTTP(self.pulse.content),
            'entities': self.geoEntities,
            'osmids': self.osmids
        }


news_source = AccountGeoInfos(12,'le_temps_scrapbot',[6.143158, 46.204391], 'fr')
sec_sources = AccountGeoInfos(13,'secondary_sources_bot', [12.4923,41.8903], 'en')
albane_source = AccountGeoInfos(8, 'albane', [6.143158, 46.204391], 'en')

sources = [news_source, sec_sources, albane_source]

INTER_JSON_FILE_IN = "pulsesReadIn.json"
INTER_JSON_FILE_OUT = "pulsesReadOut.json"


def getCoords( api, osmid):
    osmtype = 'Node'
    if osmid < 0:
        omstype = 'Rel'
        osmid = -osmid

    opQuery = "{}({});(._;>;);out{};"
    if osmtype=='Rel':
        opQuery = opQuery.format('relation', osmid, ' center')
    else:
        opQuery = opQuery.format('node', osmid, '')

    res = api.query(opQuery)
    if osmtype == 'Rel':
        rel = res.relations[0]
        return [rel.center_lon, rel.center_lat]
    else:
        node = res.nodes[0]
        return [node.lon, node.lat]


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
    CWIter = cU.PulseIterator(cliowireConn, oldest_id=last_id, user=correct_account.id)
    data = {}
    data['pulses'] = []
    for batch in CWIter:
        for pulse in batch:
            if not 'geocoding' in pulse.hashtags:
                data['pulses'].append(GeoPulse(pulse).toJson())

    with open(INTER_JSON_FILE_IN, 'w') as outfile:
        json.dump(data, outfile)
    subprocess.call(["./geoparsepy-1/geoparsing.py", INTER_JSON_FILE_IN, INTER_JSON_FILE_OUT, s.lang, str(s.focus_point[0]), str(s.focus_point[1])])
    fnotPosted = open('IdPulsesNotPostedSince'+last_id+'.log','w')
    overApi = overpy.Overpass()
    with open(INTER_JSON_FILE_OUT, 'r') as json_file:

        data = json.load(json_file)
        nmbPulse = 0
        for p in data['pulses']:
            for index in range(len(p['entities'])):
                hasIndexerror = False
                try :
                    coords = getCoords(overApi, p['osmids'][index])
                    geoEntity = p['entities'][index]
                    if not geoEntity.startswith('#'):
                        geoEntity = '#'+geoEntity
                    newContent = p['content'] + ' #geocoding ' + geoEntity + ' ' +coordsToHashtag(coords)
                except IndexError:
                    hasIndexerror = True
                if hasIndexerror or  len(newContent) > 499:
                    if hasIndexerror:
                        fnotPosted.write('NotFound:')
                    fnotPosted.write(str(p['id'])+'\n')
                else:
                    nmbPulse += 1
                    cliowireConn.status_post(newContent, in_reply_to_id=p['id'])
        print('Total number of pulses posted on the platform : '+ repr(nmbPulse))

    fnotPosted.close()
    #need to update the id of the most recent pulse to allow statefull future computations
    last_id = CWIter.latest_id
    #we need to save the last id that we have
    cU.updateBotsMetadata(file_name, last_id)

main(sys.argv)
