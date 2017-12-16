#!/usr/bin/python2.7
# -*-coding:UTF-8 -*
import os, sys, logging, traceback, codecs, datetime, copy, time, ast, math, re, random, shutil, json
import geoparsepy.config_helper, geoparsepy.common_parse_lib, geoparsepy.PostgresqlHandler, geoparsepy.geo_parse_lib, geoparsepy.geo_preprocess_lib
import sys
import json


args = sys.argv
JsonPulsesIn = args[1]
JsonPulsesOut = args[2]
lang = args[3]
focus_point_lon = args[4]
focus_point_lat = args[5]

LOG_FORMAT = ('%(message)s')
logger = logging.getLogger( __name__ )
logging.basicConfig(filename='geoparsing_output.log', level=logging.INFO, format=LOG_FORMAT )
logger.info('logging started')

dictGeospatialConfig = geoparsepy.geo_parse_lib.get_geoparse_config(
	lang_codes = [lang],
	logger = logger,
	corpus_dir = None,
	whitespace = u'"\u201a\u201b\u201c\u201d()',
	sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
	punctuation = """,;\/:+-#~&*=!?""",
	)

fin = open(JsonPulsesIn, 'r')
data = json.load(fin)

listPulse = data['pulses']

databaseHandle = geoparsepy.PostgresqlHandler.PostgresqlHandler( 'postgres', 'postgres', 'localhost', 5432, 'openstreetmap', 600 )

dictLocationIDs = {}
listFocusArea=['europe_places']
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
for nIndex in range(len(listPulse)) :
	strUTF8Text = listPulse[ nIndex ]['content']
	listToken = geoparsepy.common_parse_lib.unigram_tokenize_microblog_text( strUTF8Text, dictGeospatialConfig )
	listTokenSets.append( listToken )
	listGeotags.append( None )

listMatchSet = geoparsepy.geo_parse_lib.geoparse_token_set( listTokenSets, indexed_locations, dictGeospatialConfig )

strGeom = 'POINT({} {})'.format(focus_point_lon, focus_point_lat)
listGeotags[0] = strGeom

listMatchGeotag = geoparsepy.geo_parse_lib.reverse_geocode_geom( [strGeom], indexed_geoms, dictGeospatialConfig )
if len( listMatchGeotag[0] ) > 0  :
	for tupleOSMIDs in listMatchGeotag[0] :
		setIndexLoc = osmid_lookup[ tupleOSMIDs ]
		for nIndexLoc in setIndexLoc :
			strName = cached_locations[nIndexLoc][1]
			logger.info( 'Reverse geocoded geotag location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + '] = ' + strName )

dataOut = {}
dataOut['pulses'] = []



for nIndex in range(len(listMatchSet)) :
	currPulse = listPulse[nIndex]
	logger.info( 'Text = ' + unicode(currPulse['content'].replace('#', '').replace('_', '')))
	listMatch = listMatchSet[ nIndex ]
	strGeom = listGeotags[ nIndex ]
	setOSMID = set([])
	#holds latest resultst from GeoParsings
	dictLocID = {}
	for tupleMatch in listMatch :
		nTokenStart = tupleMatch[0]
		nTokenEnd = tupleMatch[1]
		tuplePhrase = tupleMatch[3]
		for tupleOSMIDs in tupleMatch[2] :
			setIndexLoc = osmid_lookup[ tupleOSMIDs ]
			for nIndexLoc in setIndexLoc :
				phrase = ' '.join(tuplePhrase)
				logger.info( 'Location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + phrase )
				dictLocID[phrase] = tupleOSMIDs[0]
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
			phrase = strNameList.lower()
			dictLocID[phrase] = tupleOSMID[0]
	if len(dictLocID) > 0:
		for k,v in dictLocID.iteritems():
			currPulse['entities'].append(k)
			currPulse['osmids'].append(v)
		dataOut['pulses'].append(currPulse)

fin.close()
fout = open(JsonPulsesOut, 'w')
json.dump(dataOut, fout)
fout.close()
