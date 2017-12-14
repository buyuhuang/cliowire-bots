# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
..
	/////////////////////////////////////////////////////////////////////////
	//
	// (c) Copyright University of Southampton IT Innovation, 2012
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
	//	Created Date :	2014/05/13
	//	Created for Project:	REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependancies: None
	//
	/////////////////////////////////////////////////////////////////////////
	'''

Pre-processing module to create and populate SQL tables for focus areas from an installed OpenStreetMap database. Pre-processed SQL tables are required for geo_parse_lib. 

global focus area spec (required before focus area is preprocessed as it contains super region information)::

	{
		'focus_area_id' : 'global_cities10',
		'max_admin_level': 10,
	}

focus area spec (OSM ID's)::

	{
		'focus_area_id' : 'gr_paris',
		'osmid': ['relation',71525, 'relation', 87002, 'relation', 86999, 'relation', 86985, 'relation', 85802, 'relation', 91776, 'relation', 72258, 'relation', 72148, 'relation', 31340, 'relation', 72020, 'relation', 85527, 'relation', 59321, 'relation', 37027, 'relation', 37026, 'relation', 104479, 'relation', 105122, 'relation', 105748, 'relation', 104868, 'relation', 108318, 'relation', 129550, 'relation', 130544, 'relation', 67826, 'relation', 67685, 'relation', 87628, 'relation', 87922],
		'admin_lookup_table' : 'global_cities10_admin',
	}

focus area spec (name and super regions)::

	{
		'focus_area_id' : 'southampton',
		'admin': ['southampton','south east england', 'united kingdom'],
		'admin_lookup_table' : 'global_cities10_admin',
	}

focus area spec (radius from point)::

	{
		'focus_area_id' : 'oxford',
		'radius': ['POINT(-1.3176274 51.7503955)', 0.2],
		'admin_lookup_table' : 'global_cities10_admin',
	}

focus area spec (geom)::

	{
		'focus_area_id' : 'solent_shipping_lane',
		'geom': 'POLYGON(( ... ))',
		'admin_lookup_table' : 'global_cities10_admin',
	}

focus area spec (places with only a point within a set of super regions)::

	{
		'focus_area_id' : 'uk_places',
		'place_types': ['suburb','quarter','neighbourhood','town','village','island','islet','archipelago'],
		'parent_osmid': ['relation',62149],
		'admin_lookup_table' : 'global_cities10_admin',
	}
	{
		'focus_area_id' : 'europe_places',
		'place_types': ['suburb','quarter','neighbourhood','town','village','island','islet','archipelago'],
		'parent_osmid': ['relation',62149, 'relation', 1403916, 'relation', 1311341, 'relation', 295480, 'relation', 9407, 'relation', 50046, 'relation', 2323309, 'relation', 51477, 'relation', 365331, 'relation', 51701, 'relation', 2978650, 'relation', 54224, 'relation', 52822, 'relation', 62273, 'relation', 51684, 'relation', 79510, 'relation', 72594, 'relation', 72596, 'relation', 49715, 'relation', 59065, 'relation', 60189, 'relation', 16239, 'relation', 218657, 'relation', 21335, 'relation', 14296, 'relation', 214885, 'relation', 1741311, 'relation', 2528142, 'relation', 90689, 'relation', 58974, 'relation', 60199, 'relation', 53296, 'relation', 2088990, 'relation', 53292, 'relation', 53293, 'relation', 186382, 'relation', 192307, 'relation', 174737, 'relation', 307787, 'relation', 1124039, 'relation', 365307, 'relation', 1278736],
		'admin_lookup_table' : 'global_cities10_admin',
	}
	note: uk, france, spain, portugal, andorra, denmark, holland, germany, italy, switzerland, norway, finland, sweden, ireland, czech republic, estonia, latvia, lithuania, poland, belarus, russia, austria, slovenia, hungary, slovakia, croatia, serbia, bosnia and herzegovina, romania, moldova, ukraine, montenegro, kosovo, albania, macedonia, bulgaria, greece, turkey, cyprus, monaco, malta, gibralta

focus area spec (global places with only a point)::

	{
		'focus_area_id' : 'global_places',
		'place_types': ['suburb','quarter','neighbourhood','town','village','island','islet','archipelago'],
		'admin_lookup_table' : 'global_cities10_admin',
	}

Performance notes:
	* Preprocesssing time is related to number of points/line/polygons (N) and number of admin regions (M). admin regions are cross-checked for containment so this there are N*M calculations to perform.
	* global_cities10 (300,000 polygons) will take about 12 days to compute on a modest server machine in 2016 (only need do it once of course).
	* uk_places (20,000 points) takes 20 mins.
	* france_places (40,000 points) take 2 hours.
	* europe_places (420,000 points) is made up of each european country. this allows a sequential country-by-country calculation which reduced the size of M and is vastly quicker than global places. it takes 7 hours to compute.
	* north_america_places (usa and canada) (52,000 points) takes 1 hour to compute.
	* au_nz_places (australia and new zealand) (8,000 points) takes 3 mins to compute.
	* global places (about 1,000,000 points) has a maximum size of M and is thus so slow it takes > 12 days to compute. this is disabled and is viable only for future CPU hardware that is quick enough to process it.


Alternative approach is OSM reverse geocoding using Nominatim:
	* Nominatim is a Linux GPL script/lib used by OSM to create an indexed planet OSM dataset that can then be looked up for reverse geocoding (i.e. name -> OSMID)
	* HTTP service available via OSM but this does not scale for large number of locations (as throughput is too slow)
	* local deployment of Nominatim is possible but indexing is built into the planet OSM deployment scripts (i.e. takes 10+ days to run) and is apparently very complex and difficult to get working
	* see http://wiki.openstreetmap.org/wiki/Nominatim

"""

import os, sys, logging, traceback, codecs, datetime, copy, threading, Queue, time
import PostgresqlHandler, geo_parse_lib, common_parse_lib
import psycopg2, shapely, shapely.speedups, shapely.prepared, shapely.wkt, shapely.geometry

def create_preprocessing_tables( focus_area, database_handle, schema, table_point = 'point', table_line = 'line', table_poly = 'poly', table_admin = 'admin', timeout_statement = 60, timeout_overall = 60, delete_contents = False, logger = None ) :
	"""
	create preprocessing tables for a new focus area (if they do not already exist)

	:param dict focus_area: focus area description to create tables for.
	:param PostgresqlHandler.PostgresqlHandler database_handle: handle to database object
	:param str schema: Postgres schema name under which tables will be created
	:param str table_point: Table name suffix to append to focus area ID to make point table
	:param str table_line: Table name suffix to append to focus area ID to make line table
	:param str table_poly: Table name suffix to append to focus area ID to make polygon table
	:param str table_admin: Table name suffix to append to focus area ID to make admin region table
	:param int timeout_statement: number of seconds to allow each SQL statement
	:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
	:param bool delete_contents: if True the contents of any existing tables will be deleted
	:param logging.Logger logger: logger object (optional)
	"""

	# check args without defaults
	if not isinstance( focus_area, dict ) :
		raise Exception( 'invalid focus_area' )
	if not isinstance( database_handle, PostgresqlHandler.PostgresqlHandler ) :
		raise Exception( 'invalid database_handle' )
	if (not isinstance( schema, str )) and (not isinstance( schema, unicode)) :
		raise Exception( 'invalid schema' )
	
	# make database tables for preprocessing work
	# note: psycopg2 inserts '' around all strings regardless of where they appear in SQL statement.
	# schema and table names cannot have quotes in PostgerSQL. thus we add schema and tables manually into teh SQL string not using parameterization
	listStatementsTables = []
	listStatementsDeletes = []

	if 'focus_area_id' in focus_area :
		strFocusAreaID = focus_area['focus_area_id']
	else :
		raise Exception( 'focus_area_id key not found in jsonFocusArea dict' )

	strTableSQL = """
CREATE SCHEMA IF NOT EXISTS {:s};
""".format( schema )

	listStatementsTables.append( (strTableSQL,None) )

	strTableSQL = """
CREATE TABLE IF NOT EXISTS {:s}.{:s} (
  loc_id serial,
  name text,
  osm_id_set bigint[],
  admin_regions bigint[],
  geom geometry(Geometry,4326),
  tags hstore,
  CONSTRAINT {:s}_pkey PRIMARY KEY (loc_id)
)
WITH (
  OIDS=FALSE
);
""".format( schema,strFocusAreaID + '_' + table_point,strFocusAreaID + '_' + table_point )

	# note: we use a SQL function to trap exception in case GIST index already exists as postgres 9.3 does not allow NOT EXISTS on CREATE INDEX
	# see http://dba.stackexchange.com/questions/35616/create-index-if-it-does-not-exist

	strIndexSQL = """
CREATE OR REPLACE FUNCTION create_index() RETURNS void AS $$
BEGIN
	CREATE INDEX {:s} ON {:s}.{:s} USING GIST ( geom );
EXCEPTION
	WHEN undefined_table THEN
		RETURN;
	WHEN duplicate_table THEN
		RETURN;
END;
$$ LANGUAGE plpgsql;

SELECT create_index();
""".format( strFocusAreaID + '_' + table_point + '_gist_index',schema,strFocusAreaID + '_' + table_point )

	strSQLDelete = """
DELETE FROM {:s}.{:s};
""".format( schema,strFocusAreaID + '_' + table_point )

	listStatementsTables.append( (strTableSQL,None) )
	listStatementsTables.append( (strIndexSQL,None) )
	if delete_contents == True :
		listStatementsDeletes.append( (strSQLDelete,None) )

	strTableSQL = """
CREATE TABLE IF NOT EXISTS {:s}.{:s} (
  loc_id serial,
  name text,
  osm_id_set bigint[],
  admin_regions bigint[],
  geom geometry(Geometry,4326),
  tags hstore,
  CONSTRAINT {:s}_pkey PRIMARY KEY (loc_id)
)
WITH (
  OIDS=FALSE
);
""".format( schema,strFocusAreaID + '_' + table_line,strFocusAreaID + '_' + table_line )

	strIndexSQL = """
CREATE OR REPLACE FUNCTION create_index() RETURNS void AS $$
BEGIN
	CREATE INDEX {:s} ON {:s}.{:s} USING GIST ( geom );
EXCEPTION
	WHEN undefined_table THEN
		RETURN;
	WHEN duplicate_table THEN
		RETURN;
END;
$$ LANGUAGE plpgsql;

SELECT create_index();
""".format( strFocusAreaID + '_' + table_line + '_gist_index',schema,strFocusAreaID + '_' + table_line )

	strSQLDelete = """
DELETE FROM {:s}.{:s};
""".format( schema,strFocusAreaID + '_' + table_line )

	listStatementsTables.append( (strTableSQL,None) )
	listStatementsTables.append( (strIndexSQL,None) )
	if delete_contents == True :
		listStatementsDeletes.append( (strSQLDelete,None) )

	strTableSQL = """
CREATE TABLE IF NOT EXISTS {:s}.{:s} (
  loc_id serial,
  name text,
  osm_id_set bigint[],
  admin_regions bigint[],
  geom geometry(Geometry,4326),
  tags hstore,
  CONSTRAINT {:s}_pkey PRIMARY KEY (loc_id)
)
WITH (
  OIDS=FALSE
);
""".format( schema,strFocusAreaID + '_' + table_poly,strFocusAreaID + '_' + table_poly )

	strIndexSQL = """
CREATE OR REPLACE FUNCTION create_index() RETURNS void AS $$
BEGIN
	CREATE INDEX {:s} ON {:s}.{:s} USING GIST ( geom );
EXCEPTION
	WHEN undefined_table THEN
		RETURN;
	WHEN duplicate_table THEN
		RETURN;
END;
$$ LANGUAGE plpgsql;

SELECT create_index();
""".format( strFocusAreaID + '_' + table_poly + '_gist_index',schema,strFocusAreaID + '_' + table_poly )

	strSQLDelete = """
DELETE FROM {:s}.{:s};
""".format( schema,strFocusAreaID + '_' + table_poly )

	listStatementsTables.append( (strTableSQL,None) )
	listStatementsTables.append( (strIndexSQL,None) )
	if delete_contents == True :
		listStatementsDeletes.append( (strSQLDelete,None) )

	strTableSQL = """
CREATE TABLE IF NOT EXISTS {:s}.{:s} (
  loc_id serial,
  name text,
  osm_id_set bigint[],
  admin_regions bigint[],
  geom geometry(Geometry,4326),
  tags hstore,
  CONSTRAINT {:s}_pkey PRIMARY KEY (loc_id)
)
WITH (
  OIDS=FALSE
);
""".format( schema,strFocusAreaID + '_' + table_admin,strFocusAreaID + '_' + table_admin )

	strIndexSQL = """
CREATE OR REPLACE FUNCTION create_index() RETURNS void AS $$
BEGIN
	CREATE INDEX {:s} ON {:s}.{:s} USING GIST ( geom );
EXCEPTION
	WHEN undefined_table THEN
		RETURN;
	WHEN duplicate_table THEN
		RETURN;
END;
$$ LANGUAGE plpgsql;

SELECT create_index();
""".format( strFocusAreaID + '_' + table_admin + '_gist_index',schema,strFocusAreaID + '_' + table_admin )

	strSQLDelete = """
DELETE FROM {:s}.{:s};
""".format( schema,strFocusAreaID + '_' + table_admin )

	listStatementsTables.append( (strTableSQL,None) )
	listStatementsTables.append( (strIndexSQL,None) )
	if delete_contents == True :
		listStatementsDeletes.append( (strSQLDelete,None) )

	# note: Postgres does NOT provide concurrency support for CREATE TABLE so concurrent attempts WILL result
	# in an SQL error for the 2nd attempt (actually on unique KEY validation check)
	# see: http://www.postgresql.org/message-id/CA+TgmoZAdYVtwBfp1FL2sMZbiHCWT4UPrzRLNnX1Nb30Ku3-gg@mail.gmail.com
	# solution: trap errors and ignore :(

	# execute create table statements (using first connection as this is not multi-threaded)
	try :
		# reconnect as there seems to be a thread issue with the connection object (maybe connection object is not thread safe?)
		database_handle.reconnect()

		# execute SQL
		database_handle.execute_sql_statement( listStatementsTables, timeout_statement, timeout_overall )
	except :
		if logger != None :
			logger.warning( 'SQL error in create_preprocessing_tables() : this is probably NOT an error if concurrent attempts to make table failed : ' + repr(sys.exc_info()[0]) + ' : ' + repr(sys.exc_info()[1]) )

	if delete_contents == True :
		database_handle.execute_sql_statement( listStatementsDeletes, timeout_statement, timeout_overall )


def execute_preprocessing_focus_area( focus_area, database_pool, schema, table_point = 'point', table_line = 'line', table_poly = 'poly', table_admin = 'admin', timeout_statement = 1209600, timeout_overall = 1209600, logger = None ) :
	"""
	Populates preprocessing tables with locations for a new focus area. If the area has already been precomputed it will immediately return with the location ID range. Small areas (e.g. town) take a few minutes to compute. Large areas (e.g. city) take up to 1 hour to compute. The global place type filter can 8 days to compute so the database timeout values are large.
	The database tables will be SQL locked whilst the data import is occuring to ensure new locations are allocated continuous primary key IDs,
	allowing a simple result range (start ID and end ID) to be returned as opposed to a long list of IDs for each new location.

	This funciton is process safe but not thread safe as it uses an internal Queue() object to coordinate multiple database cursors and efficiently insert data using parallel SQL inserts.

	The global area (referenced using the focus area key 'admin_lookup_table') must be already created and available in the same schema as this new focus area.

	If the table already exists and already has locations then no import wil occur (assuming area has already been preprocessed).

	:param dict focus_area: focus area description
	:param dict database_pool: pool of PostgresqlHandler.PostgresqlHandler objects for each of the 4 table types used to execute parallel SQL imports e.g. { 'admin' : PostgresqlHandler.PostgresqlHandler, ... }
	:param str schema: Postgres schema name under which tables will be created
	:param str table_point: Table name suffix to append to focus area ID to make point table
	:param str table_line: Table name suffix to append to focus area ID to make line table
	:param str table_poly: Table name suffix to append to focus area ID to make polygon table
	:param str table_admin: Table name suffix to append to focus area ID to make admin region table
	:param int timeout_statement: number of seconds to allow each SQL statement
	:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
	:param logging.Logger logger: logger object (optional)

	:return: for each table a tuple with the new location primary key ID range e.g. { 'focus1_admin' : (nLocIDStart, nLocIDEnd), ... }
	:rtype: dict
	"""

	# check args without defaults
	if not isinstance( focus_area, dict ) :
		raise Exception( 'invalid focus_area' )
	if not isinstance( database_pool, dict ) :
		raise Exception( 'invalid database_pool' )
	if (not isinstance( schema, str )) and (not isinstance( schema, unicode)) :
		raise Exception( 'invalid schema' )

	if logger != None :
		logger.info( 'starting preprocessing of new focus area : ' + repr(focus_area) )

	if not isinstance( focus_area, dict ) :
		raise Exception( 'focus_area not a dict' )
	if 'focus_area_id' in focus_area :
		strFocusAreaID = focus_area['focus_area_id']
	else :
		raise Exception( 'focus_area_id key not found in focus_area dict' )

	# tips on OpenGIS SQL
	# ST_Collect is faster than ST_Union
	# ST_Intersects is faster than ST_Contains
	# operator && uses a bounding box and is the fastest of all (but will not match true geometry so use as a pre-filter)
	# but read operation docs to understand exactly what each operator is doing!
	dictNewLocations = {}

	if 'admin_lookup_table' in focus_area :
		strAdminLookupTable = focus_area['admin_lookup_table']
	else :
		strAdminLookupTable = None

	tuplePlaceTypes = None

	# parse query and construct the SQL to use for it
	# different types of focus area request are supported and they translate to different SQL queries
	listSQLInserts = []

	# check focus area one of the required entries
	if (not 'radius' in focus_area) and (not 'geom' in focus_area) and (not 'admin' in focus_area) and (not 'osmid' in focus_area) and (not 'place_types' in focus_area) :
		raise Exception( 'unknown focus area type' )

	#
	# FOCUS AREA = RADIUS, GEOM, ADMIN, OSMID
	#

	if ('radius' in focus_area) or ('geom' in focus_area) or ('admin' in focus_area) or ('osmid' in focus_area) :

		# get filters common to these three focus area types
		strAdminName = None
		listAdminParents = None

		#
		# make SQL to get the geometry area from which to find locations to preprocess
		# geom => explicitly defined geom SQL
		# radius => explicitly defined point and radius
		# admin => name, admin, ... => geom lookup SQL
		# osmid => type, osmid => geom lookup SQL
		#
		if 'geom' in focus_area :
			strGeom = focus_area['geom']

			strGeomDefinedSQL = """
SELECT ST_GeomFromText( '{:s}',4326 ) AS geom
""".format( strGeom )

		elif 'radius' in focus_area :
			listRadiusEntity = focus_area['radius']
			if len( listRadiusEntity ) != 2 :
				raise Exception( 'radius entry is not a list [geom_str,dist_float] (check JSON focus area is correct)' )
			strGeom = listRadiusEntity[0]
			nDistance = float( listRadiusEntity[1] )

			# note: ST_Dwithin() is much quicker than defining a geom then looking for overlaps
			#       BUT this approach allows commonality with the other ways to define a geom
			# note: Units of radius are measured in units of the spatial reference system (i.e. degrees)

			strGeomDefinedSQL = """
SELECT ST_Buffer( ST_GeomFromText( '{:s}',4326 ), {:.12g} ) AS geom
""".format( strGeom, nDistance )

		elif 'admin' in focus_area :
			listAdminNames = focus_area['admin']
			if len(listAdminNames) < 1 :
				raise Exception('admin focus area does not have any names to find geom (check JSON focus area is correct)')

			if len(listAdminNames) == 1 :
				strAdminName = listAdminNames[0].lower()
				tupleAdminParents = None

				# first match returned only as there will be many matches of any given location name
				# this is a poor query!
				strGeomDefinedSQL = """
SELECT
  possible_match.geom AS geom
FROM
  (
    SELECT geom
    FROM {:s}.{:s}
    WHERE lower(name) = %s
  ) AS possible_match
LIMIT 1
""".format( schema, strAdminLookupTable )

			else :
				# note: list not tuple as we want an ARRAY['aaa','bbb' ...] not a tuple ('aaa','bbb'...) in the final SQL statement
				strAdminName = listAdminNames[0].lower()
				tupleAdminParents = tuple( [x.lower() for x in listAdminNames[1:]] )

				# use the global cities table to do an efficient lookup (otherwise it will take a very long time to match admin regions to list)
				strGeomDefinedSQL = """
SELECT
  matches.geom AS geom
FROM (
	SELECT
	  possible_match.osm_id_set AS osm_id_set,
	  possible_match.geom AS geom,
	  array_agg( lower({:s}.{:s}.name) ) AS admin_names
	FROM {:s}.{:s},
	  (
		SELECT
			geom,
			osm_id_set,
			admin_regions
		FROM {:s}.{:s}
		WHERE lower(name) = %s
	  ) AS possible_match
	WHERE 
	  {:s}.{:s}.osm_id_set != possible_match.osm_id_set
	  AND lower({:s}.{:s}.name) IN %s
	  AND {:s}.{:s}.osm_id_set && possible_match.admin_regions
	GROUP BY possible_match.osm_id_set, possible_match.geom
) AS matches
ORDER BY array_length(matches.admin_names,1) DESC
LIMIT 1
""".format( schema, strAdminLookupTable, schema, strAdminLookupTable, schema, strAdminLookupTable, schema, strAdminLookupTable, schema, strAdminLookupTable, schema, strAdminLookupTable )

		elif 'osmid' in focus_area :

			strGeomDefinedSQL = """
SELECT way AS geom FROM {:s} WHERE
""".format( 'planet_osm_polygon' )

			listOSMEntity = focus_area['osmid']
			nIndexOSM = 0
			while nIndexOSM < len( listOSMEntity ) :
				if nIndexOSM + 1 >= len( listOSMEntity ) :
					raise Exception( 'osmid list is of incorrect format (check JSON focus area is correct)' )


				# note: only relations make sense to get a closed geometry object as these
				#       are entered into the planet_osm_polygon table with a negative id
				strOSMType = listOSMEntity[nIndexOSM]
				nOSMID = int( listOSMEntity[nIndexOSM+1] )
				if strOSMType != 'relation' :
					raise Exception( 'unknown focus area OSMID type (expected relation) got (' + strOSMType + ')' )

				if nIndexOSM == 0 :
					strGeomDefinedSQL = strGeomDefinedSQL + ' osm_id = {:d} '.format( nOSMID * -1 )
				else :
					strGeomDefinedSQL = strGeomDefinedSQL + ' OR osm_id = {:d} '.format( nOSMID * -1 )

				nIndexOSM = nIndexOSM + 2

		# prepare tuple for geom WITH data (other SQL will not need data so we can do this here)
		listTuple = []
		if strAdminName != None :
			if tupleAdminParents != None :
				listTuple = [strAdminName, tupleAdminParents]
			else :
				listTuple = [strAdminName]
		tupleSQLParams = tuple( listTuple )

		#
		# ADMIN
		#

		# get the current size of the table.
		# if this is not 0 then we simply do no preprocessing and return the min and max primary key ID values
		# because the focus area has already been preprocessed
		strSQL = """SELECT MIN(loc_id), MAX(loc_id) FROM {:s}.{:s}""".format( schema,strFocusAreaID + '_' + table_admin )
		listCount = database_pool[table_admin].execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
		if len(listCount) != 1 :
			raise Exception( 'admin table row count failed' )

		# result = [(nMin,nMax)] or [(None,None)] if no rows present
		nRowStart = listCount[0][0]
		nRowEnd = listCount[0][1]
		bTableEmpty = False
		if (nRowStart == None) or (nRowEnd == None) :
			bTableEmpty = True

		if bTableEmpty == True :
			#
			# admin regions (polygons and lines closed and made into polygons) within the specified geom
			# note: we reuse the precomputed global admin levels to ensure (a) its quick (b) lines and polygons are used
			# note: we do not consider points (e.g. places like suburbs) as they do not have geom information useful to calculate subregions which is the purpose of admin area entries
			# note: we deliberately do NOT check for existing locations (and update them) as we are expected to
			#       run in parallel across multiple databases so will handle duplicates at the geoparse aggregation stage
			#       this allows global database (no parent admin regions) to be made quickly then extra (duplicate) locations added
			#       with parent admin regions filled in later on
			#

			strSQL = """
WITH
geom_defined AS (
	{:s}
  ),
admin_all AS (
	SELECT
	  name,
	  osm_id_set,
	  admin_table.geom AS geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS admin_table, geom_defined
	WHERE
	  ST_IsValid( admin_table.geom )
	  AND ST_IsValid( geom_defined.geom )
	  AND ST_Envelope( admin_table.geom ) && ST_Envelope( geom_defined.geom )
	  AND ST_Intersects( admin_table.geom, geom_defined.geom )
),
target_all AS (
	SELECT
	  name,
	  osm_id_set,
	  admin_table.geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS admin_table, geom_defined
	WHERE
	  ST_IsValid( admin_table.geom )
	  AND ST_IsValid( geom_defined.geom )
	  AND ST_Envelope( admin_table.geom ) && ST_Envelope( geom_defined.geom )
	  AND ST_Intersects( admin_table.geom, geom_defined.geom )
),
regions_to_add AS (
	SELECT
	  target_with_super_region.name AS name,
	  target_with_super_region.osm_id_set AS osm_id_set,
	  array_agg( target_with_super_region.super_region ) AS admin_regions,
	  target_with_super_region.union_way AS geom,
	  target_with_super_region.tags AS tags
	FROM
	(
		/* super region = any admin polygon that contains target polygon */
		SELECT
		  target_all.name AS name,
		  target_all.osm_id_set AS osm_id_set,
		  unnest(admin_all.osm_id_set) AS super_region,
		  target_all.geom AS union_way,
		  target_all.tags AS tags
		FROM target_all, admin_all
		WHERE
		  ST_Envelope( admin_all.geom ) && ST_Envelope( target_all.geom )
		  AND ST_Contains( admin_all.geom, target_all.geom )

		UNION
		
		/* super region = target id set so that all targets appears even if they have no super regions and done match the previous query (e.g. UK) */
		SELECT
		  target_all.name AS name,
		  target_all.osm_id_set AS osm_id_set,
		  unnest( target_all.osm_id_set ) AS super_region,
		  target_all.geom AS union_way,
		  target_all.tags AS tags
		FROM target_all

	) AS target_with_super_region
	GROUP BY target_with_super_region.name, target_with_super_region.osm_id_set, target_with_super_region.union_way, target_with_super_region.tags
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
  SELECT
	regions_to_add.name,
	regions_to_add.osm_id_set,
	regions_to_add.admin_regions,
	regions_to_add.geom,
	regions_to_add.tags
  FROM regions_to_add
RETURNING loc_id;
""".format( strGeomDefinedSQL, schema, strAdminLookupTable, schema, strAdminLookupTable, schema, strFocusAreaID + '_' + table_admin )

			listSQLInserts.append( (table_admin,strSQL,tupleSQLParams,logger,database_pool[table_admin],timeout_statement, timeout_overall) )

		else :
			# admin table aready exists so no SQL needed
			# but we still need to report the existing locations
			# as if they were just populated so subsequent code (e.g. geoparse) can process them
			dictNewLocations[ strFocusAreaID + '_' + table_admin ] = (nRowStart, nRowEnd)

		#
		# POLY : polygons NOT admin regions
		#

		# get the current size of the table.
		# if this is not 0 then we simply do no preprocessing and return the min and max primary key ID values
		# because the focus area has already been preprocessed
		strSQL = """SELECT MIN(loc_id), MAX(loc_id) FROM {:s}.{:s}""".format( schema,strFocusAreaID + '_' + table_poly )
		listCount = database_pool[table_poly].execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
		if len(listCount) != 1 :
			raise Exception( 'poly table row count failed' )

		# result = [(nMin,nMax)] or [(None,None)] if no rows present
		nRowStart = listCount[0][0]
		nRowEnd = listCount[0][1]
		bTableEmpty = False
		if (nRowStart == None) or (nRowEnd == None) :
			bTableEmpty = True

		if bTableEmpty == True :

			strSQL = """
WITH
geom_defined AS (
	{:s}
  ),
admin_all AS (
	SELECT
	  name,
	  osm_id_set,
	  admin_table.geom AS geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS admin_table, geom_defined
	WHERE
	  ST_IsValid( admin_table.geom )
	  AND ST_IsValid( geom_defined.geom )
	  AND ST_Envelope( admin_table.geom ) && ST_Envelope( geom_defined.geom )
	  AND ST_Intersects( admin_table.geom, geom_defined.geom )
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
  SELECT
	expanded_admin.name AS name,
	expanded_admin.osm_id_set AS osm_id_set,
	array_agg( expanded_admin.admin_regions ) AS admin_regions,
	expanded_admin.geom AS geom,
	expanded_admin.tags AS tags
  FROM
  (
	  SELECT
		name_poly AS name,
		unique_poly.osm_id_set AS osm_id_set,
		unnest( admin_all.osm_id_set ) AS admin_regions,
		unique_poly.union_way AS geom,
		hstore( string_to_array( way_tags_serialized, '###' ) ) AS tags
	  FROM geom_defined,admin_all,
	  (
		SELECT name AS name_poly,
		  array_agg( osm_id ) AS osm_id_set,
		  ST_Buffer( ST_Collect( array_agg( planet_osm_polygon.way ) ), 0 ) AS union_way,
		  string_agg( array_to_string( planet_osm_ways.tags,'###' ),'###' ) AS way_tags_serialized
		FROM planet_osm_polygon, planet_osm_ways, geom_defined
		WHERE
		  name IS NOT NULL
		  AND planet_osm_polygon.boundary IS NULL
		  AND planet_osm_polygon.place IS NULL
		  AND ST_IsValid( planet_osm_polygon.way )
		  AND ST_IsValid( geom_defined.geom )
		  AND ST_Envelope( planet_osm_polygon.way ) && ST_Envelope( geom_defined.geom )
		  AND ST_Intersects( planet_osm_polygon.way, geom_defined.geom )
		  AND planet_osm_ways.id = osm_id
		GROUP BY name
	  ) AS unique_poly
	  WHERE
	    ST_Envelope(admin_all.geom) && ST_Envelope(unique_poly.union_way)
	    AND ST_Contains( admin_all.geom, unique_poly.union_way )
  ) AS expanded_admin
  GROUP BY expanded_admin.name, expanded_admin.osm_id_set, expanded_admin.geom, expanded_admin.tags
RETURNING loc_id;
""".format( strGeomDefinedSQL, schema, strAdminLookupTable, schema, strFocusAreaID + '_' + table_poly )

			listSQLInserts.append( (table_poly,strSQL,tupleSQLParams,logger,database_pool[table_poly],timeout_statement, timeout_overall) )

		else :
			# poly table aready exists so no SQL needed
			# but we still need to report the existing locations
			# as if they were just populated so subsequent code (e.g. geoparse) can process them
			dictNewLocations[ strFocusAreaID + '_' + table_poly ] = (nRowStart, nRowEnd)


		#
		# LINES
		#

		# get the current size of the table.
		# if this is not 0 then we simply do no preprocessing and return the min and max primary key ID values
		# because the focus area has already been preprocessed
		strSQL = """SELECT MIN(loc_id), MAX(loc_id) FROM {:s}.{:s}""".format( schema,strFocusAreaID + '_' + table_line )
		listCount = database_pool[table_line].execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
		if len(listCount) != 1 :
			raise Exception( 'line table row count failed' )

		# result = [(nMin,nMax)] or [(None,None)] if no rows present
		nRowStart = listCount[0][0]
		nRowEnd = listCount[0][1]
		bTableEmpty = False
		if (nRowStart == None) or (nRowEnd == None) :
			bTableEmpty = True

		if bTableEmpty == True :

			strSQL = """
WITH
geom_defined AS (
	{:s}
  ),
admin_all AS (
	SELECT
	  name,
	  osm_id_set,
	  admin_table.geom AS geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS admin_table, geom_defined
	WHERE
	  ST_IsValid( admin_table.geom )
	  AND ST_IsValid( geom_defined.geom )
	  AND ST_Envelope( admin_table.geom ) && ST_Envelope( geom_defined.geom )
	  AND ST_Intersects( admin_table.geom, geom_defined.geom )
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
  SELECT
	expanded_admin.name AS name,
	expanded_admin.osm_id_set AS osm_id_set,
	array_agg( expanded_admin.admin_regions ) AS admin_regions,
	expanded_admin.geom AS geom,
	expanded_admin.tags AS tags
  FROM
  (
	  SELECT
		name_line AS name,
		unique_line.osm_id_set AS osm_id_set,
		unnest( admin_all.osm_id_set ) AS admin_regions,
		unique_line.union_way AS geom,
		hstore( string_to_array( way_tags_serialized, '###' ) ) AS tags
	  FROM admin_all,geom_defined,
	  (
		SELECT name AS name_line,
		  array_agg( osm_id ) AS osm_id_set,
		  ST_Collect( array_agg( way ) ) AS union_way,
		  string_agg( array_to_string( planet_osm_ways.tags,'###' ),'###' ) AS way_tags_serialized
		FROM planet_osm_line, planet_osm_ways, geom_defined
		WHERE
		  name IS NOT NULL
		  AND planet_osm_ways.id = osm_id
		  AND ST_IsValid( planet_osm_line.way )
		  AND ST_IsValid( geom_defined.geom )
		  AND ST_Envelope( planet_osm_line.way ) && ST_Envelope( geom_defined.geom )
		  AND ST_Intersects( planet_osm_line.way, geom_defined.geom )
		GROUP BY name
	  ) AS unique_line
	  WHERE
	    ST_Envelope(admin_all.geom) && ST_Envelope( unique_line.union_way )
	    AND ST_Contains( admin_all.geom, unique_line.union_way )
  ) AS expanded_admin
  GROUP BY expanded_admin.name, expanded_admin.osm_id_set, expanded_admin.geom, expanded_admin.tags
RETURNING loc_id;
""".format( strGeomDefinedSQL, schema, strAdminLookupTable, schema, strFocusAreaID + '_' + table_line )

			listSQLInserts.append( (table_line,strSQL,tupleSQLParams,logger,database_pool[table_line],timeout_statement, timeout_overall) )

		else :
			# line table aready exists so no SQL needed
			# but we still need to report the existing locations
			# as if they were just populated so subsequent code (e.g. geoparse) can process them
			dictNewLocations[ strFocusAreaID + '_' + table_line ] = (nRowStart, nRowEnd)

		#
		# POINT: points NOT admin regions
		#

		# get the current size of the table.
		# if this is not 0 then we simply do no preprocessing and return the min and max primary key ID values
		# because the focus area has already been preprocessed
		strSQL = """SELECT MIN(loc_id), MAX(loc_id) FROM {:s}.{:s}""".format( schema,strFocusAreaID + '_' + table_point )
		listCount = database_pool[table_point].execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
		if len(listCount) != 1 :
			raise Exception( 'point table row count failed' )

		# result = [(nMin,nMax)] or [(None,None)] if no rows present
		nRowStart = listCount[0][0]
		nRowEnd = listCount[0][1]
		bTableEmpty = False
		if (nRowStart == None) or (nRowEnd == None) :
			bTableEmpty = True

		if bTableEmpty == True :

			strSQL = """
WITH
geom_defined AS (
	{:s}
  ),
admin_all AS (
	SELECT
	  name,
	  osm_id_set,
	  admin_table.geom AS geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS admin_table, geom_defined
	WHERE
	  ST_IsValid( admin_table.geom )
	  AND ST_IsValid( geom_defined.geom )
	  AND ST_Envelope( admin_table.geom ) && ST_Envelope( geom_defined.geom )
	  AND ST_Intersects( admin_table.geom, geom_defined.geom )
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
  SELECT
	expanded_admin.name AS name,
	expanded_admin.osm_id_set AS osm_id_set,
	array_agg( expanded_admin.admin_regions ) AS admin_regions,
	expanded_admin.geom AS geom,
	expanded_admin.tags AS tags
  FROM
  (
	  SELECT
		name_point AS name,
		array[ unique_node.osm_id ] AS osm_id_set,
		unnest( admin_all.osm_id_set ) AS admin_regions,
		unique_node.way AS geom,
		hstore( point_tags ) AS tags
	  FROM admin_all,geom_defined,
	  (
		SELECT name AS name_point,
		  osm_id,
		  way,
		  planet_osm_nodes.tags AS point_tags
		FROM public.planet_osm_point, public.planet_osm_nodes, geom_defined
		WHERE
		  name IS NOT NULL
		  AND planet_osm_point.boundary IS NULL
		  AND planet_osm_point.place IS NULL
		  AND ST_IsValid( planet_osm_point.way )
		  AND ST_IsValid( geom_defined.geom )
		  AND ST_Envelope( planet_osm_point.way ) && ST_Envelope( geom_defined.geom )
		  AND ST_Intersects( planet_osm_point.way, geom_defined.geom )
		  AND planet_osm_nodes.id = planet_osm_point.osm_id
		GROUP BY name, osm_id, way, point_tags
	  ) AS unique_node
	  WHERE
	    ST_Envelope( admin_all.geom ) && ST_Envelope( unique_node.way )
	    AND ST_Contains( admin_all.geom, unique_node.way )
  ) AS expanded_admin
  GROUP BY expanded_admin.name, expanded_admin.osm_id_set, expanded_admin.geom, expanded_admin.tags
RETURNING loc_id;
""".format( strGeomDefinedSQL, schema, strAdminLookupTable, schema, strFocusAreaID + '_' + table_point )

			listSQLInserts.append( (table_point,strSQL,tupleSQLParams,logger,database_pool[table_point], timeout_statement, timeout_overall) )

		else :
			# line table aready exists so no SQL needed
			# but we still need to report the existing locations
			# as if they were just populated so subsequent code (e.g. geoparse) can process them
			dictNewLocations[ strFocusAreaID + '_' + table_point ] = (nRowStart, nRowEnd)


	#
	# FOCUS FILTER = NODES WITH PLACE TYPES
	#
	if 'place_types' in focus_area :

		# get the current size of the table (typically 1,000,000 nodes match the usual place types below city).
		# if this is not 0 then we simply do no preprocessing and return the min and max primary key ID values
		# because the focus area has already been preprocessed
		strSQL = """SELECT MIN(loc_id), MAX(loc_id) FROM {:s}.{:s}""".format( schema,strFocusAreaID + '_' + table_point )
		listCount = database_pool[table_point].execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
		if len(listCount) != 1 :
			raise Exception( 'places (point) table row count failed' )

		# result = [(nMin,nMax)] or [(None,None)] if no rows present
		nRowStart = listCount[0][0]
		nRowEnd = listCount[0][1]
		bTableEmpty = False
		if (nRowStart == None) or (nRowEnd == None) :
			bTableEmpty = True

		if bTableEmpty == True :

			# get super regions if any otherwise assume its a global places request
			if 'parent_osmid' in focus_area :

				# compute each parent_osmid separately as the admin lookup is sqr(n) calculation since admin areas are cross-checked vs places. the more admin areas and places, and sqr(n) more cross checks to perform

				nIndexOSM = 0
				while nIndexOSM < len( focus_area['parent_osmid'] ) :
					if nIndexOSM + 1 >= len( focus_area['parent_osmid'] ) :
						raise Exception( 'parent osmid list is of incorrect format (check JSON focus area is correct)' )

					listIDs = []

					# note: only relations make sense to get a closed geometry object as these
					#       are entered into the planet_osm_polygon table with a negative id
					strOSMType = focus_area['parent_osmid'][nIndexOSM]
					nOSMID = int( focus_area['parent_osmid'][nIndexOSM+1] )
					if strOSMType != 'relation' :
						raise Exception( 'unknown focus area parent OSMID type (expected relation) got (' + strOSMType + ')' )

					listIDs.append( nOSMID * -1 )
					nIndexOSM = nIndexOSM + 2

					# check 'place' is in the tags array then check one of the place types is also present
					# OSM uses text[] not hstore() so we need to so array overlap && operator not key and value check
					# note: pass a LIST not a tuple for listIDs so it is converted to a ARRAY not a RECORD
					tupleSQLParams = tuple( [ listIDs, listIDs, tuple(focus_area['place_types']) ] )

					strSQL = """
WITH
admin_all AS (
	SELECT
	  name,
	  osm_id_set,
	  geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS table_admin
	WHERE
	  table_admin.admin_regions && %s::bigint[]
	  AND ST_IsValid( table_admin.geom )

),
target_all AS (
	SELECT
	  admin_all.geom
	FROM admin_all
	WHERE
	  admin_all.osm_id_set && %s::bigint[]
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
  SELECT
	expanded_admin.name AS name,
	expanded_admin.osm_id_set AS osm_id_set,
	array_agg( expanded_admin.admin_regions ) AS admin_regions,
	expanded_admin.geom AS geom,
	expanded_admin.tags AS tags
  FROM
  (
	  SELECT
		unique_node.name AS name,
		array[ unique_node.osm_id ] AS osm_id_set,
		unnest( admin_all.osm_id_set ) AS admin_regions,
		unique_node.way AS geom,
		hstore( unique_node.tags ) AS tags
	  FROM admin_all,
	  (
		SELECT
		  planet_osm_point.name AS name,
		  planet_osm_point.osm_id AS osm_id,
		  planet_osm_point.way AS way,
		  planet_osm_nodes.tags AS tags
		FROM planet_osm_point, planet_osm_nodes, target_all
		WHERE
		  planet_osm_point.name IS NOT NULL
		  AND planet_osm_point.place IN %s
		  AND ST_IsValid( planet_osm_point.way )
		  AND ST_Envelope( target_all.geom ) && planet_osm_point.way
		  AND ST_Contains( target_all.geom, planet_osm_point.way )
		  AND planet_osm_nodes.id = planet_osm_point.osm_id
	  ) AS unique_node
	  WHERE
	    ST_Envelope( admin_all.geom ) && ST_Envelope( unique_node.way )
	    AND ST_Contains( admin_all.geom, unique_node.way )
  ) AS expanded_admin
  GROUP BY expanded_admin.name, expanded_admin.osm_id_set, expanded_admin.geom, expanded_admin.tags
RETURNING loc_id;
""".format( schema, strAdminLookupTable, schema, strFocusAreaID + '_' + table_point )

					# add SQL to list
					listSQLInserts.append( (table_point,strSQL,tupleSQLParams,logger,database_pool[table_point], timeout_statement, timeout_overall) )

			else : 
				# check first 'place' is in the tags array then check one of the place types is also present
				# OSM uses text[] not hstore() so we need to so array overlap && operator not key and value check
				# note: this takes too long to test but in the future machines ight be quick enough to run it in under 2 weeks!
				tupleSQLParams = tuple( [ tuple(focus_area['place_types']) ] )

				strSQL = """
WITH
admin_all AS (
	SELECT
	  name,
	  osm_id_set,
	  geom,
	  admin_regions,
	  tags
	FROM {:s}.{:s} AS table_admin
	WHERE
	  ST_IsValid( table_admin.geom )
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
  SELECT
	expanded_admin.name AS name,
	expanded_admin.osm_id_set AS osm_id_set,
	array_agg( expanded_admin.admin_regions ) AS admin_regions,
	expanded_admin.geom AS geom,
	expanded_admin.tags AS tags
  FROM
  (
	  SELECT
		unique_node.name AS name,
		array[ unique_node.osm_id ] AS osm_id_set,
		unnest( admin_all.osm_id_set ) AS admin_regions,
		unique_node.way AS geom,
		hstore( unique_node.tags ) AS tags
	  FROM admin_all,
	  (
		SELECT
		  planet_osm_point.name AS name,
		  planet_osm_point.osm_id AS osm_id,
		  planet_osm_point.way AS way,
		  planet_osm_nodes.tags AS tags
		FROM planet_osm_point, planet_osm_nodes
		WHERE
		  name IS NOT NULL
		  AND planet_osm_point.place IN %s
		  AND ST_IsValid( planet_osm_point.way )
		  AND planet_osm_nodes.id = planet_osm_point.osm_id
	  ) AS unique_node
	  WHERE
	    ST_Envelope( admin_all.geom ) && ST_Envelope( unique_node.way )
		AND ST_Contains( admin_all.geom, unique_node.way )
  ) AS expanded_admin
  GROUP BY expanded_admin.name, expanded_admin.osm_id_set, expanded_admin.geom, expanded_admin.tags
RETURNING loc_id;
""".format( schema, strAdminLookupTable, schema, strFocusAreaID + '_' + table_point )

				# add SQL to list
				listSQLInserts.append( (table_point,strSQL,tupleSQLParams,logger,database_pool[table_point], timeout_statement, timeout_overall) )

		else :
			# line table aready exists so no SQL needed
			# but we still need to report the existing locations
			# as if they were just populated so subsequent code (e.g. geoparse) can process them
			dictNewLocations[ strFocusAreaID + '_' + table_point ] = (nRowStart, nRowEnd)

	# execute SQL inserts as query as we want results
	# use parallel threads to execute SQL simultaneously for increased performance
	# with a thread safe queue per table to track location ID results at end
	# result = { db_table : (loc_start, loc_end) ... }
	queueSQLInsertResults = { table_point : Queue.Queue(), table_line : Queue.Queue(), table_poly : Queue.Queue(), table_admin : Queue.Queue() }

	if logger != None :
		logger.info( 'starting SQL threads' )

	listThreads = []
	for strTableName in [ table_point, table_line, table_poly, table_admin ] :
		# one thread per table type
		# to ensure we sequentially add entriies to individual tables and therefore get back sequential ranges of p_id's
		# which we will report start/end later
		# note: non-sequential p_id entries will mean start/end will capture locations NOT part of a focus area (e.g. parallel inserts into admin table interleaving p_id's)
		listTupleSQLInsert = []

		for tupleSQLInsert in listSQLInserts :
			if tupleSQLInsert[0] == strTableName :
				listTupleSQLInsert.append( tupleSQLInsert )
		if len(listTupleSQLInsert) > 0 :

			# add an initial EXCLUSIVE table lock which only allows ACCESS SHARE (i.e. read only) to happen in parallel during table inserts
			# so we are process and thread safe for multiple table inserts (e.g. admin poly + admin point)
			# this is really important as we will return a start + end loc id and therefore assume we get a continuous loc id result set
			# note: lock duration is the transaction so will be released once the commit() occurs (there is no unlock in Postgres as such)
			# http://www.postgresql.org/docs/9.1/static/sql-lock.html
			strLock = """LOCK {:s}.{:s} IN EXCLUSIVE MODE;""".format( schema, strFocusAreaID + '_' + strTableName )
			tupleLock = ( strTableName, strLock, None, logger, database_pool[strTableName], timeout_statement, timeout_overall )
			listTupleSQLInsert.insert( 0,tupleLock )

			threadBuffer = threading.Thread( target = thread_worker_sql_insert, args = (listTupleSQLInsert,queueSQLInsertResults,logger) )
			threadBuffer.daemon = False
			threadBuffer.start()
			listThreads.append( threadBuffer )

	if logger != None :
		logger.info( 'waiting for joins' )

	for threadEntry in listThreads :
		threadEntry.join()
	if logger != None :
		logger.info( 'join successful' )

	for strTableName in [ table_point, table_line, table_poly, table_admin ] :
		if queueSQLInsertResults[ strTableName ].empty() == False :
			nLocIDStart = -1
			nLocIDEnd = -1
			while queueSQLInsertResults[ strTableName ].empty() == False :
				nLocID = queueSQLInsertResults[ strTableName ].get()
				if (nLocIDStart == -1) or (nLocIDStart > nLocID) :
					nLocIDStart = nLocID
				if (nLocIDEnd == -1) or (nLocIDEnd < nLocID) :
					nLocIDEnd = nLocID

			dictNewLocations[ strFocusAreaID + '_' + strTableName ] = (nLocIDStart,nLocIDEnd)

	if logger != None :
		logger.debug( 'LOC IDs = ' + repr(dictNewLocations) )

	return dictNewLocations

def execute_preprocessing_global( global_area, database_pool, schema, table_point = 'point', table_line = 'line', table_poly = 'poly', table_admin = 'admin', timeout_statement = 1209600, timeout_overall = 1209600, logger = None ) :
	"""
	Populates preprocessing tables with locations for a global area. This can take a very long time (about 12 days on a modest server machine in 2016) so the default database timeout values are large.
	The database tables will be SQL locked whilst the data import is occuring to ensure new locations are allocated continuous primary key IDs,
	allowing a simple result range (start ID and end ID) to be returned as opposed to a long list of IDs for each new location.

	This funciton is process safe but not thread safe as it uses an internal Queue() object to coordinate multiple database cursors and efficiently insert data using parallel SQL inserts.

	A global area must be created before individual focus areas can be created since it will contain for each admin region all its super regions, calculated based on PostGIS geometry.

	If the table already exists and already has locations then no import wil occur (assuming area has already been preprocessed).

	:param dict global_area: global area description
	:param dict database_pool: pool of PostgresqlHandler.PostgresqlHandler objects for each of the 4 table types used to execute parallel SQL imports e.g. { 'admin' : PostgresqlHandler.PostgresqlHandler, ... }
	:param str schema: Postgres schema name under which tables will be created
	:param str table_point: Table name suffix to append to focus area ID to make point table
	:param str table_line: Table name suffix to append to focus area ID to make line table
	:param str table_poly: Table name suffix to append to focus area ID to make polygon table
	:param str table_admin: Table name suffix to append to focus area ID to make admin region table
	:param int timeout_statement: number of seconds to allow each SQL statement
	:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
	:param logging.Logger logger: logger object (optional)

	:return: for each table a tuple with the new location primary key ID range e.g. { 'global_admin' : (nLocIDStart, nLocIDEnd), ... }
	:rtype: dict
	"""

	# check args without defaults
	if not isinstance( global_area, dict ) :
		raise Exception( 'invalid global_area' )
	if not isinstance( database_pool, dict ) :
		raise Exception( 'invalid database_pool' )
	if (not isinstance( schema, str )) and (not isinstance( schema, unicode)) :
		raise Exception( 'invalid schema' )

	if logger != None :
		logger.info( 'starting preprocessing of global admin : ' + repr(global_area) )

	if not isinstance( global_area, dict ) :
		raise Exception( 'focus_area not a dict' )
	if 'focus_area_id' in global_area :
		strFocusAreaID = global_area['focus_area_id']
	else :
		raise Exception( 'focus_area_id key not found in global_area' )


	# tips on OpenGIS SQL
	# ST_Collect is faster than ST_Union
	# ST_Intersects is faster than ST_Contains
	# operator && uses a bounding box and is the fastest of all (but will not match true geometry so use as a pre-filter)
	# but read operation docs to understand exactly what each operator is doing!
	dictNewLocations = {}

	# get focus area metadata for parent admin region calculation
	if 'max_admin_level' in global_area :
		nMaxAdminLevel = global_area['max_admin_level']
	else :
		raise Exception( 'max_admin_level key not found in global_area' )

	# make a list like ['1','2',...] for the SQL as admin levels are actually string values on OSM tables
	listAdminLevels = range(1,nMaxAdminLevel+1)
	for nIndex in range(len(listAdminLevels)) :
		listAdminLevels[nIndex] = str( listAdminLevels[nIndex] )

	# if we are asked to download admin regions then use a custom admin level range
	tupleAdminLevels = tuple( listAdminLevels )

	# parse query and construct the SQL to use for it
	# different types of focus area request are supported and they translate to different SQL queries
	listSQLInserts = []

	# get the current size of the table.
	# if this is not 0 then we simply do no preprocessing and return the min and max primary key ID values
	# because the focus area has already been preprocessed
	strSQL = """SELECT MIN(loc_id), MAX(loc_id) FROM {:s}.{:s}""".format( schema,strFocusAreaID + '_' + table_admin )
	listCount = database_pool[table_admin].execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
	if len(listCount) != 1 :
		raise Exception( 'global table row count failed' )

	# result = [(nMin,nMax)] or [(None,None)] if no rows present
	nRowStart = listCount[0][0]
	nRowEnd = listCount[0][1]
	bTableEmpty = False
	if (nRowStart == None) or (nRowEnd == None) :
		bTableEmpty = True

	# insert global admin regions ONLY if table is empty
	if bTableEmpty == True :

		# note: there can be several entries for a single osmid with different ways and we allow them all as its miles too slow to ST_Buffer into a single polygon
		#       this means there will be multiple entires for some (OSMID, name) entries each with a different way
		# note: check for line admin entries also as Wales is a line (!!!!) not a polygon (its not even a closed line so cannot make a polygon from it !!!!!)
		#       make all lines into polygons (adding start point to ensure its closed)
		# note: some places have a line AND a polygon entry so we only get line if there is no polygon available
		# note: deliberately allow the parent id == target id since if we have a top level region (e.g. UK) it will not have a parent so wont match WHERE clause and will not be returned
		# note: using a UNION (not UNION ALL) removes duplicates
		# note: use {osm_id_set} not osm_id to keep symetry with poly table where many ways with their own ids are aggregated into a single polygon
		# note: use ST_IsRing filter for lines that are simple and closed before making them into polygons otherwise otherwise we get a GEOMContains error later during ST_Contains

		strSQL = """
WITH
admin_poly AS (
SELECT
  planet_osm_polygon.osm_id AS osm_id,
  planet_osm_polygon.name AS name,
  array[ planet_osm_polygon.osm_id ] AS osm_id_set,
  planet_osm_polygon.way AS union_way,
  hstore( array['name',planet_osm_polygon.name] || array['ref',planet_osm_polygon.ref] || array['admin level',planet_osm_polygon.admin_level] || array['place',planet_osm_polygon.place] || hstore_to_array( planet_osm_polygon.tags ) ) AS tags
FROM planet_osm_polygon
WHERE
  planet_osm_polygon.name IS NOT NULL
  AND planet_osm_polygon.boundary = 'administrative'
  AND planet_osm_polygon.admin_level IN %s
  AND ST_IsValid( planet_osm_polygon.way )
),
admin_lines AS (
SELECT
  original_line.osm_id AS osm_id,
  original_line.name AS name,
  original_line.osm_id_set AS osm_id_set,
  ST_MakePolygon( original_line.closed_line ) AS union_way,
  original_line.tags AS tags
FROM
  (
	SELECT
	  planet_osm_line.osm_id AS osm_id,
	  planet_osm_line.name AS name,
	  array[ planet_osm_line.osm_id ] AS osm_id_set,
	  ST_AddPoint( planet_osm_line.way, ST_StartPoint( planet_osm_line.way ) ) AS closed_line,
	  hstore( array['name',planet_osm_line.name] || array['ref',planet_osm_line.ref] || array['admin level',planet_osm_line.admin_level] || array['place',planet_osm_line.place] || hstore_to_array( planet_osm_line.tags ) ) AS tags
	FROM planet_osm_line
	WHERE
	  NOT EXISTS( SELECT planet_osm_line.osm_id FROM admin_poly WHERE planet_osm_line.osm_id = admin_poly.osm_id )
	  AND planet_osm_line.name IS NOT NULL
	  AND planet_osm_line.boundary = 'administrative'
	  AND planet_osm_line.admin_level IN %s
	  AND ST_IsValid( planet_osm_line.way )
	  AND ST_NumPoints( planet_osm_line.way ) > 3
  ) AS original_line
WHERE
  ST_IsRing( original_line.closed_line )
),
admin_all AS (
SELECT * FROM admin_poly
UNION
SELECT * FROM admin_lines
),
target_all AS (
SELECT * FROM admin_poly
UNION
SELECT * FROM admin_lines
)
INSERT INTO {:s}.{:s} ( name,osm_id_set,admin_regions,geom,tags )
SELECT
  target_with_super_region.name,
  target_with_super_region.osm_id_set,
  array_agg( target_with_super_region.super_region ) AS admin_regions,
  target_with_super_region.union_way,
  target_with_super_region.tags
FROM
(
	/* super region = any polygon that contains target polygon */
	SELECT
	  target_all.name AS name,
	  target_all.osm_id_set AS osm_id_set,
	  admin_all.osm_id AS super_region,
	  target_all.union_way AS union_way,
	  target_all.tags AS tags
	FROM target_all, admin_all
	WHERE
	  ST_IsValid( admin_all.union_way )
	  AND admin_all.union_way && ST_Envelope( target_all.union_way )
	  AND ST_Contains( admin_all.union_way, target_all.union_way )

	UNION

	/* super region = target id set so that all targets appears even if they have no super regions and done match the previous query (e.g. UK) */
	SELECT
	  target_all.name AS name,
	  target_all.osm_id_set AS osm_id_set,
	  unnest( target_all.osm_id_set ) AS super_region,
	  target_all.union_way AS union_way,
	  target_all.tags AS tags
	FROM target_all
) AS target_with_super_region
GROUP BY target_with_super_region.osm_id_set, target_with_super_region.name, target_with_super_region.union_way, target_with_super_region.tags
RETURNING loc_id;
""".format( schema, strFocusAreaID + '_' + table_admin )

		tupleSQLParams = (tupleAdminLevels, tupleAdminLevels )
		listSQLInserts.append( (table_admin,strSQL,tupleSQLParams,logger,database_pool[table_admin], timeout_statement, timeout_overall) )

	else :
		# global table aready exists so no SQL needed
		# but we still need to report the existing locations
		# as if they were just populated so subsequent code (e.g. geoparse) can process them
		dictNewLocations[ strFocusAreaID + '_' + table_admin ] = (nRowStart, nRowEnd)

	# execute SQL inserts as query as we want results
	# use parallel threads to execute SQL simultaneously for increased performance
	# with a thread safe queue per table to track location ID results at end
	# result = { db_table : (loc_start, loc_end) ... }
	queueSQLInsertResults = { table_point : Queue.Queue(), table_line : Queue.Queue(), table_poly : Queue.Queue(), table_admin : Queue.Queue() }

	if logger != None :
		logger.info( 'starting SQL threads' )
	listThreads = []
	for strTableName in [ table_point, table_line, table_poly, table_admin ] :
		# one thread per table type
		# to ensure we sequentially add entriies to individual tables and therefore get back sequential ranges of p_id's
		# which we will report start/end later
		# note: non-sequential p_id entries will mean start/end will capture locations NOT part of a focus area (e.g. parallel inserts into admin table interleaving p_id's)
		listTupleSQLInsert = []

		for tupleSQLInsert in listSQLInserts :
			if tupleSQLInsert[0] == strTableName :
				listTupleSQLInsert.append( tupleSQLInsert )
		if len(listTupleSQLInsert) > 0 :

			# add an initial EXCLUSIVE table lock which only allows ACCESS SHARE (i.e. read only) to happen in parallel during table inserts
			# so we are process and thread safe for multiple table inserts (e.g. admin poly + admin point)
			# this is really important as we will return a start + end loc id and therefore assume we get a continuous loc id result set
			# note: lock duration is the transaction so will be released once the commit() occurs (there is no unlock in Postgres as such)
			# http://www.postgresql.org/docs/9.1/static/sql-lock.html
			strLock = """LOCK {:s}.{:s} IN EXCLUSIVE MODE;""".format( schema, strFocusAreaID + '_' + strTableName )
			tupleLock = ( strTableName, strLock, None, logger, database_pool[strTableName], timeout_statement, timeout_overall )
			listTupleSQLInsert.insert( 0,tupleLock )

			threadBuffer = threading.Thread( target = thread_worker_sql_insert, args = (listTupleSQLInsert,queueSQLInsertResults,logger) )
			threadBuffer.daemon = False
			threadBuffer.start()
			listThreads.append( threadBuffer )

	if logger != None :
		logger.info( 'waiting for joins' )

	for threadEntry in listThreads :
		threadEntry.join()
	if logger != None :
		logger.info( 'join successful' )

	for strTableName in [ table_point, table_line, table_poly, table_admin ] :
		if queueSQLInsertResults[ strTableName ].empty() == False :
			nLocIDStart = -1
			nLocIDEnd = -1
			while queueSQLInsertResults[ strTableName ].empty() == False :
				nLocID = queueSQLInsertResults[ strTableName ].get()
				if (nLocIDStart == -1) or (nLocIDStart > nLocID) :
					nLocIDStart = nLocID
				if (nLocIDEnd == -1) or (nLocIDEnd < nLocID) :
					nLocIDEnd = nLocID

			dictNewLocations[ strFocusAreaID + '_' + strTableName ] = (nLocIDStart,nLocIDEnd)

	if logger != None :
		logger.debug( 'LOC IDs = ' + repr(dictNewLocations) )

	return dictNewLocations

def thread_worker_sql_insert( sql_list, sql_result_queue_dict, logger = None ) :
	"""
	Internal thread callback function to preprocess a new area. This function should nenver be called independantly of the execute_preprocessing_global() or execute_preprocessing_focus_area() functions.

	All sql imports in list must be for the same database as we lock that database for the entire transaction to ensure inserted location IDs are sequential.

	:param list sql_list: list of info required to execute sql query e.g. [ ('focus1_admin',sql_query_str,tuple_sql_data,logger,database_handle,timeout_statement,timeout_overall), ... ]
	:param dict sql_result_queue_dict: dict of Queue() instances for each table type to store SQL results in a thread safe way e.g. { 'focus1_admin' : Queue(), ... }
	"""

	try :

		# check args without defaults
		if not isinstance( sql_list, list ) :
			raise Exception( 'invalid sql_list' )
		if not isinstance( sql_result_queue_dict, dict ) :
			raise Exception( 'invalid sql_result_queue_dict' )

		# nothing to do ?
		if len(sql_list) == 0 :
			return

		# get database details (first entry as they should all be the same)
		logger = sql_list[0][3]
		dbHandler = sql_list[0][4]
		timeout_statement = sql_list[0][5]
		timeout_overall = sql_list[0][6]

		# perform inserts sequentially for a specific table so we dont interleave p_id values
		# for example if we have a focus area adding point + polygon data in two parallel threads
		# note: all queries will be run in a transaction so this is process safe
		listSQL = []
		for tupleSQLInsert in sql_list :
			listSQL.append( (tupleSQLInsert[1],tupleSQLInsert[2]) )

		# note: use the SQL handler associated with this table as we will run SQL commands in a multi-threaded
		#       way for maximum performance. cannot use multi SQL cursors as this will add all commands to a single
		#       transaction, which is serial and not the same as using 4 seperate connections in parallel

		if logger != None :
			logger.info('start SQL (' + sql_list[0][0] + ' x ' + str(len(sql_list)) + ') ...' )

		# reconnect as there seems to be a thread issue with the connection object (maybe connection object is not thread safe?)
		dbHandler.reconnect()

		# execute SQL
		listNewIDs = dbHandler.execute_sql_query_batch( listSQL, timeout_statement, timeout_overall )

		if logger != None :
			logger.info('... end SQL (' + sql_list[0][0] + ' x ' + str(len(sql_list)) + ') ...' )

		# parse SQL result [(loc_id,)...]
		for tupleLocID in listNewIDs :
			sql_result_queue_dict[ sql_list[0][0] ].put( tupleLocID[0] )

	except :
		if logger != None :
			logger.exception( 'thread_worker_sql_insert() exception (location results will be ignored)' )


def cache_preprocessed_locations( database_handle, location_ids, schema, geospatial_config, timeout_statement = 600, timeout_overall = 600, spatial_filter = None ) :
	"""
	Load a set of previously preprocessed locations from database. The cached location structure returned is used by geo_parse_lib functions.

	:param PostgresqlHandler.PostgresqlHandler database_handle: handle to database object
	:param dict location_ids: for each table the range of locations ids to load. A -1 for min or max indicates no min or max range. Use a range of (-1,-1) for all locations. e.g. { 'focus1_admin' : [nStartID,nEndID], ... }
	:param str schema: Postgres schema name under which tables will be created
	:param dict geospatial_config: config object returned from a call to geo_parse_lib.get_geoparse_config()
	:param int timeout_statement: number of seconds to allow each SQL statement
	:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
	:param str spatial_filter: OpenGIS spatial polygon to use as a spatial filter for returned locations (ST_Intersects used). This is optional and can be None.

	:return: list structure containing location information to be used by geo_parse_lib functions e.g. [loc_id,name,(osm_id,...),(admin_id,...),ST_AsText(geom),{tag:value},(variant_phrase, ...)]
	:rtype: list
	"""

	# check args without defaults
	if not isinstance( database_handle, PostgresqlHandler.PostgresqlHandler ) :
		raise Exception( 'invalid database_pool' )
	if not isinstance( location_ids, dict ) :
		raise Exception( 'invalid location_ids' )
	if (not isinstance( schema, str )) and (not isinstance( schema, unicode)) :
		raise Exception( 'invalid schema' )
	if not isinstance( geospatial_config, dict ) :
		raise Exception( 'invalid geospatial_config' )


	if geospatial_config['logger'] != None :
		geospatial_config['logger'].info( 'caching locations : ' + repr(location_ids) )

	# loop on each source to allow source filtering
	# and get data in smaller chunks to avoid running out of memory (e.g. geonames has 3 million entries)
	listPlaceData = []
	listKeys = location_ids.keys()
	listSQL = []
	for strTableName in listKeys :

		listLocIDs = location_ids[ strTableName ]
		if (spatial_filter != None) and (len(spatial_filter) > 0) :
			strSpatialClause = """ST_Intersects( geom, ST_GeomFromText( '{:s}',4326 ) )""".format( spatial_filter )
		else :
			strSpatialClause = None

		# query to get all locations within the range specified
		# note: make a unique location ID by adding the table name to end (e.g. '123_flood_ny_admin')
		# note: hstore_to_matrix() will convert tags::hstore to a 2d array {{key,value},...}
		# result = tuple = (1, 'Saxon Wharf', [-3519617L], [-62149L, -151304L, -127864L, -3519617L], 'POLYGON((...))', {{'name':'Saxon Wharf'},{'type':'multipolygon'}, {'place':'locality'}, {'landuse':'industrial'}, {'source:location':'Bing Imagery'}}')

		if (listLocIDs[0] > -1) and (listLocIDs[1] > -1) :
			strSQLQuery = """SELECT concat('{:s}_',loc_id),name,osm_id_set,admin_regions,ST_AsText(geom),hstore_to_matrix(tags) FROM {:s}.{:s} WHERE loc_id >= %s AND loc_id <= %s""".format( strTableName, schema, strTableName )
			tupleSQLParams = (listLocIDs[0], listLocIDs[1])
		elif (listLocIDs[0] > -1) :
			strSQLQuery = """SELECT concat('{:s}_',loc_id),name,osm_id_set,admin_regions,ST_AsText(geom),hstore_to_matrix(tags) FROM {:s}.{:s} WHERE loc_id >= %s""".format( strTableName, schema, strTableName )
			tupleSQLParams = (listLocIDs[0],)
		elif (listLocIDs[1] > -1) :
			strSQLQuery = """SELECT concat('{:s}_',loc_id),name,osm_id_set,admin_regions,ST_AsText(geom),hstore_to_matrix(tags) FROM {:s}.{:s} WHERE loc_id <= %s""".format( strTableName, schema, strTableName )
			tupleSQLParams = (listLocIDs[1],)
		else :
			strSQLQuery = """SELECT concat('{:s}_',loc_id),name,osm_id_set,admin_regions,ST_AsText(geom),hstore_to_matrix(tags) FROM {:s}.{:s}""".format( strTableName, schema, strTableName )
			tupleSQLParams = None

		# add spatial query if needed
		if strSpatialClause != None :
			if tupleSQLParams == None :
				strSQLQuery = strSQLQuery + ' WHERE ' + strSpatialClause
			else :
				strSQLQuery = strSQLQuery + ' AND ' + strSpatialClause

		# add statement to list for execution
		listSQL.append( (strSQLQuery, tupleSQLParams) )

	# note: SQL returns UTF8 encoded <str> objects. to get <unicode> use unicode( strText, 'utf8' )
	listRows = database_handle.execute_sql_query_batch( listSQL, timeout_statement, timeout_overall )

	listResult = []
	if len(listRows) > 0 :
		for listLocationData in listRows :
			# make SQL tuple result into a list so we can append to it
			# we will later make a hashtable linking location tokens to the cached lists row index
			listEntry = list( listLocationData )

			# convert name text to unicode()
			listEntry[1] = unicode( listEntry[1], 'utf8' )

			# make a dict from the 2d array SQL returns for tags
			# and replace the 2d array (dict is a lot quicker to search)
			# note: ignore OSM NULL values for tags (e.g. ref = NULL)
			# note: REMOVE any _ characters as OSM is inconsistent and varies between 'admin level' and 'admin_level'
			dictTags = {}
			for listTagValue in listEntry[5] :
				if listTagValue[1] != None :
					strTag = unicode( listTagValue[0], 'utf8' ).replace( '_',' ' )
					strValue = unicode( listTagValue[1], 'utf8' )
					if not strTag in dictTags :
						dictTags[ strTag ] = strValue
			listEntry[5] = dictTags

			# convert lists of OSM IDs to tuples so we can use them as indexs in dictionaries
			listEntry[2] = tuple( listEntry[2] )
			listEntry[3] = tuple( listEntry[3] )

			# get the basic phrase for this location
			strPhrase = common_parse_lib.clean_text( listEntry[1], geospatial_config )

			# get an alternative names (e.g. language variants, ref, alt) from the tag data
			# and for building/street/admin names do language specific token expansion
			listVariantPhrases = geo_parse_lib.expand_osm_alternate_names( listEntry[2], strPhrase, dictTags, geospatial_config )

			# add full set of name variants as an extra dimension at end of location info
			listEntry.append( tuple( listVariantPhrases ) )

			# add location entry to result set
			listResult.append( listEntry )

	# DEBUG
	#for nIndex in range(0,100) :
	#	if len(listResult) > nIndex :
	#		dictGeospatialConfig['logger'].info( 'PRE_SET = ' + repr(listResult[nIndex][2]) + ' : ' + repr(listResult[nIndex][6]) )
	#for nIndex in range(0,1000) :
	#	if listResult[nIndex][1] == 'Paris' :
	#		dictGeospatialConfig['logger'].info( 'PRE_PARIS = ' + repr(listResult[nIndex][2]) + ' : ' + repr(listResult[nIndex][6]) + ' : ' + repr(listResult[nIndex][5]) )



	# all done
	return listResult

def get_point_for_osmid( osm_id, osm_type, geom, database_handle, timeout_statement = 60, timeout_overall = 60 ) :
	"""
	calculate a representative point for a OSMID. if its a relation lookup the admin centre, capital or label node members. if its a node use that point. otherwise use shapely lib to calc a centroid point for this polygon.
	this function requires a database connection to OSM planet database

	:param int osm_id: OSM ID of a relation, way or node
	:param str osm_type: OSM Type as returned by geo_parse_lib.calc_OSM_type()
	:param str geom: OpenGIS geometry for OSM ID
	:param PostgresqlHandler.PostgresqlHandler database_handle: handle to database object connected to OSM database (with tables public.planet_osm_point and public.planet_osm_rels available)
	:param int timeout_statement: number of seconds to allow each SQL statement
	:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)

	:return: coordinates (long, lat) for a point that represents this OSM ID well (e.g. admin centre or centroid)
	:rtype: tuple
	"""

	# check args without defaults
	if (not isinstance( osm_id, int )) and (not isinstance( osm_id, long )) :
		raise Exception( 'invalid osm_id' )
	if (not isinstance( osm_type, str )) and (not isinstance( osm_type, unicode )) :
		raise Exception( 'invalid osm_type' )
	if (not isinstance( geom, str )) and (not isinstance( geom, unicode )) :
		raise Exception( 'invalid geom' )
	if not isinstance( database_handle, PostgresqlHandler.PostgresqlHandler ) :
		raise Exception( 'invalid database_handle' )

	# for admin areas try to find the admin centre node (if there is one)
	# note: only rels table has a members column that might include a label or admin centre, ways do not
	if osm_type == 'admin' :

		if osm_id < 0 :

			strSQL = """
select members from public.planet_osm_rels WHERE id = {:s}
""".format( str(-1*osm_id) )

			listRows = database_handle.execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
			if len( listRows ) == 0 :
				raise Exception( 'relation found without an entry in planet_osm_rels : ' + str(osm_id) )
			listMembers = listRows[0][0]

			if ('admin_centre' in listMembers) or ('label' in listMembers) or ('capital' in listMembers) :
			
				# get admin_centre or if not present capital or label node for the point of choice
				if listMembers.count( 'admin_centre' ) > 0 :
					nIndex = listMembers.index( 'admin_centre' )
				elif listMembers.count( 'capital' ) > 0 :
					nIndex = listMembers.index( 'capital' )
				else :
					nIndex = listMembers.index( 'label' )

				if nIndex == 0 :
					raise Exception( 'admin_centre or label at index 0 in list (should be impossible) : ' + str(osm_id) )

				# get admin centre and if its a node get the point (otherwise fall back to centroid calculation)
				strAdminCentreOSMID = listMembers[ nIndex-1 ]
				if strAdminCentreOSMID.startswith( 'n' ) :

					nAdminCentreOSMID = long( strAdminCentreOSMID[ 1: ] )

					strSQL = """
select ST_AsText( way ) from public.planet_osm_point WHERE osm_id = {:s}
""".format( str(nAdminCentreOSMID) )
					# note: the long lat in planet_osm_nodes is NOT a proper coordinate and the point way column should be used instead

					# note: its possible node references is not in point table as mistakes happen in OSM
					listRows = database_handle.execute_sql_query( (strSQL,None), timeout_statement, timeout_overall )
					if len( listRows ) != 0 :
						strGeom = listRows[0][0]
						if not strGeom.startswith('POINT(') :
							raise Exception( 'OSM node geom not a point (should be impossible) : ' + str(nAdminCentreOSMID) )
						tupleCoords = strGeom[6:-1].split(' ')
						nLong = float( tupleCoords[0] )
						nLat = float( tupleCoords[1] )
						return ( nLong, nLat )

	# otherwise use shapely to calculate a representative point
	shapeGeom = shapely.wkt.loads( geom )
	if isinstance( shapeGeom, shapely.geometry.point.Point ) :
		pointC = shapeGeom
	else :
		pointC = shapeGeom.centroid
	
	# check for a fail response as some OSM node points appear to fail (!)
	if (pointC == None) or (pointC.coords == []) :
		return None

	# return point coordinates (long, lat)
	nX = float( pointC.x )
	nY = float( pointC.y )
	return (nX,nY)
