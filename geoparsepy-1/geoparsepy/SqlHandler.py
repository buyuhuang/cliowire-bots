# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
..
	/////////////////////////////////////////////////////////////////////////
	//
	// (c) Copyright University of Southampton IT Innovation, 2014
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
	//	Created Date :	2014/03/21
	//	Created for Project :	REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependancies : None
	//
	/////////////////////////////////////////////////////////////////////////
	'''

SQL database io handler abstract class
| note: Applications should instantiate thier choice of either MysqlHandler or PostgresqlHandler classes but use the SqlHandler interface. This avoids having to install both database backend libraries when only one is needed.

"""

import traceback, logging

class SqlHandler( object ) :
	"""
	Abstract SQL handler class to allow clients to execute robust, retry on failure type SQL statements.
	"""

	def __init__( self, user, passw, hostname, port, database, timeout_statement = 60 ) :
		"""
		constructor - connects to a specific SQL database

		:param str user: username to access database with
		:param str passw: password to access database with
		:param str hostname: hostname of machine with database endpoint
		:param int port: port number of database endpoint
		:param int database: database name to connect to
		:param int timeout_statement: number of seconds to allow each SQL statement
		"""

		raise Exception( 'abstract class - instantiate a database specific class' )

	def execute_sql_query( self, query, timeout_statement = 60, timeout_overall = 180 ) :
		"""
		execute a single SQL query and return the result (if any)
		| note: use variables for all data that has escape characters, non-ascii encoding or is simply large as opposed to niavely serializing the data into an SQL query string

		:param tuple query: SQL query tuple to execute to get config JSON object. e.g. ( "SELECT var FROM mytable WHERE var = %s", ('match_value',) ). if there is no data part to the query None can be provided e.g. ( "SELECT * FROM mytable", None )
		:param int timeout_statement: number of seconds to allow each SQL statement
		:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
		:return: Python list with result row data OR empty list (no data)
		:rtype: list
		"""

		raise Exception( 'abstract class - instantiate a database specific class' )

	def execute_sql_statement( self, statement_list, timeout_statement = 60, timeout_overall = 180 ) :
		"""
		execute a set of SQL statements (insert, create etc) with no result expected
		| note: use variables for all data that has escape characters, non-ascii encoding or is simply large as opposed to niavely serializing the data into an SQL query string

		:param list statement_list: list of SQL statements in tuple form to execute in a single commit e.g. [ ( "INSERT INTO mytable VALUES(%s,%s)", ('value1','value2') ), ... ]. if there is no data part to the query None can be provided e.g. ( "INSERT INTO mytable VALUES(1)", None )
		:param int timeout_statement: number of seconds to allow each SQL statement
		:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
		"""

		raise Exception( 'abstract class - instantiate a database specific class' )

	def close( self ) :
		"""
		close an open connection
		"""
		raise Exception( 'abstract class - instantiate a database specific class' )
