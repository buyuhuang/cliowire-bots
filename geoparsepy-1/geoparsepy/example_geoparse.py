# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
	/////////////////////////////////////////////////////////////////////////
	//
	// (c) Copyright University of Southampton IT Innovation, 2016
	//
	// Copyright in this software belongs to IT Innovation Centre of
	// Gamma House, Enterprise Road, Southampton SO16 7NS, UK.
	//
	// This software may not be used, sold, licensed, transferred, copied
	// or reproduced in whole or in part in any manner or form or in or
	// on any media by any person other than in accordance with the terms
	// of the Licence Agreement supplied with the software, or otherwise
	// without the prior written consent of the copyright owners.
	//
	// This software is distributed WITHOUT ANY WARRANTY, without even the
	// implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
	// PURPOSE, except where stated in the Licence Agreement supplied with
	// the software.
	//
	//    Created By :    Stuart E. Middleton
	//    Created Date :    2016/03/22
	//    Created for Project:    REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependencies: None
	//
	/////////////////////////////////////////////////////////////////////////

Example geoparsing a set of text statements using the global focus area

"""

import os, sys, logging, traceback, codecs, datetime, copy, time, ast, math, re, random, shutil, json
import config_helper, common_parse_lib, PostgresqlHandler, geo_parse_lib, geo_preprocess_lib
import pkg_resources

def demo( config_file = None ) :

	# make logger (global to STDOUT)
	LOG_FORMAT = ('%(message)s')
	logger = logging.getLogger( __name__ )
	logging.basicConfig( level=logging.INFO, format=LOG_FORMAT )
	logger.info('logging started')

	try :
		if config_file == None :
			if pkg_resources.resource_exists( __name__, 'example_geoparse.py' ) :
				# if run as an installed python lib
				strConfigFile = os.path.dirname( pkg_resources.resource_filename( __name__, 'example_geoparse.py' ) ) + os.sep + 'example_geoparse.ini'
			else :
				# if run as a standalone file in a dir
				strConfigFile = os.path.dirname( __file__ ) + os.sep + 'example_geoparse.ini'
		else :
			strConfigFile = config_file

		# load config
		dictConfig = config_helper.read_config( strConfigFile )

		# init nlp
		strCorpusDir = dictConfig['corpus_dir']
		listLangs = dictConfig['language_codes']
		nLocParentSemanticDistance = int( dictConfig[ 'semantic_distance_loc_parent' ] )
		nLocGeomDistance = float( dictConfig[ 'geom_distance_loc' ] )
		tupleAllowedConfidenceTests = tuple( dictConfig[ 'allowed_conf_tests' ] )
		strSpatialFilter = dictConfig['spatial_filter_gazetteer']
		listOSMLocationsOfInterest = dictConfig['osm_locations_of_interest']

		# init database
		nTimeoutStatement = int( dictConfig['timeout_statement'] )
		nTimeoutOverall = int( dictConfig['timeout_overall'] )
		strUser = dictConfig['db_user']
		strPass = dictConfig['db_pass']
		strHost = dictConfig['db_host']
		nPort = int( dictConfig['db_port'] )
		strDatabase = dictConfig['db_name']
		strSchema = dictConfig['db_schema_reveal']
		listFocusArea = dictConfig['focus_area_list']

		# get a geospatial config object
		dictGeospatialConfig = geo_parse_lib.get_geoparse_config(
			lang_codes = listLangs,
			logger = logger,
			corpus_dir = strCorpusDir,
			whitespace = u'"\u201a\u201b\u201c\u201d()',
			sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
			punctuation = """,;\/:+-#~&*=!?""",
			)

		# create database handle
		databaseHandle = PostgresqlHandler.PostgresqlHandler( strUser, strPass, strHost, nPort, strDatabase, nTimeoutStatement )
		print "postdb handle.\n"

		# load all pre-processed focus area locations into memory ready for geoparsing
		dictLocationIDs = {}
		for strFocusArea in listFocusArea :
			dictLocationIDs[strFocusArea + '_admin'] = [-1,-1]
			dictLocationIDs[strFocusArea + '_poly'] = [-1,-1]
			dictLocationIDs[strFocusArea + '_line'] = [-1,-1]
			dictLocationIDs[strFocusArea + '_point'] = [-1,-1]

		#cached_locations = geo_preprocess_lib.cache_preprocessed_locations( databaseHandle, dictLocationIDs, strSchema, dictGeospatialConfig, nTimeoutStatement, nTimeoutOverall, strSpatialFilter )
		#logger.info( 'number of cached locations = ' + str(len(cached_locations)) )

		# close database handles
		databaseHandle.close()

		# create an inverted index
		indexed_locations = geo_parse_lib.calc_inverted_index( '''cached_locations,''' dictGeospatialConfig )
		logger.info( 'number of indexed phrases = ' + str(len(indexed_locations.keys())) )

		# create a geom index
		indexed_geoms = geo_parse_lib.calc_geom_index( cached_locations )
		logger.info( 'number of indexed geoms = ' + str(len(indexed_geoms.keys())) )

		# create an OSM ID lookup table
		osmid_lookup = geo_parse_lib.calc_osmid_lookup( cached_locations )

		# make an empty geom cache to store geometry distance and intersection results to avoid repeating work
		dictGeomResultsCache = {}

		# define some text to geoparse
		listText = [
			u'hello New York, USA its Bill from Bassett calling',
			u'live on the BBC Victoria Derbyshire is visiting Derbyshire for an exclusive UK interview',
			]

		# tokenize sentences into token sets ready for geoparsing
		listTokenSets = []
		listGeotags = []
		for nIndex in range(len(listText)) :
			strUTF8Text = listText[ nIndex ]
			listToken = common_parse_lib.unigram_tokenize_microblog_text( strUTF8Text, dictGeospatialConfig )
			listTokenSets.append( listToken )
			listGeotags.append( None )

		# geoparse each token set to get all possible location matches (not yet disambiguated)
		listMatchSet = geo_parse_lib.geoparse_token_set( listTokenSets, indexed_locations, dictGeospatialConfig )

		# add a geotag within Southampton to help disambiguate Bassett to be the one in Southampton and not any other location with the same name around the world (e.g. Bassett, Rock County, Nebraska, United States of America)
		strGeom = 'POINT(-1.4052268 50.9369033)'
		listGeotags[0] = strGeom

		# reverse geocode this geom
		listMatchGeotag = geo_parse_lib.reverse_geocode_geom( [strGeom], indexed_geoms, dictGeospatialConfig )
		if len( listMatchGeotag[0] ) > 0  :
			for tupleOSMIDs in listMatchGeotag[0] :
				setIndexLoc = osmid_lookup[ tupleOSMIDs ]
				for nIndexLoc in setIndexLoc :
					strName = cached_locations[nIndexLoc][1]
					logger.info( 'Reverse geocoded geotag location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + '] = ' + strName )

		# disambiguate location matches in each token set
		for nIndex in range(len(listMatchSet)) :

			logger.info( 'Text = ' + listText[nIndex] )

			# get raw matches
			listMatch = listMatchSet[ nIndex ]

			# get geotag (can be None)
			strGeom = listGeotags[ nIndex ]

			# print out location matches before disambiguaton
			setOSMID = set([])
			for tupleMatch in listMatch :
				nTokenStart = tupleMatch[0]
				nTokenEnd = tupleMatch[1]
				tuplePhrase = tupleMatch[3]
				for tupleOSMIDs in tupleMatch[2] :
					setIndexLoc = osmid_lookup[ tupleOSMIDs ]
					# note: each OSMID might have several rows each with a different geom. only print first row for each OSMID as we are not printing geom.
					for nIndexLoc in setIndexLoc :
						logger.info( 'Location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + ' '.join(tuplePhrase) )
						break

			# create a list of annotated location matches with super region information useful for disambiguation
			# note: there can be several entries for a single OSMID if its made up of several geom objects (e.g. several islands)
			listLocMatches = geo_parse_lib.create_matched_location_list( listMatch, cached_locations, osmid_lookup )

			# filter location matches by confidence. pass in geom information (i.e. geotag) if available to help disambiguate locations
			geo_parse_lib.filter_matches_by_confidence( listLocMatches, dictGeospatialConfig, geom_context = strGeom, geom_cache = dictGeomResultsCache )

			# filter location matches by geom area to get best single match per token (i.e. choose a city polygon with a large area before an admin centre point with zero area)
			geo_parse_lib.filter_matches_by_geom_area( listLocMatches, dictGeospatialConfig )

			# filter location matches by a parent region of interest (USA and UK in this case)
			if len(listOSMLocationsOfInterest) > 0 :
				geo_parse_lib.filter_matches_by_region_of_interest( listLocMatches, listOSMLocationsOfInterest, dictGeospatialConfig )

			# for remaiming location matches get the multi-lingual name and OSM URI and display it
			# note: the index order of disambiguated locations will not be the same as the matched locations as both sorting and filtering has been applied during filter_matches_by_confidence()
			# note: only print each OSMID entry once if it has multiple geoms as its a text output
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
					listNameMultilingual = geo_parse_lib.calc_multilingual_osm_name_set( dictOSMTags, dictGeospatialConfig )
					strNameList = ';'.join( listNameMultilingual )
					strOSMURI = geo_parse_lib.calc_OSM_uri( tupleOSMID, strGeom )
					logger.info( 'Disambiguated Location [index ' + str(nMatchIndex) + ' osmid ' + repr(tupleOSMID) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + strNameList + ' : ' + strOSMURI )

	except :
		logger.exception( 'example_geoparse main() exception' )
		sys.stdout.flush()
		sys.exit(1)

	# all done
	logger.info('finished')
	sys.stderr.flush()
	sys.stdout.flush()
	sys.exit(0);


################################
# main
################################

# only execute if this is the main file
if __name__ == '__main__' :

	#
	# check args
	#
	if len(sys.argv) < 2 :
		print 'Usage: example_geoparse.py <config file>\n'
		sys.stdout.flush()
		sys.exit(1)
	if not os.path.isfile(sys.argv[1]) :
		print '<config file> ' + sys.argv[1] + ' does not exist\n'
		sys.stdout.flush()
		sys.exit(1)

	demo( config_file = sys.argv[1] )
