#!/usr/bin/python2.7
# -*-coding:UTF-8 -*
import os, sys, logging, traceback, codecs, datetime, copy, time, ast, math, re, random, shutil, json
import geoparsepy.config_helper, geoparsepy.common_parse_lib, geoparsepy.PostgresqlHandler, geoparsepy.geo_parse_lib, geoparsepy.geo_preprocess_lib


#def geoparse(listOfPulse):
LOG_FORMAT = ('%(message)s')
logger = logging.getLogger( __name__ )
logging.basicConfig(filename='example4.log', level=logging.INFO, format=LOG_FORMAT )
logger.info('logging started')

dictGeospatialConfig = geoparsepy.geo_parse_lib.get_geoparse_config(
	#lang_codes = ['en','fr','it'],
	lang_codes = ['en'],
	logger = logger,
	corpus_dir = None,
	whitespace = u'"\u201a\u201b\u201c\u201d()',
	sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
	punctuation = """,;\/:+-#~&*=!?""",
	)


listText = [
	u'hello New York, USA its Bill from Bassett calling',
	u'live on the BBC Victoria Derbyshire is visiting Derbyshire for an exclusive UK interview',
	u'Hello, this is bill, your friendly neighbor',
	u'Paris is a nice city',
	u'Hello I am a pulse, it is friday morning',
	u'DHstudents went to Venice.',
	u'DHstudents went to Yorkshire.',
	u'DHstudents went to Johannesburg.',
	u'Ernst JUnger était écrivain allemand en 1998 #ErnstJUnger #écrivainallemand #JDG1998-02-21',
	u'Jean Rouaud était écrivain en 1998 #JeanRouaud #écrivain #JDG1998-02-21',
	u'Madeleine Santschi était écrivain suisse en 1998 #MadeleineSantschi #écrivainsuisse #JDG1998-02-26',
	u'La Suisse est un pays formidable',
	u'La suisse est un pays formidable',
	u'Rapsi was mentionned living in Roma',
	u'At Geneva lives great People',
	u'Sofia is the capital of Bulgary',
	u'Athena is close to the Adriatic sea',
	u'Ancona is close to the Adriatic sea',
	u'Sion is a city in Valais',
	u'I would like to recolt some signature for apocalypse',
	u'13 ways of going to Bern',
	u'London is the capital citiy for britannic people',
	u'Paris, France, is a nice city',
	u'Nice is a boarding city of meditteranean sea',
	u'Rome has many colliseum',
	u'Extreme perturbation are at Padua',
	u'Reykjavik holds the summer festival',
	u'Some people lives in Amsterdam',
	u'I would like to go to Bremes',
	u'Dresden is located north of Germany',
	u'Pesaro (http://it.wikipedia.org/wiki/Pesaro) is present in book \'Piety and patronage in Renaissance Venice : Bellini, Titian and the Franciscans\' by Goffen, Rona at page 3.'
	]

databaseHandle = geoparsepy.PostgresqlHandler.PostgresqlHandler( 'postgres', 'postgres', 'localhost', 5432, 'openstreetmap', 600 )

dictLocationIDs = {}
#listFocusArea=[ 'global_cities10', 'europe_places', 'north_america_places', 'au_nz_places' ]
listFocusArea=['global_cities10', 'europe_places']
for strFocusArea in listFocusArea :
	dictLocationIDs[strFocusArea + '_admin'] = [-1,-1]
	dictLocationIDs[strFocusArea + '_poly'] = [-1,-1]
	dictLocationIDs[strFocusArea + '_line'] = [-1,-1]
	dictLocationIDs[strFocusArea + '_point'] = [-1,-1]

cached_locations = geoparsepy.geo_preprocess_lib.cache_preprocessed_locations( databaseHandle, dictLocationIDs, 'reveal', dictGeospatialConfig )
logger.info( 'number of cached locations = ' + str(len(cached_locations)) )

databaseHandle.close()

indexed_locations = geoparsepy.geo_parse_lib.calc_inverted_index( cached_locations, dictGeospatialConfig )
logger.info( 'number of indexed phrases = ' + str(len(indexed_locations.keys())) )

indexed_geoms = geoparsepy.geo_parse_lib.calc_geom_index( cached_locations )
logger.info( 'number of indexed geoms = ' + str(len(indexed_geoms.keys())) )

osmid_lookup = geoparsepy.geo_parse_lib.calc_osmid_lookup( cached_locations )

dictGeomResultsCache = {}

listTokenSets = []
listGeotags = []
for nIndex in range(len(listText)) :
	strUTF8Text = listText[ nIndex ]
	listToken = geoparsepy.common_parse_lib.unigram_tokenize_microblog_text( strUTF8Text, dictGeospatialConfig )
	listTokenSets.append( listToken )
	listGeotags.append( None )

listMatchSet = geoparsepy.geo_parse_lib.geoparse_token_set( listTokenSets, indexed_locations, dictGeospatialConfig )

#strGeom = 'POINT(-1.4052268 50.9369033)' #Southampton
strGeom = 'POINT(6.143158 46.204391)' #Geneva
listGeotags[0] = strGeom

listMatchGeotag = geoparsepy.geo_parse_lib.reverse_geocode_geom( [strGeom], indexed_geoms, dictGeospatialConfig )
if len( listMatchGeotag[0] ) > 0  :
	for tupleOSMIDs in listMatchGeotag[0] :
		setIndexLoc = osmid_lookup[ tupleOSMIDs ]
		for nIndexLoc in setIndexLoc :
			strName = cached_locations[nIndexLoc][1]
			logger.info( 'Reverse geocoded geotag location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + '] = ' + strName )

for nIndex in range(len(listMatchSet)) :
	logger.info( 'Text = ' + listText[nIndex] )
	listMatch = listMatchSet[ nIndex ]
	strGeom = listGeotags[ nIndex ]
	setOSMID = set([])
	for tupleMatch in listMatch :
		nTokenStart = tupleMatch[0]
		nTokenEnd = tupleMatch[1]
		tuplePhrase = tupleMatch[3]
		for tupleOSMIDs in tupleMatch[2] :
			setIndexLoc = osmid_lookup[ tupleOSMIDs ]
			for nIndexLoc in setIndexLoc :
				logger.info( 'Location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + ' '.join(tuplePhrase) )
				break
	listLocMatches = geoparsepy.geo_parse_lib.create_matched_location_list( listMatch, cached_locations, osmid_lookup )
	geoparsepy.geo_parse_lib.filter_matches_by_confidence( listLocMatches, dictGeospatialConfig, geom_context = strGeom, geom_cache = dictGeomResultsCache )
	geoparsepy.geo_parse_lib.filter_matches_by_geom_area( listLocMatches, dictGeospatialConfig )
	geoparsepy.geo_parse_lib.filter_matches_by_region_of_interest( listLocMatches, [-148838, -62149], dictGeospatialConfig )
	setOSMID = set([])
	for nMatchIndex in range(len(listLocMatches)) :
		nTokenStart = listLocMatches[nMatchIndex][1]
		nTokenEnd = listLocMatches[nMatchIndex][2]
		tuplePhrase = listLocMatches[nMatchIndex][3]
		strGeom = listLocMatches[nMatchIndex][4]
		tupleOSMID = listLocMatches[nMatchIndex][5]
		dictOSMTags = listLocMatches[nMatchIndex][6]
		if not tupleOSMID in setOSMID :
			setOSMID.add( tupleOSMID )
			listNameMultilingual = geoparsepy.geo_parse_lib.calc_multilingual_osm_name_set( dictOSMTags, dictGeospatialConfig )
			strNameList = ';'.join( listNameMultilingual )
			strOSMURI = geoparsepy.geo_parse_lib.calc_OSM_uri( tupleOSMID, strGeom )
			logger.info( 'Disambiguated Location [index ' + str(nMatchIndex) + ' osmid ' + repr(tupleOSMID) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + strNameList + ' : ' + strOSMURI )
#geoparse(None)
