# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
..
	/////////////////////////////////////////////////////////////////////////
	//
	// (c) Copyright University of Southampton IT Innovation, 2013
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
	//	Created By :	Stuart E. Middleton
	//	Created Date :	2013/12/20
	//	Created for Project:	REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependancies: None
	//
	/////////////////////////////////////////////////////////////////////////
	'''

Config file helper functions to parse python INI files from disk and SQL database
"""

import logging, json, io, ConfigParser, ast
from SqlHandler import SqlHandler

def read_config( filename, logger = None ) :
	"""
	read config file using ConfigParser.ConfigParser(). this helper function processes lists, tuples and dictionary serializations using ast.literal_eval() to return python objects not str

	:param str filename: config ini filename
	:param logging.Logger logger: logger object
	:return: parsed config file in a dict structure e.g. { 'database_name' : 'mydatabase', 'list_names' : ['name1','name2'] }
	:rtype: dict
	"""

	if not isinstance( filename, (str,unicode) ) :
		raise Exception( 'filename invalid' )

	if logger == None :
		logger = logging.getLogger()

	logger.info( 'reading config file : ' + str(filename) )
	dictConfig = {}
	configObj = ConfigParser.ConfigParser()

	# old code does not with fir .ini files with BOM header (i.e. windows style UTF8 files)
	#configObj.read( filename )

	with io.open( filename, 'r', encoding='utf_8_sig' ) as fp :
		configObj.readfp(fp)

	listSections = configObj.sections()
	for section in listSections :
		logger.info( '[' + str(section) + ']' )
		listOptions = configObj.options(section)
		for option in listOptions :
			dictConfig[option] = configObj.get(section, option)

			# use python to decode lists and dict entries
			if len(dictConfig[option]) > 1 :
				if (dictConfig[option][0] == '[') or (dictConfig[option][0] == '{') or (dictConfig[option][0] == '(') :
					dictConfig[option] = ast.literal_eval( dictConfig[option] )
				if dictConfig[option] == 'None' :
					dictConfig[option] = ast.literal_eval( dictConfig[option] )

			logger.info( '  ' +str(option) + '= ' + str(dictConfig[option]) )

	return dictConfig

def read_config_from_SQL( database_handler, query, timeout_statement = 60, timeout_overall = 180, logger = None ) :
	"""
	read config from a SQL query (SQL query should return a JSON config string for subsequent parsing)

	:param SqlHandler.SqlHandler database_handler: database handler object for SQL query
	:param tuple query: SQL query tuple to execute to get config JSON object e.g. ( "SELECT json_config FROM ... WHERE assessment_id = %s", ('ny_floods',) )
	:param int timeout_statement: number of seconds to allow each SQL statement
	:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
	:param logging.Logger logger: logger object
	:return: parsed config file in a dict structure e.g. { 'database_name' : 'mydatabase', 'list_names' : ['name1','name2'] }
	:rtype: dict
	"""

	if not isinstance( database_handler, SqlHandler ) :
		raise Exception( 'database_handler invalid' )
	if not isinstance( query, tuple ) :
		raise Exception( 'query invalid' )

	if logger == None :
		logger = logging.getLogger()

	# get JSON config string from database
	logger.info( 'querying SQL to get config : ' + repr(query) )
	listResult = database_handler.execute_sql_query( query, timeout_statement, timeout_overall )
	if len(listResult) != 1 :
		raise Exception( 'SQL query did not return a single (row) JSON encoded config string' )
	if len(listResult[0]) != 1 :
		raise Exception( 'SQL query did not return a single (column) JSON encoded config string' )
	strResult = listResult[0][0]

	# parse JSON config string
	dictConfig = json.loads( strResult )

	# pretty print config to log
	for strKey in dictConfig.keys() :
		logger.info( str(strKey) + '= ' + repr(dictConfig[strKey]) )

	# return dict of config data
	return dictConfig


