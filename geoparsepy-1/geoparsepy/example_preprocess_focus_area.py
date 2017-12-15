# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
..
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
	//    Created Date :    2016/03/16
	//    Created for Project:    REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependencies: None
	//
	/////////////////////////////////////////////////////////////////////////
	'''

Example preprocessing a focus area and writing the preprocessed locations to a SQL table ready for geoparsing

"""

import os, sys, logging, traceback, codecs, datetime, copy, time, ast, math, re, random, shutil, json
import config_helper, common_parse_lib, PostgresqlHandler, geo_preprocess_lib, geo_parse_lib
import pkg_resources

def demo( config_file = None ) :

	# make logger (global to STDOUT)
	LOG_FORMAT = ('%(message)s')
	logger = logging.getLogger( __name__ )
	logging.basicConfig( level=logging.INFO, format=LOG_FORMAT )
	logger.info('logging started')

	try :
		if config_file == None :
			if pkg_resources.resource_exists( __name__, 'example_preprocess_focus_area.py' ) :
				# if run as an installed python lib
				strConfigFile = os.path.dirname( pkg_resources.resource_filename( __name__, 'example_preprocess_focus_area.py' ) ) + os.sep + 'example_preprocess_focus_area.ini'
			else :
				# if run as a standalone file in a dir
				strConfigFile = os.path.dirname( __file__ ) + os.sep + 'example_preprocess_focus_area.ini'
		else :
			strConfigFile = config_file

		# load config
		dictConfig = config_helper.read_config( strConfigFile )

		strCorpusDir = dictConfig['corpus_dir']
		listLangs = dictConfig['language_codes']

		# initialize SQL and create table if it does not already exist
		strUser = dictConfig['db_user']
		strPass = dictConfig['db_pass']
		strHost = dictConfig['db_host']
		nPort = int( dictConfig['db_port'] )
		strDatabase = dictConfig['db_name']
		strSchema = dictConfig['db_schema_reveal']

		if len( dictConfig['focus_area_spec'] ) > 0 :
			dictFocusAreaSpec = ast.literal_eval( dictConfig['focus_area_spec'] )
		else :
			dictFocusAreaSpec = None

		if len( dictConfig['global_area_spec'] ) > 0 :
			dictGlobalSpec = ast.literal_eval( dictConfig['global_area_spec'] )
		else :
			dictGlobalSpec = None

		# make a geoparse config object
		# note: lower tokens will be True for geoparsing work and stemmer will use default per language (plural removal usually)
		dictGeospatialConfig = geo_parse_lib.get_geoparse_config( 
			lang_codes = listLangs,
			logger = logger,
			corpus_dir = strCorpusDir,
			whitespace = u'"\u201a\u201b\u201c\u201d()',
			sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
			punctuation = """,;\/:+-#~&*=!?""",
			)

		# create database pool
		dbHandlerPool = {}
		dbHandlerPool['admin'] = PostgresqlHandler.PostgresqlHandler( strUser, strPass, strHost, nPort, strDatabase )
		dbHandlerPool['point'] = PostgresqlHandler.PostgresqlHandler( strUser, strPass, strHost, nPort, strDatabase )
		dbHandlerPool['poly'] = PostgresqlHandler.PostgresqlHandler( strUser, strPass, strHost, nPort, strDatabase )
		dbHandlerPool['line'] = PostgresqlHandler.PostgresqlHandler( strUser, strPass, strHost, nPort, strDatabase )

		# calc global area - a pre-computed table is available also for global admin which takes 11 days to compute
		if dictGlobalSpec != None :

			logger.info( 'starting global area ' + repr(dictGlobalSpec) )

			# make table
			geo_preprocess_lib.create_preprocessing_tables( dictGlobalSpec, dbHandlerPool['admin'], strSchema, delete_contents = False, logger = logger )

			# preprocess global locations and populate the target SQL table
			dictNewLocations = geo_preprocess_lib.execute_preprocessing_global( dictGlobalSpec, dbHandlerPool, strSchema, logger = logger )

			logger.info( 'finished global area : ' + repr(dictGlobalSpec) )
			logger.info( 'location id range : ' + repr(dictNewLocations) )

		# calc each focus area - a pre-computed table is available also for global_places which takes 8 days to compute
		if dictFocusAreaSpec != None :
			for strFocusArea in dictFocusAreaSpec.keys() :

				logger.info( 'starting focus area ' + strFocusArea )

				# get JSON spec
				jsonFocusArea = dictFocusAreaSpec[strFocusArea]

				# make tables if they dont already exist for this focus area
				geo_preprocess_lib.create_preprocessing_tables( jsonFocusArea, dbHandlerPool['admin'], strSchema, delete_contents = False, logger = logger )

				# preprocess focus area locations and populate the target SQL table
				dictNewLocations = geo_preprocess_lib.execute_preprocessing_focus_area( jsonFocusArea, dbHandlerPool, strSchema, logger = logger )

				logger.info( 'finished focus area ' + strFocusArea )
				logger.info( 'location id range : ' + repr(dictNewLocations) )

		# close database handles
		dbHandlerPool['admin'].close()
		dbHandlerPool['point'].close()
		dbHandlerPool['poly'].close()
		dbHandlerPool['line'].close()

	except :
		logger.exception( 'example_preprocess_focus_area main() exception' )
		sys.stderr.flush()
		sys.stdout.flush()
		sys.exit(1)

	# all done
	logger.info('finished')
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
		print 'Usage: example_preprocess_focus_area.py <config file>\n'
		sys.stdout.flush()
		sys.exit(1)
	if not os.path.isfile(sys.argv[1]) :
		print '<config file> ' + sys.argv[1] + ' does not exist\n'
		sys.stdout.flush()
		sys.exit(1)

	demo( config_file = sys.argv[1] )
