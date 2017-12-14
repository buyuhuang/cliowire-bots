# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
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
	// Created By : Stuart E. Middleton
	// Created Date : 2014/03/21
	// Created for Project: REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependancies : None
	//
	/////////////////////////////////////////////////////////////////////////

Postgresql database io handler using psycopg2:
	* see http://initd.org/psycopg/docs/module.html
	* see http://initd.org/psycopg/docs/usage.html#
	* see http://www.postgresql.org/docs/9.1/static/libpq-connect.html
	* see http://www.postgresql.org/docs/current/static/runtime-config.html

note on spotting connection failures in Postgres via psycopg2:
	* connection.closed --> tells us if a connection has been closed using close(). this is useless if the network fails and connection is closed this way
	* connection.status --> tells us about a transaction status (ready, prepared etc). this lets us know if a statements are prepared but not committed but has nothing to say aboyt if the connection is alive or not
	* connection.reset() --> reset transaction not the connection
	* the only sure way to know if a connection is alive is to execute a statement and catch the exception, then reconnect using original details
"""

import os, re, sys, copy, collections, codecs, string, traceback, datetime, time, math, logging
import psycopg2, psycopg2.extras
from SqlHandler import SqlHandler

class PostgresqlHandler( SqlHandler ) :
	"""
	Postgresql handler class to allow clients to execute robust, retry on failure type SQL statements.
	"""

	def __init__( self, user, passw, hostname, port, database, timeout_statement = 60 ) :
		"""
		constructor - connects to a Postgresql database

		:param str user: username to access database with
		:param str passw: password to access database with
		:param str hostname: hostname of machine with database endpoint
		:param int port: port number of database endpoint
		:param int database: database name to connect to
		:param int timeout_statement: number of seconds to allow each SQL statement
		"""

		# compile regex to extract codes from Postgres error messages (see evaluate_sql_error() for details)
		# match format = :[?????]
		self.error_code_regex = re.compile('[\:][\[][\S]{5}[\]]')

		# disconnection phrases
		self.listDisconnectPhrases = []
		self.listDisconnectPhrases.append( 'server closed the connection unexpectedly' )
		self.listDisconnectPhrases.append( 'could not connect to server: Connection refused' )

		# http://www.postgresql.org/docs/current/static/errcodes-appendix.html#ERRCODES-TABLE
		# 03000 sql_statement_not_yet_complete
		# 08000 connection_exception
		# 08001 sqlclient_unable_to_establish_sqlconnection
		# 08003 connection_does_not_exist
		# 08006 connection_failure
		# 53300 too_many_connections
		# 57014 query cancelled (i.e. timeout)
		# 58030 io_error

		self.listAllowedCodes = []
		self.listAllowedCodes.append( '03000' )
		self.listAllowedCodes.append( '08000' )
		self.listAllowedCodes.append( '08001' )
		self.listAllowedCodes.append( '08003' )
		self.listAllowedCodes.append( '08006' )
		self.listAllowedCodes.append( '53300' )
		self.listAllowedCodes.append( '57014' )
		self.listAllowedCodes.append( '58030' )

		# init
		self.connection = None
		dateCurrent = datetime.datetime.now()
		timeMax = datetime.timedelta( seconds=timeout_statement )
		dateExpire = dateCurrent + timeMax
		bAbort = False
		strLastError = ''

		# note: self.bConnClosed is a flag to indicate that the client has closed the connection and it should NOT be reconnedted
		self.bConnClosed = False

		# remember connection details for reconnect later
		self.connDatabase = database
		self.connUser = user
		self.connPassword = passw
		self.connHost = hostname
		self.connPort = port
		self.connConnectTimeout = timeout_statement

		# note: Postgres option statement_timeout is in milliseconds
		#self.connOptions = '-c statement_timeout=' + str(timeout_statement*1000)

		# loop trying to execute the given SQL statement
		# until the expiry time
		while (bAbort == False) and (datetime.datetime.now() < dateExpire) :
			try :
				# remember the open connection
				print 'try'
				self.reconnect()
				return

			except psycopg2.Error, err :
				# check for the special case that the database connection has been terminated (e.g. Postgres reboot)
				# and needs to be restarted. this is NOT easy in psycopg2 as the standard error codes are embedded
				# within the message (!) not the err.pgcode of the psycopg2.OperationalError class
				if self.check_for_disconnect( err ) == True :
					strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					try :
						# reconnect and then try again after 1 second
						self.reconnect()
					except :
						# if reconnect fails try again after 1 second (which will fail) and come back here for another reconnect attempt
						logging.debug( 'reconnect failed (will retry in 1 second)' )
						pass
				else :
					if err.pgcode != None :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.pgerror) + ' : ' + str(err.message)
					else :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					bAbort = self.evaluate_sql_error( err )

		# failure so throw a meaningful exception to help client
		#KEM line below does not work, as strUser, etc are expected to be global variables!
		#raise Exception( 'Postgresql connection failed [' + strUser + ':' + strPass + '@' + strHost + ':' + str(nPort) + '/' + strDatabase + ']' + ' : ' + strLastError )
		raise Exception( 'Postgresql connection failed [' + user + ':' + passw + '@' + hostname + ':' + str(port) + '/' + database + ']' + ' : ' + strLastError )

	def execute_sql_query( self, query, timeout_statement = 60, timeout_overall = 180 ) :
		"""
		execute a single SQL query and return the result (if any)

		| note : use variables for all data that has escape characters, non-ascii encoding or is simply large as opposed to niavely serializing the data into an SQL query string

		:param tuple query: SQL query tuple to execute to get config JSON object. e.g. ( "SELECT var FROM mytable WHERE var = %s", ('match_value',) ). if there is no data part to the query None can be provided e.g. ( "SELECT * FROM mytable", None )
		:param int timeout_statement: number of seconds to allow each SQL statement
		:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
		:return: Python list with result row data OR empty list (no data)
		:rtype: list
		"""

		# check args
		if query == None :
			raise Exception( 'SQL query failed : null sql statement' )
		if not isinstance( query, tuple ) :
			raise Exception( 'SQL query failed : sql statement not a tuple' )
		if len(query) != 2 :
			raise Exception( 'SQL query failed : sql statement not a tuple of length 2' )
		if not isinstance( query[0], (str,unicode) ) :
			raise Exception( 'SQL query failed : sql statement query string not type str or unicode' )
		if (query[1] != None) and (not isinstance( query[1], tuple )) :
			raise Exception( 'SQL query failed : sql statement variable not tuple or None' )

		# setup timings
		dateCurrent = datetime.datetime.now()
		timeMax = datetime.timedelta( seconds=timeout_overall )
		dateExpire = dateCurrent + timeMax
		bAbort = False
		strLastError = ''

		# check connection
		if self.connection == None :
			raise Exception( 'SQL query failed : connection handle None - construction must have failed' )

		# loop trying to execute the given SQL statement
		# until the expiry time
		while (bAbort == False) and (datetime.datetime.now() < dateExpire) :
			cursor = None
			try :
				# if this connection is part-way through a transaction reset it as this
				# indicates a previous SQL statement failure
				if self.connection.status != psycopg2.extensions.STATUS_READY :
					# rollback failed transaction and get ready for a new one
					self.connection.reset()

				# SQL statements should be ASCII (convienience formatting to ASCII to avoid ASCII strings like table names read in from file as default UTF8 and becoming unicode pointlessly)
				strSQL =  query[0].encode( 'ascii' )

				cursor = self.connection.cursor()
				if query[1] != None :
					cursor.execute( strSQL, query[1] )
				else :
					cursor.execute( strSQL )

				# postgres needs a commit even for SELECT
				self.connection.commit()

				# get results
				listResult = cursor.fetchall()

				# all done
				cursor.close()

				# success
				return listResult

			except psycopg2.Error, err :
				# check for the special case that the database connection has been terminated (e.g. Postgres reboot)
				# and needs to be restarted. this is NOT easy in psycopg2 as the standard error codes are embedded
				# within the message (!) not the err.pgcode of the psycopg2.OperationalError class
				if self.check_for_disconnect( err ) == True :
					strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					try :
						# reconnect and then try again after 1 second
						self.reconnect()
					except :
						# if reconnect fails try again after 1 second (which will fail) and come back here for another reconnect attempt
						logging.debug( 'reconnect failed (will retry in 1 second)' )
						pass
				else :
					if err.pgcode != None :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.pgerror) + ' : ' + str(err.message)
					else :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					bAbort = self.evaluate_sql_error( err )

			# failure so close cursor before retry loop
			if cursor != None :
				cursor.close()

			# sleep for 1 second before retrying
			time.sleep( 1 )

		# failure
		raise Exception( 'SQL query failed (timeout retrying) : ' + strLastError + ' : ' + query[0] )

	def execute_sql_query_batch( self, query_list, timeout_statement = 60, timeout_overall = 180 ) :
		"""
		execute a batch of SQL queries and return the concatenated result (if any)

		| note : non-query statements ARE allowed here (e.g. LOCK) to allow INSERT or LOCK in the transaction before a query
		| note : use variables for all data that has escape characters, non-ascii encoding or is simply large as opposed to niavely serializing the data into an SQL query string

		:param list query_list: list of SQL query tuples to execute to get config JSON object. e.g. [ ( "SELECT var FROM mytable WHERE var = %s", ('match_value',) ), ... ]. if there is no data part to the query None can be provided e.g. [( "SELECT * FROM mytable", None ), ... ]
		:param int timeout_statement: number of seconds to allow each SQL statement
		:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
		:return: Python list with result row data OR empty list (no data)
		:rtype: list
		"""

		# check args
		if (query_list == None) or len(query_list) == 0 :
			raise Exception( 'SQL query failed : null or empty sql statement list' )

		# setup timings
		dateCurrent = datetime.datetime.now()
		timeMax = datetime.timedelta( seconds=timeout_overall )
		dateExpire = dateCurrent + timeMax
		bAbort = False
		strLastError = ''

		# check connection
		if self.connection == None :
			raise Exception( 'SQL query failed : connection handle None - construction must have failed' )

		# loop trying to execute the given SQL statement
		# until the expiry time
		nStatementIndex = 0
		while (bAbort == False) and (datetime.datetime.now() < dateExpire) :
			cursor = None
			listResult = []
			try :
				# if this connection is part-way through a transaction reset it as this
				# indicates a previous SQL statement failure
				if self.connection.status != psycopg2.extensions.STATUS_READY :
					# rollback failed transaction and get ready for a new one
					self.connection.reset()

				cursor = self.connection.cursor()

				# note: psycopg2 will open a transaction on the first command
				for tupleStatement in query_list :

					if not isinstance( tupleStatement, tuple ) :
						raise Exception( 'SQL query failed : sql statement not a tuple' )
					if len(tupleStatement) != 2 :
						raise Exception( 'SQL query failed : sql statement not a tuple of length 2' )
					if not isinstance( tupleStatement[0], (str,unicode) ) :
						raise Exception( 'SQL query failed : sql statement query string not type str or unicode' )
					if (tupleStatement[1] != None) and (not isinstance( tupleStatement[1], tuple )) :
						raise Exception( 'SQL query failed : sql statement variable not tuple or None' )

					# SQL statements should be ASCII (convienience formatting to ASCII to avoid ASCII strings like table names read in from file as default UTF8 and becoming unicode pointlessly)
					strSQL =  tupleStatement[0].encode( 'ascii' )

					if tupleStatement[1] != None :
						cursor.execute( strSQL, tupleStatement[1] )
					else :
						cursor.execute( strSQL )

					# get results (extend the aggregated result list)
					# note: if there are no results this causes an error (!?!) and it looks like the only way
					#       to handle this is to catch the psycopg2.ProgrammingError exception
					try :
						listResult.extend( cursor.fetchall() )
					except psycopg2.ProgrammingError :
						# no results (e.g. if its a LOCK statement of something)
						pass

				# commit any changes that may have been made by the query
				self.connection.commit()

				# all done
				cursor.close()

				# success
				return listResult

			except psycopg2.Error, err :
				# check for the special case that the database connection has been terminated (e.g. Postgres reboot)
				# and needs to be restarted. this is NOT easy in psycopg2 as the standard error codes are embedded
				# within the message (!) not the err.pgcode of the psycopg2.OperationalError class
				if self.check_for_disconnect( err ) == True :
					strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					try :
						# reconnect and then try again after 1 second
						self.reconnect()
					except :
						# if reconnect fails try again after 1 second (which will fail) and come back here for another reconnect attempt
						logging.debug( 'reconnect failed (will retry in 1 second)' )
						pass
				else :
					if err.pgcode != None :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.pgerror) + ' : ' + str(err.message)
					else :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					bAbort = self.evaluate_sql_error( err )

			# failure so close cursor before retry loop
			if cursor != None :
				cursor.close()

			# sleep for 1 second before retrying
			time.sleep( 1 )

		# failure
		raise Exception( 'SQL query failed (timeout retrying) : ' + strLastError + ' : ' + tupleStatement[0] )

	def execute_sql_statement( self, statement_list, timeout_statement = 60, timeout_overall = 180 ) :
		"""
		execute a set of SQL statements (insert, create etc) with no result expected

		| note : use variables for all data that has escape characters, non-ascii encoding or is simply large as opposed to niavely serializing the data into an SQL query string

		:param list statement_list: list of SQL statements in tuple form to execute in a single commit e.g. [ ( "INSERT INTO mytable VALUES(%s,%s)", ('value1','value2') ), ... ]. if there is no data part to the query None can be provided e.g. ( "INSERT INTO mytable VALUES(1)", None )
		:param int timeout_statement: number of seconds to allow each SQL statement
		:param int timeout_overall: number of seconds total to allow each SQL statement (including retries)
		"""

		# check args
		if statement_list == None :
			raise Exception( 'SQL statement failed : null sql statement list' )
		if not isinstance( statement_list, list ) :
			raise Exception( 'SQL statement failed : sql statement list not a list' )

		# check connection
		if self.connection == None :
			raise Exception( 'SQL query failed : connection handle None - construction must have failed' )

		nStatementIndex = 0

		# setup timings
		dateCurrent = datetime.datetime.now()
		timeMax = datetime.timedelta( seconds=timeout_overall )
		dateExpire = dateCurrent + timeMax
		bAbort = False
		strLastError = ''

		# get a cursor to execute the statement set
		while (bAbort == False) and (datetime.datetime.now() < dateExpire) :
			cursor = None
			try :
				# if this connection is part-way through a transaction reset it as this
				# indicates a previous SQL statement failure
				if self.connection.status != psycopg2.extensions.STATUS_READY :
					# rollback failed transaction and get ready for a new one
					self.connection.reset()

				# get a cursor
				cursor = self.connection.cursor()

				# loop trying to execute the given SQL statement adding them to SQL transaction
				for nStatementIndex in range(len(statement_list)) :

					if not isinstance( statement_list[nStatementIndex], tuple ) :
						raise Exception( 'SQL statement @ index ' + str(nStatementIndex) + ' not a tuple' )
					if not isinstance( statement_list[nStatementIndex][0], (str,unicode) ) :
						raise Exception( 'SQL statement[0] @ index ' + str(nStatementIndex) + ' not a str or unicode' )
					if (statement_list[nStatementIndex][1] != None) and (not isinstance( statement_list[nStatementIndex][1], tuple )) :
						raise Exception( 'SQL statement[1] @ index ' + str(nStatementIndex) + ' not tuple or None' )

					# SQL statements should be ASCII (convienience formatting to ASCII to avoid ASCII strings like table names read in from file as default UTF8 and becoming unicode pointlessly)
					strSQL = statement_list[nStatementIndex][0].encode( 'ascii' )

					if statement_list[nStatementIndex][1] != None :
						# [ sql_statement_with_format, tuple_data_objects ]
						cursor.execute( strSQL, statement_list[nStatementIndex][1] )
					else :
						# just_sql_statement
						cursor.execute( strSQL )

				# commit statements and close cursor
				self.connection.commit()
				cursor.close()

				# success
				return

			except psycopg2.Error, err :
				# check for the special case that the database connection has been terminated (e.g. Postgres reboot)
				# and needs to be restarted. this is NOT easy in psycopg2 as the standard error codes are embedded
				# within the message (!) not the err.pgcode of the psycopg2.OperationalError class
				if self.check_for_disconnect( err ) == True :
					strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					try :
						# reconnect and then try again after 1 second
						self.reconnect()
					except :
						# if reconnect fails try again after 1 second (which will fail) and come back here for another reconnect attempt
						logging.debug( 'reconnect failed (will retry in 1 second)' )
						pass
				else :
					if err.pgcode != None :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.pgerror) + ' : ' + str(err.message)
					else :
						strLastError = '[' + str(err.pgcode) + '] ' + str(err.message)
					bAbort = self.evaluate_sql_error( err )

			# failure so close cursor before retry loop
			if cursor != None :
				cursor.close()

			# sleep for 1 second before retrying
			time.sleep( 1 )

		# timeout
		raise Exception( 'SQL statement failed (timeout retrying) :' + strLastError )

	def evaluate_sql_error( self, err ) :
		"""
		evaluate an sql error to see if we need to abort

		:param psycopg2.Error err: SQL exception object
		:return: True if the SQL query or statement can be retried (e.g. network connection error that might go away), or False if it should be aborted (e.g. SQL syntax error)
		:rtype: bool
		"""

		# get possible error codes from the message text as postgres python libs do NOT set err.pgcode
		# as often as they should (!)
		strExtractedCode = None

		# check for OperationalError as this is thrown on database connection failure so a retry is worthwhile
		listCodes = self.error_code_regex.findall( str( err.message ) )
		if len(listCodes) > 0 :
			strExtractedCode = listCodes[0][2:7]
			logging.debug('extracted SQL error code = {' + str(strExtractedCode) + '}' )

		# check pgcode first (might be None)
		if (err.pgcode) != None and (err.pgcode in self.listAllowedCodes) :
			# allow a retry
			logging.debug( 'SQL statement failed (will retry) : [' + str(err.pgcode) + '] ' + str(err.pgerror) + ' : ' + str(err.message) )
			return False
		else :
			if strExtractedCode  != None :
				if strExtractedCode in self.listAllowedCodes :
					# allow a retry
					logging.debug( 'SQL statement failed (will retry) : [' + strExtractedCode + '] ' + str(err.message) )
					return False

			# abort as we have an unknown error
			return True

	def check_for_disconnect( self, err ) :
		"""
		special connection failure parsing

		:param psycopg2.Error err: SQL exception object
		:return: True if the error indicates we are disconnected
		:rtype: bool
		"""

		# check for disconnection message phrases
		if isinstance( err, psycopg2.OperationalError ) :
			strMessage = str( err.message )
			for nTestIndex in range(len(self.listDisconnectPhrases)) :
				if strMessage.count( self.listDisconnectPhrases[nTestIndex] ) > 0 :
					return True
		return False

	def reconnect( self ) :
		"""
		reconnect using previously cached connection params

		| note : UTF8 client encoding is set for all connections
		"""

		if self.bConnClosed == False :
			print 'itsfalsemymain'
			# establish a connection
			#self.connection = psycopg2.connect( database=self.connDatabase, user=self.connUser, password=self.connPassword, host=self.connHost, port=self.connPort, connect_timeout=self.connConnectTimeout ,options=self.connOptions )
			self.connection = psycopg2.connect( database=self.connDatabase, user=self.connUser, password=self.connPassword, host=self.connHost, port=self.connPort, connect_timeout=self.connConnectTimeout )
			self.connection.set_client_encoding( 'utf8' )

			# register hstore support (turn it on for all cursors globally)
			# this allows python dict to be mapped to hstore
			psycopg2.extras.register_hstore( conn_or_curs = self.connection, globally = True, unicode=True, oid=None, array_oid=None )

	def close( self ) :
		"""
		close connecton and flag it as closed to prevent restarts

		| note : once flagged closed the connection will not be restarted using reconnect()
		"""
		self.bConnClosed = True
		if self.connection != None :
			self.connection.close()
