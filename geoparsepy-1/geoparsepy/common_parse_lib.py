# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
..
	/////////////////////////////////////////////////////////////////////////
	//
	// (c) Copyright University of Southampton IT Innovation, 2015
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
	// Created Date : 2015/11/10
	// Created for Project : REVEAL
	//
	/////////////////////////////////////////////////////////////////////////
	//
	// Dependancies : Source code derived from ITINNO copyright code in TRIDEC
	//
	/////////////////////////////////////////////////////////////////////////
	'''

common parse lib supporting tokenization, POS tagging and sentence management

| POS tagger information
|  http://www-nlp.stanford.edu/links/statnlp.html#Taggers

| Standard POS tagger
|  http://nlp.stanford.edu/software/tagger.shtml
|  license = GPL v2
|  NLTK support for python via remote Java exec (i.e. SLOW)
|  English, Arabic, Chinese, French, German

| TreeTagger
|  http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/
|  http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/Tagger-Licence
|  https://github.com/miotto/treetagger-python
|  https://courses.washington.edu/hypertxt/csar-v02/penntable.html
|  license = BSD style free for research/eval/teaching but NOT commercial (need to buy it for that)
|  NLTK support for python (i.e. FAST)
|  German, English, French, Italian, Dutch, Spanish, Bulgarian, Russian, Portuguese, Galician, Chinese, Swahili, Slovak, Latin, Estonian, Polish and old French

| Language codes
|  http://tools.ietf.org/html/bcp47

"""

import os, re, sys, copy, collections, codecs, string, ConfigParser, traceback, datetime, time, math, subprocess, Queue, threading
import nltk, nltk.corpus
from nltk.util import ngrams

# url and namespace entities regex
# captures: sem@it-innovation.ac.uk http://www.co.uk/blah?=stuff&more+stuff www.co.uk http://user:pass@www.co.uk
# ignores: S.E. Middleton, $5.13, #hashtag, @user_name
# ignores \u2026 which is ... unicode character used by twitter to truncate tweets (which might truncate a URI)
# matches <token>.<token>.<token>... as many tokens as needed as long as there are 2 .'s
# where tokens are at least 2 char long (to avoid matching sets of legitimate initials 'a.b. jones')
#namespace_entity_extract_regex = re.compile(ur'[\w\@\-\\\/\:\?\=\&\+]{2,}[\.][\w\@\-\\\/\:\?\=\&\+]{2,}[\.](?:[\w\@\-\\\/\:\?\=\&\+]{2,}[\.])*[\w\@\-\\\/\:\?\=\&\+]{2,}', re.IGNORECASE | re.UNICODE)
#url_entity_extract_regex = re.compile(ur'[\w]{3,}\:\/\/[^ \t\n\r\f\v\u2026]*', re.IGNORECASE | re.UNICODE)

namespace_entity_extract = ur'\A.*?(?P<NAMESPACE>([a-zA-Z0-9_@\-]){2,}[.](([a-zA-Z0-9_@\-]){1,}[.]){1,5}([a-zA-Z0-9_@\-]){1,})'
url_entity_extract = ur'\A.*?(?P<URI>[\w]{3,}\:\/\/[^ \t\n\r\f\v\u2026]*)'

namespace_entity_extract_regex = re.compile( namespace_entity_extract, re.IGNORECASE | re.UNICODE | re.DOTALL)
url_entity_extract_regex = re.compile( url_entity_extract, re.IGNORECASE | re.UNICODE | re.DOTALL)

# currency and number regex
# e.g. 56, 56.76, $54.23, $54 but NOT 52.com
numeric_extract_regex = re.compile(ur'\A\D?\d+\.?\d*\Z', re.IGNORECASE | re.UNICODE)

def get_common_config( lang_codes = [], logger = None, corpus_dir = None,  stanford_base_dir = None, treetagger_base_dir = None, **kwargs ) :
	"""
	return a common config object for this specific set of languages. the config object contains an instantiated NLTK stemmer, tokenizer and settings tailored for the chosen language set. all available language specific corpus will be read into memory, such as stoplists. 
	common config settings are below:
		* *stemmer* = NLTK stemmer, default is to do no stemming *stemmer = nltk.stem.RegexpStemmer('', 100000)*
		* *t_word* = NLTK word tokenizer for chosen language. default is nltk.tokenize.treebank.TreebankWordTokenizer()
		* *t_sent* = NLTK sent tokenizer for chosen language. default is nltk.tokenize.treebank.PunktSentenceTokenizer()
		* *regex_namespace* = regre.RegexObject, regex to match namespaces e.g. www.bbc.co.uk
		* *regex_url* = regre.RegexObject, regex to match URIs e.g. http://www.bbc.co.uk
		* *regex_numeric_extract* = regre.RegexObject, regex to match numeric strings e.g. 56, 56.76, $54.23, $54 but NOT 52.com
		* *lang_codes* = list, list of ISO 639-1 2 character language codes e.g. ['en','fr']
		* *stoplist* = list, aggregated set of stopwords for languages selected
		* *logger* = logging.Logger, logger object
		* *whitespace* = str, string containing whitespace characters that will be removed prior to tokenization. default is "\\\\u201a\\\\u201b\\\\u201c\\\\u201d
		* *punctuation* = str, string containing punctuation characters that will be forced into thier own token. default is ,;\\\\/:+-#~&*=!?
		* *corpus_dir* = str, directory where common_parse_lib language specific corpus files are located
		* *max_gram* = int, maximum size of n-grams for use in create_ngram_tokens() function. default if 4
		* *first_names* = set, aggragated language specific set of first names
		* *lower_tokens* = bool, if True text will be converted to lower() before tokenization. default is False
		* *sent_token_seps* = list, unicode sentence termination tokens. default is [\\\\n, \\\\r\\\\n, \\\\f, \\\\u2026]
		* *stanford_base_dir* = base dir for stanfard POS tagger
		* *treetagger_base_dir* = base dir for TreeTagger
		* *lang_pos_mapping* = dict, set of langauge to PSO tagger mappings. e.g. { 'en' : 'stanford', 'ru' : 'treetagger' }
		* *pos_sep* = tuple, POS separator character and a safe replacement. the default POS separator char is '/' and usually POS tagged sentences become 'term/POS term/POS ...'. when tagging a token containing this character e.g. 'one/two' the POS separator character will be replaced prior to serialization to avoid an ambiguous output.
		* *token_preservation_regex* = dict of key name for regre.RegexObject objects to identify tokens that should be preserved and a unique POS token name (e.g. { 'regex_namespace' : 'NAMESPACE', 'regex_url' : 'URI' } ). POS token name must be unique for chosen POS tagger and safe for POS serialization without characters like ' ' or '/'. this dict argument allows additional POS tokens to be added in the future without the need to change the common_parse_lib code.

	| note: a config object approach is used, as opposed to a global variable, to allow common_parse_lib functions to work in a multi-threaded environment

	:param list lang_codes: list of ISO 639-1 2 character language codes (e.g. ['en','fr'])
	:param logging.Logger logger: logger object
	:param list corpus_dir: directory where common_parse_lib language specific corpus files are located. if None the package installation dir will be used. Default is None
	:param list stanford_base_dir: base dir for stanfard POS tagger (None if not installed)
	:param list treetagger_base_dir: base dir for TreeTagger (None if not installed)
	:param kwargs: variable argument to override any default config values

	:return: configuration settings to be used by all common_parse_lib functions
	:rtype: dict
	"""

	if corpus_dir == None :
		if pkg_resources.resource_exists( __name__, 'common_parse_lib.py' ) :
			# if run as an installed python lib
			strCorpusDir = os.path.dirname( pkg_resources.resource_filename( __name__, 'common_parse_lib.py' ) )
		else :
			# if run as a standalone file in a dir
			strCorpusDir = os.path.dirname( __file__ )
	else :
		strCorpusDir = corpus_dir

	# setup default values
	dictCommonConfig = {
		'stemmer' : nltk.stem.RegexpStemmer('', 100000),
		't_word' : nltk.tokenize.treebank.TreebankWordTokenizer(),
		't_sent' : nltk.tokenize.punkt.PunktSentenceTokenizer(),
		'regex_namespace' : namespace_entity_extract_regex,
		'regex_url' : url_entity_extract_regex,
		'regex_numeric_extract' : numeric_extract_regex,
		'lang_codes' : lang_codes,
		'lang_codes_ISO639_2' : [],
		'stoplist' : [],
		'logger' : logger,
		'whitespace' : u'"\u201a\u201b\u201c\u201d',
		'punctuation' : """,;\/:+-#~&*=!?""",
		'corpus_dir' : strCorpusDir,
		'max_gram' : 4,
		'first_names' : set([]),
		'lower_tokens' : False,
		'sent_token_seps' : ['\n','\r\n', '\f', u'\u2026'],
		'stanford_base_dir' : stanford_base_dir,
		'treetagger_base_dir' : treetagger_base_dir,
		'lang_pos_mapping' : {},
		'pos_sep' : ('/','|'),
		'token_preservation_regex' : [ ('regex_url','URI'), ('regex_namespace','NAMESPACE') ]
		}

	#
	# override any defaults with provided args
	#
	for k,v in kwargs.iteritems():
		dictCommonConfig[k] = v

	# use None not '' for POS tagger filenames
	if dictCommonConfig['stanford_base_dir'] == '' :
		dictCommonConfig['stanford_base_dir'] = None
	if dictCommonConfig['treetagger_base_dir'] == '' :
		dictCommonConfig['treetagger_base_dir'] = None

	# validate special POS tag dict before its used
	listReplacementRegexName = dictCommonConfig['token_preservation_regex']
	for (strRegexName,strPOSTokenName) in listReplacementRegexName :
		if not strRegexName in dictCommonConfig.keys() :
			raise Exception( 'regex pattern ' + strRegexName + ' not in common config but is in pos_replacement_regex' )
		if ' ' in strPOSTokenName :
			raise Exception( 'regex pattern ' + strRegexName + ' has an invalid POS tag (spaces)' )
		if '/' in strPOSTokenName :
			raise Exception( 'regex pattern ' + strRegexName + ' has an invalid POS tag (forward slash)' )

	"""
	rePOSPattern = re.compile( ur'[^' + dictCommonConfig['pos_sep'][0] + ']*' +  dictCommonConfig['pos_sep'][0] + '\S*' , re.UNICODE )
	dictCommonConfig['regex_pos_parse'] = rePOSPattern
	"""


	# POS mapping example
	# lang_pos_mapping = { 'en' : 'stanford', 'ru' : 'treetagger' }
	# pos_sep = ('/','|') ==> sep char and its replacement
	#   ... so that TreeTagger POS tag 'IN/that' becomes 'IN|that' which can then be serialized OK using / separator char to 'that/IN_that'
	#   ... also will change tokens for same reason

	# sent_token_seps = ['\n','\r\n', '\f', u'\u2026']
	# characters that always denote a new sentence like a newline. do NOT include period . in this as you can have numbers like 8.34 

	# note: NLTK3 PunktSentenceTokenizer() leave periods on words (e.g. some sentence.)
	#       TreebankWordTokenizer treats # as a token in itself (e.g. # tag) as well as %5.67 (e.g. # 5.67) and 

	#
	# create a stoplist based on the languages used
	# - NLTK language stoplists
	# - NLTK names (en)
	#
	listStoplistFinal = []

	# stopwords from NLTK based on language
	for strCode in lang_codes :
		# note: NLTK stopwords are stored in language named files so do a quick convert from lang code to lang name
		strLanguage = None
		strISO639 = None
		if strCode == 'da' :
			strLanguage = 'danish'
			strISO639 = 'dan'
		elif strCode == 'en' :
			strLanguage = 'english'
			strISO639 = 'eng'
		elif strCode == 'fi' :
			strLanguage = 'finnish'
			strISO639 = 'fin'
		elif strCode == 'fr' :
			strLanguage = 'french'
			strISO639 = 'fra'
		elif strCode == 'de' :
			strLanguage = 'german'
			strISO639 = 'deu'
		elif strCode == 'hu' :
			strLanguage = 'hungarian'
			strISO639 = 'hun'
		elif strCode == 'it' :
			strLanguage = 'italian'
			strISO639 = 'ita'
		elif strCode == 'no' :
			strLanguage = 'norwegian'
			strISO639 = 'nor'
		elif strCode == 'pt' :
			strLanguage = 'portuguese'
			strISO639 = 'por'
		elif strCode == 'ru' :
			strLanguage = 'russian'
			strISO639 = 'rus'
		elif strCode == 'es' :
			strLanguage = 'spanish'
			strISO639 = 'spa'
		elif strCode == 'se' :
			strLanguage = 'swedish'
			strISO639 = 'swe'
		elif strCode == 'tr' :
			strLanguage = 'turkish'
			strISO639 = 'tur'

		if strISO639 != None :
			dictCommonConfig['lang_codes_ISO639_2'].append( strISO639 )

		if strLanguage != None :
			listStoplist = nltk.corpus.stopwords.words( strLanguage )
			for strTerm in listStoplist :
				# convert NLTK corpus term (latin encoding) to (utf-8 encoding)
				# note: NLTK 3 is all unicode so this is just for legacy code
				if isinstance( strTerm,str ) :
					strText = unicode( strTerm,'utf-8' )
				else :
					strText = strTerm

				# clean and stem stoplist words as this is what will happen to all tokens
				# we match against the stoplist
				# note: if cleaned and stemmed word disappears then ignore it!
				# note: clean_text does NOT use the stoplist so its OK to call it here
				strTextClean = clean_text( strText, dictCommonConfig )
				strStem = dictCommonConfig['stemmer'].stem( strTextClean )
				if len(strStem) > 0 :
					if not strStem in listStoplistFinal :
						listStoplistFinal.append( strStem )

	# common names (as locations often match common names such as Chelsea)
	if 'en' in lang_codes :
		listNames = nltk.corpus.names.words()
		for strName in listNames :
			# convert NLTK corpus term (latin encoding) to (utf-8 encoding)
			# note: NLTK 3 is all unicode so this is just for legacy code
			if isinstance( strName,str ) :
				strText = unicode( strName,'utf-8' )
			else :
				strText = strName

			# add name to name list
			strTextClean = clean_text( strText, dictCommonConfig )
			dictCommonConfig['first_names'].add( strTextClean )

	dictCommonConfig['stoplist'] = listStoplistFinal

	# specify the lang to POS tagger mapping making sure we do not override any settings provided explicitly by caller
	# note: default POS tagger is NLTK treebank which is not very good for anything but English !!
	dictPOS = {}

	if dictCommonConfig['treetagger_base_dir'] != None :
		# better choice is the multi-lingual treetagger
		# note: more countries are needed as lots speak spanish, english etc.
		if not 'bg' in dictPOS :
			dictPOS['bg'] = 'treetagger'
		if not 'nl' in dictPOS :
			dictPOS['nl'] = 'treetagger'
		if not 'en' in dictPOS :
			dictPOS['en'] = 'treetagger'
		if not 'et' in dictPOS :
			dictPOS['et'] = 'treetagger'
		if not 'fi' in dictPOS :
			dictPOS['fi'] = 'treetagger'
		if not 'fr' in dictPOS :
			dictPOS['fr'] = 'treetagger'
		if not 'de' in dictPOS :
			dictPOS['de'] = 'treetagger'
		if not 'it' in dictPOS :
			dictPOS['it'] = 'treetagger'
		if not 'pl' in dictPOS :
			dictPOS['pl'] = 'treetagger'
		if not 'ru' in dictPOS :
			dictPOS['ru'] = 'treetagger'
		if not 'sk' in dictPOS :
			dictPOS['sk'] = 'treetagger'
		if not 'es' in dictPOS :
			dictPOS['es'] = 'treetagger'

	if dictCommonConfig['stanford_base_dir'] != None :
		# stanford is better choice than treetagger where both can do a language
		# note: more countries are needed as lots speak arabic etc.
		if not 'ar' in dictPOS :
			dictPOS['ar'] = 'stanford'
		if not 'en' in dictPOS :
			dictPOS['en'] = 'stanford'
		if not 'zh' in dictPOS :
			dictPOS['zh'] = 'stanford'
		if not 'fr' in dictPOS :
			dictPOS['fr'] = 'stanford'
		if not 'es' in dictPOS :
			dictPOS['es'] = 'stanford'
		if not 'de' in dictPOS :
			dictPOS['de'] = 'stanford'

	dictCommonConfig['lang_pos_mapping'] = dictPOS

	# all done
	return dictCommonConfig

def ngram_tokenize_microblog_text( text, dict_common_config ) :
	"""
	tokenize a microblog entry (e.g. tweet) into all possible combinations of N-gram phrases keeping the linear sentence structure intact
	text will be cleaned and tokenized. URL's and namespaces are explicitly preserved as single tokens. a set of all possible n-gram tokens is returned up to max-gram

	:param unicode text: UTF-8 text to tokenize
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:return: list of n-gram token sets e.g. [ [('one',),('two',),('three',),('four',)], [('one','two'), ('two','three'), ('three','four')], [('one','two','three'),('two','three','four')] ]
	:rtype: list
	"""

	# check args without defaults
	if (not isinstance( text, str )) and (not isinstance( text, unicode )) :
		raise Exception( 'invalid text' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )


	# tokenize text into 1g tokens
	listTokensAll = unigram_tokenize_microblog_text( text, dict_common_config )

	# create ngram token set from this
	listTokenAllg = create_ngram_tokens( listTokensAll, dict_common_config['max_gram'], dict_common_config['sent_token_seps'] )

	# all done
	return listTokenAllg

def unigram_tokenize_microblog_text( text, dict_common_config ) :
	"""
	tokenize a microblog entry (e.g. tweet) into unigram tokens
	text will be cleaned and tokenized. URL's and namespaces are explicitly preserved as single tokens.

	:param unicode text: UTF-8 text to tokenize
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:return: list of unigram tokens e.g. [ 'one','two','three' ]
	:rtype: list
	"""

	# check args without defaults
	if (not isinstance( text, str )) and (not isinstance( text, unicode )) :
		raise Exception( 'invalid text' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	# 
	# tokenize text
	#
	# strategy for handling tweet text and making 1..6g tokens for subsequent matching
	# (1) preserve URLs and NS with placeholder tokens
	# (2) clean whitespace from text 
	# (3) remove stop list words
	# (4) stem text
	# (5) tokenize <text> and create all 1..6g tokens
	# (6) optionally add a sent_token separator at the end of every parsed token set
	# (7) restore URLs and NS
	#

	if dict_common_config['t_word'] == None :
		raise Exception( 'word tokenizer None' )
	listSentToken = dict_common_config['sent_token_seps']

	# find any URL, NS etc entities and replace them with a __URL1__ token
	# so we can treat them as single tokens later on
	# e.g.
	# find any namespace entities like emails and web address fragments and replace them with a space
	# this avoids joe@co.nz ==> joe@co nz and then matching new zealand
	# and www.news.nz (without the http protocol)
	# note: execute regex in strict list order so we can add most permissive patterns last to avoid overmatching
	dictReplacementTokens = {}

	listReplacementRegexName = dict_common_config['token_preservation_regex']
	nIndex = 0
	for (strRegexName,strPOSTokenName) in listReplacementRegexName :
		rePattern = dict_common_config[ strRegexName ]

		bMore = True
		while bMore == True :
			matchInstance = rePattern.match( text )
			if matchInstance != None :
				if strPOSTokenName not in matchInstance.groupdict().keys() :
					raise Exception( 'regex pattern ' + strRegexName + ' does not create named group ' + strPOSTokenName )

				strEntity = matchInstance.groupdict()[strPOSTokenName]
				strPlaceholder = '__' + strPOSTokenName + str(nIndex+1) + '__'
				nIndex = nIndex + 1

				# replace 1st match with the token (so it will not match again and be kept whole in tokenization)
				text = text.replace( strEntity,strPlaceholder, 1 )

				# remember each tokens true value so it can be replaced later
				dictReplacementTokens[strPlaceholder] = strEntity
			else :
				bMore = False

	# clean the text field
	strTextClean = clean_text( text, dict_common_config )

	# tokenize - sentences first then words
	# note: Treebank word tokenizer will produce tokens like 'Road.' so if multiple sentences exist so use sentence tokenization first
	# listTokensAll = 1g tokens optionally with a sent separator token
	listTokensAll = []
	if dict_common_config['t_sent'] != None :
		listSentText = []
		if len(listSentToken) > 0 :
			# convert all sep chars to 1st sep char
			if len(listSentToken) > 1 :
				for strTokenSep in listSentToken[1:] :
					strTextClean = strTextClean.replace( strTokenSep, listSentToken[0] )

			# split using 1st sep char
			listSentText = strTextClean.split( listSentToken[0] )
		else :
			listSentText = [strTextClean]
 
		# use sent tokenizer on sent broken down by newline
		# to get sent broken down by . etc
		listSentences = []
		for strSentText in listSentText :
			listSentences.extend( dict_common_config['t_sent'].tokenize( strSentText ) )
	else :
		listSentences = [ strTextClean ]

	# tokenize words in each sent
	for strSentence in listSentences :
		listTokens = tokenize_sentence( strSentence, dict_common_config )
		listTokensAll.extend( listTokens )

		# note: assumption is that sent token is removed by chosen sent tokenizer so we add it back in
		if len(listSentToken) > 0 :
			listTokensAll.append( listSentToken[0] )

	# restore replacement tokens (e.g. URI's and NS) to thier original values preserving them from bring broken up via tokenization
	for nIndex in range(len(listTokensAll)) :
		if listTokensAll[nIndex] in dictReplacementTokens.keys() :
			listTokensAll[nIndex] = dictReplacementTokens[ listTokensAll[nIndex] ]

	# all done
	return listTokensAll


def tokenize_sentence( sent, dict_common_config ) :
	"""
	tokenizes a single sentence into stemmed tokens.
	if nltk.tokenize.treebank.TreebankWordTokenizer is used then tokens will be corrected for embedded punctuation within tokens and embedded periods within tokens unless they are numeric values

	:param unicode sent: UTF-8 text sentence to tokenize
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:return: list of unigram tokens e.g. [ 'one','two','three' ]
	:rtype: list
	"""

	# check args without defaults
	if (not isinstance( sent, str )) and (not isinstance( sent, unicode )) :
		raise Exception( 'invalid sent' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	if dict_common_config['t_word'] == None :
		raise Exception( 'word tokenizer None' )

	strCharPunctuation = dict_common_config['punctuation']
	regex_numeric = dict_common_config['regex_numeric_extract']

	# tokenize using the chosen tokenizer into 1-gram tokens
	listTokens = dict_common_config['t_word'].tokenize( sent )

	# clean whitespace from start and end of each token
	for nIndex in range(len(listTokens)) :
		listTokens[nIndex] = listTokens[nIndex].strip()

	# the Punkt sentence tokenizer will work for 'london.oxford' but fail for multiple periods
	# words like 'london..oxford', the odd 'dott.' and ':'
	# explicitly check for this weakness to avoid missing microblog style lists of places

	# note: NLTK3 PunktWordTokenizer() leave periods on words (e.g. some sentence.) and treats # as a token in itself (e.g. # tag)
	if isinstance( dict_common_config['t_word'],nltk.tokenize.treebank.TreebankWordTokenizer ) :

		nIndex = 0
		while nIndex < len(listTokens) :
			# Punkt internal punctuation cannot handle missing spaces with punctuation
			# e.g. Punkt will parse 'one ,two' but not 'one,two'
			# and will leave punctuation attached
			# e.g. Punkt will parse 'one, two' ==> 'one,', 'two'
			# therefore expand punctuation by adding spaces then insert the new tokens
			strTokenExpanded = listTokens[nIndex]
			if len(strTokenExpanded) > 1 :
				for cPunctuation in strCharPunctuation :
					strTokenExpanded = strTokenExpanded.replace( cPunctuation, ' ' + cPunctuation + ' ' )
				listTokenNew = strTokenExpanded.strip().split(' ')
				if len(listTokenNew) > 1 :
					# insert N tokens just after current token (insert in reverse order)
					for nNew in range(len(listTokenNew)-1,-1,-1) :
						listTokens.insert( nIndex+1, listTokenNew[nNew].strip() )

					# delete current token (keep index the same so it now points to start of added token set
					del listTokens[nIndex]
				else :
					listTokens[nIndex] = listTokenNew[0]

			# handle periods . differently as they might be part of a number OR a separator
			# so if it contains a number leave token alone
			# $1.45 => leave it alone as its a number [$1.45]
			# 'some..stuff' => tokenize using . to make [some,.,.,stuff]
			strToken = listTokens[nIndex]
			if regex_numeric.match( strToken ) == None :
				bNum = False
			else :
				bNum = True

			if bNum == False :
				# split text using . as its not a number
				listTokenNew = strToken.strip().split('.')

				# if we have a split then expand the token set
				# otherwise leave it alone completely (keep tokens like '.')
				if len(listTokenNew) > 1 :
					listTokens[nIndex] = listTokenNew[0]
					for nNew in range(1,len(listTokenNew)) :
						# insert will add token BEFORE index so we make sure its 1 after current pos
						# also we need to increment the index anyway as the list has just expanded

						# add period
						nIndex = nIndex + 1
						listTokens.insert( nIndex, '.' )

						# add token (if its not '' which it might be if period at end e.g. 'hello.' ==> ['hello',''])
						strTokenToAdd = listTokenNew[nNew].strip()
						if len(strTokenToAdd) > 0 :
							nIndex = nIndex + 1
							listTokens.insert( nIndex, strTokenToAdd )
				else :
					listTokens[nIndex] = listTokenNew[0]

			# next token
			nIndex = nIndex + 1

	# stem the resulting tokens
	if dict_common_config['stemmer'] != None :
		stemmer = dict_common_config['stemmer']
		for nIndex in range(len(listTokens)) :
			if len( listTokens[nIndex] ) > 1 :
				strStem = stemmer.stem( listTokens[nIndex] )
				listTokens[nIndex] = strStem.strip()

	# remove all empty string entries from list
	while listTokens.count( '' ) > 0 :
		listTokens.remove( '' )

	return listTokens

def create_ngram_tokens( list_tokens, max_gram = 4, sent_temination_tokens = None ) :
	"""
	compile n-gram phrase sets keeping the linear sequence of tokens intact up to a maximum gram size
	the optional sent_temination_tokens prevents n-gram tokens spanning sent terminator tokens (e.g. newlines)

	:param list list_tokens: unigram token list
	:param int max_gram: max gram size to create
	:param list sent_temination_tokens: list of sent terminator tokens

	:return: set of n-gram tokens e.g. [ [('one',),('two',),('three',),('four',)], [('one','two'), ('two','three'), ('three','four')], [('one','two','three'),('two','three','four')] ]
	:rtype: list
	"""

	# check args without defaults
	if not isinstance( list_tokens, list ) :
		raise Exception( 'invalid list_tokens' )

	# get a set of sentence end indexes (i.e. index of any sent tokens)
	listIndexSent = []
	if sent_temination_tokens != None :
		for nIndexToken in range(len(list_tokens)) :
			if list_tokens[nIndexToken] in sent_temination_tokens :
				listIndexSent.append( nIndexToken )

	# ensure 1 token past end is a sentence end index
	listIndexSent.append( len(list_tokens) )

	# process each sentence and aggregate the results
	listTokensAllg = []
	for nGram in range( max_gram ) :
		listGramTokens = []

		# get 1g tokens for each sent and calc ngrams for them
		nLastSentIndex = -1
		for nSentIndex in listIndexSent :
			listTokens1gSent = list_tokens[ nLastSentIndex + 1 : nSentIndex ]
			nLastSentIndex = nSentIndex

			# calc ngram tokens
			# note: this is nltk.util.ngrams BUT we cannot import nltk.utils (not a package in itself)
			listGramTokens.extend( list( ngrams( listTokens1gSent, nGram + 1 ) ) )

		# add all ngram tokens for all sents to a single list (keeping the strict sequential nature)
		listTokensAllg.append( listGramTokens )

	# all done
	return listTokensAllg

def clean_text( original_text, dict_common_config, whitespace_chars = None ) :
	"""
	clean a block of unicode text ready for tokenization. replace whitespace with spaces.
	| #hashtag and @username are left intact so will become whole tokens e.g. #newyork @stuart_e_middle.
	| namespace entities like email addresses, web addresses and fragments (e.g. www.news.nz) are removed
	| strip apostrophes as these make tokens difficult to match ("'" and "'s" removed)

	:param unicode original_text: UTF-8 text to clean
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 
	:param unicode whitespace_chars: whitespace characters. if None the configuration setting will be used in dict_common_config

	:return: clean text
	:rtype: unicode
	"""

	# check args without defaults
	if not isinstance( original_text, unicode ) and not isinstance( original_text, str ) :
		raise Exception( 'invalid original_text' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	strText = copy.deepcopy( original_text )
	if whitespace_chars == None :
		strCharWhitespace = dict_common_config['whitespace']
	else :
		strCharWhitespace = whitespace_chars

	# convert to lower case as tweets are pretty random about using cases so its not very useful
	# (e.g. in formal docs named entities use capitals but for tweets this is useless)
	# note: this will prevent accurate POS and NE later so not always a good thing!
	if dict_common_config['lower_tokens'] == True :
		strText = unicode( strText ).lower()
	else :
		strText = unicode( strText );

	# remove ' since they cause problems later when processing
	# as tokens wont match (e.g. dont != don't for simple matching)
	# and John's -> John since its not actually a plural
	strText = string.replace( strText,"'s",'' )
	strText = string.replace( strText,"'S",'' )
	strText = string.replace( strText,"'",'' )

	# remove user defined whitespace
	# note: do this AFTER checking for ' handling
	for cWhitespace in strCharWhitespace :
		strText = string.replace( strText,cWhitespace,' ' )

	# replace sequences of space and tabs with a single space
	# strip normal whitespace (space, tab, newline) from start and end of text
	# strText = re.sub( r'\s+', " ", strText ).strip()
	strText = re.sub( r'[ \t]+', " ", strText ).strip()

	# all done
	return strText

def check_retweet( original_text ) :
	"""
	check for rwteeets (assumes raw unprocessed text e.g. 'RT @username ...')

	:param unicode original_text: UTF-8 text to clean

	:return: true if text contains a retweet pattern
	:rtype: bool
	"""

	# check args without defaults
	if not isinstance( original_text, unicode ) :
		raise Exception( 'invalid original_text' )

	bRetweet = False

	# the official Twitter retweet protocol is to add 'RT @username' in front of a retweet
	# this is not mandatory but most people follow this
	strText = original_text.lower()
	if strText.startswith( 'rt @' ) :
		bRetweet = True

	# also support these variants
	if strText.startswith( 'rt "@' ) :
		bRetweet = True
	if strText.startswith( 'rt :@' ) :
		bRetweet = True
	if strText.startswith( 'rt ''@' ) :
		bRetweet = True

	# also check for the matches WITHIN the string itself as people often retweet by putting a comment at front manually
	if ' rt @' in strText :
		bRetweet = True
	if ' rt "@' in strText :
		bRetweet = True
	if ' rt :@' in strText :
		bRetweet = True
	if ' rt ''@' in strText :
		bRetweet = True

	return bRetweet

#
# check to see if tokens are only stoplist tokens
# listTokens = tokens to check against a stoplist
# dictCommonConfig = dict <- common_parse_lib.get_common_config()
# return = True if ALL tokens match the stoplist (i.e. token set is useless as a phrase)
#
def is_all_stoplist( list_tokens, dict_common_config ) :
	"""
	check to see if tokens are only stoplist tokens

	:param list list_tokens: list of unigram tokens
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:return: True if ALL tokens match the stoplist (i.e. token set is useless as a phrase)
	:rtype: bool
	"""

	# check args without defaults
	if not isinstance( list_tokens, list ) :
		raise Exception( 'invalid list_tokens' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	listStoplist = dict_common_config['stoplist']

	for strToken in list_tokens :
		if listStoplist.count(strToken) == 0 :
			return False

	return True

def pos_tag_tokenset( token_set, lang, dict_common_config, timeout = 300.0 ) :
	"""
	POS tag a batch of tokenized sentences for a specific langauge. it is more efficient to POS tag in reasonably large batches as the POS tagger is a separate process that must be invoked using an OS exec and a Python subprocess command. there is a fixed overhead for sub-process and pipe setup time (e.g. 1-2 seconds) so processing text in bulk is more efficient than many small separate sentences.

	| note: the POS tagger used is chosen from TreeTagger, Stanford and Treebank based on language code
	| note: URL's and namespaces matching regex patterns provided in dict_common_config will get a POS tag of 'URI' or 'NAMESPACE' regardless of which POS tagger is used
	| note: tokens matching characters in dict_common_config['sent_token_seps'] will be labelled with a POS tag 'NEWLINE'

	:param list token_set: list of tokens for a set of of sentences. each sentence has a token set, which is itself a list of either tokenized phrase tuples or tokenized phrase strings. e.g. [ [ ('london',),('attacks',),('are',) ... ], ... ] e.g. [ [ 'london','attacks','are', ... ], ... ]
	:param list lang_codes: list of ISO 639-1 2 character language codes (e.g. ['en','fr'])
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 
	:param int timeout: timeout in seconds for POS tagger process in the unlikely event the POS tagger hangs

	:return: list of POS tagged sentences e.g. [ [ ('And', 'CC'), ('now', 'RB'), ('for', 'IN'), ('something', 'NN'), ('completely', 'RB'), ('different', 'JJ') ], ... ]
	:rtype: list
	"""

	# check args without defaults
	if not isinstance( token_set, list ) :
		raise Exception( 'invalid token_set' )
	if (not isinstance( lang, str )) and (not isinstance( lang, unicode )) :
		raise Exception( 'invalid lang' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	# POS tagger is an external EXEC unless we use the NLTK default POS tagger (good for english only!)
	listCMD = None
	strType = 'treebank'
	listNewlineChars = dict_common_config['sent_token_seps']

	# apply known sub-language mappings to primary language (e.g. uk -> ru)
	strLangBase = lang.lower()
	if strLangBase == 'uk' :
		strLangBase = 'ru'

	# get POS mapping type to use for this base language
	# OR use the default POS tagger (treebank)
	if strLangBase in dict_common_config['lang_pos_mapping'] :
		strType = dict_common_config['lang_pos_mapping'][strLangBase]

	# get command line to exec POS tagger
	if strType == 'treetagger' :
		if strLangBase == 'bg' :
			strPARFile = 'bulgarian-utf8.par'
		elif strLangBase == 'nl' :
			strPARFile = 'dutch-utf8.par'
		elif strLangBase == 'en' :
			strPARFile = 'english-utf8.par'
		elif strLangBase == 'et' :
			strPARFile = 'estonian.par'
		elif strLangBase == 'fi' :
			strPARFile = 'finnish-utf8.par'
		elif strLangBase == 'fr' :
			strPARFile = 'french.par'
		elif strLangBase == 'de' :
			strPARFile = 'german-utf8.par'
		elif strLangBase == 'it' :
			strPARFile = 'italian-utf8.par'
		elif strLangBase == 'pl' :
			strPARFile = 'polish-utf8.par'
		elif strLangBase == 'ru' :
			strPARFile = 'russian.par'
		elif strLangBase == 'sk' :
			strPARFile = 'slovak-utf8.par'
		elif strLangBase == 'es' :
			strPARFile = 'spanish-utf8.par'

		if sys.platform == "win32" :
			# windows
			listCMD = [
				dict_common_config['treetagger_base_dir'] + os.sep + 'bin' + os.sep + 'tree-tagger.exe',
				dict_common_config['treetagger_base_dir'] + os.sep + 'lib' + os.sep + strPARFile,
				'-token'
				]
		else :
			# linux
			listCMD = [
				dict_common_config['treetagger_base_dir'] + os.sep + 'bin' + os.sep + 'tree-tagger',
				dict_common_config['treetagger_base_dir'] + os.sep + 'lib' + os.sep + strPARFile,
				'-token'
				]

	elif strType == 'stanford' :

		raise Exception( 'stanford POS not supported yet')

	elif strType == 'treebank' :
		listCMD = None

	else :
		raise Exception( 'unknown POS tagger type : ' + strType )

	# exec command or use NLTK treebank POS
	if listCMD == None :
		# default POS is nltk Penn Treebank
		# listResult = [ [(token,pos),...], ... ]
		# e.g. [ [('And', 'CC'), ('now', 'RB'), ('for', 'IN'), ('something', 'NN'), ('completely', 'RB'), ('different', 'JJ')] ]
		listResult = []
		for listSentTokens in token_set :
			if len(listSentTokens) > 0 :
				if isinstance( listSentTokens[0],tuple ) :
					listSentAsString = []
					for tupleToken in listSentTokens :
						listSentAsString.append( tupleToken[0] )
				else :
					listSentAsString = listSentTokens

				listPOS = nltk.pos_tag( listSentAsString )

				# force any tokens matching a URL or namespace to have a LINK post tag
				# and escape out the POS delimiter character to make sure serialized POS tags are not like //SYM
				for nTokenIndex in range(len(listPOS)) :
					strToken = listPOS[nTokenIndex][0]
					strPOS = listPOS[nTokenIndex][1]

					if strToken in listNewlineChars :
						strPOS = 'NEWLINE'
					else :

						listReplacementRegexName = dict_common_config['token_preservation_regex']
						for (strRegexName,strPOSTokenName) in listReplacementRegexName :
							rePattern = dict_common_config[ strRegexName ]
							if rePattern.match( strToken ) != None :
								strPOS = strPOSTokenName
								break

					listPOS[nTokenIndex] = (strToken,strPOS)

				"""
				OLD
				# force any tokens matching a URL or namespace to have a LINK post tag
				# and escape out the POS delimiter character to make sure serialized POS tags are not like //SYM
				for nTokenIndex in range(len(listPOS)) :
					strToken = listPOS[nTokenIndex][0]
					strPOS = listPOS[nTokenIndex][1]

					if dict_common_config['regex_url'] != None :
						if dict_common_config['regex_url'].match( strToken ) != None :
							strPOS = 'URI'

					if dict_common_config['regex_namespace'] != None :
						if dict_common_config['regex_namespace'].match( strToken ) != None :
							strPOS = 'NAMESPACE'

					if strToken in listNewlineChars :
						strPOS = 'NEWLINE'
					
					listPOS[nTokenIndex] = (strToken,strPOS)
				"""

				listResult.append( listPOS )

		return listResult

	else :
		# treetagger OR stanford run as an external process using PIPE's
		p = subprocess.Popen( listCMD, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )

		# create a single set of tokens to POS tag
		# but remember the sentence index so we can re-construct the tokenset afterwards
		listTokens = []
		listSentIndex = []
		nCount = 0
		for listSentTokens in token_set :
			if len(listSentTokens) > 0 :
				if isinstance( listSentTokens[0],tuple ) :
					listSentAsString = []
					for tupleToken in listSentTokens :
						listSentAsString.append( tupleToken[0] )
				else :
					listSentAsString = listSentTokens

				listTokens.extend( listSentAsString )
				nCount = nCount + len( listSentAsString )

			listSentIndex.append( nCount )

		# read in a thread to avoid PIPE deadlocks (see popen() and all the pipe horrors for python!)
		queueBufferOut = Queue.Queue()
		threadOut = threading.Thread( target = read_pipe_stdout, args=(p.stdout,queueBufferOut,len(listTokens)) )
		threadOut.setDaemon( True )
		threadOut.start()

		queueBufferErr = Queue.Queue()
		threadErr = threading.Thread( target = read_pipe_stderr, args=(p.stderr,queueBufferErr) )
		threadErr.setDaemon( True )
		threadErr.start()

		# send newline delimited set of tokens to the POS tagger
		# note: if we get a newline token \n or \r we will NOT get a response from the POS tagger so this special case is handled later
		for strToken in listTokens :
			if not strToken in listNewlineChars :
				strText = strToken + '\n'
				p.stdin.write( strText.encode( 'utf8' ) )
				p.stdin.flush()

		# close STDIN to force entire PIPE to be flushed when processing
		# if left open (e.g. for more data) some text in PIPE will sit in an internal buffer and not get processed. cannot find a solution to this - lots of effort looking
		p.stdin.close()

		# wait for the read thread to get the right number of lines (i.e. tokens)
		# timeout = seconds (float) worse case
		
		threadOut.join( timeout )
		threadErr.join( timeout )

		# ensure process has been terminated (closing STDIN should do this)
		# manually poll for timeout in case of obscure fails (e.g. PIPE problems)
		nReturnCode = None
		nTimeWait = 0.0
		while (nReturnCode != None) or (nTimeWait > timeout) :
				nReturnCode = p.poll()
				if nReturnCode == None :
					nTimeWait = nTimeWait + 1.0
					thread.sleep(1)
		if nTimeWait > timeout :
			raise Exception( 'POS tagger timeout waiting for response : ' + repr(listTokens) )

		# parse result and reconstruct the token set
		# tagger result = term \t pos \n
		listResult = []
		nCount = 0
		nIndexPos = 0

		for listSentTokens in token_set :

			listTaggedSent = []

			for nIndexOriginal in range(len(listSentTokens)) :

				if not listSentTokens[nIndexOriginal] in listNewlineChars :

					# check we have a POS tagged token to read
					if queueBufferOut.empty() == True :

						# log error so we know what POS tagger reported on stderr
						if dict_common_config['logger'] != None :
							strLine = queueBufferErr.get().strip()
							dict_common_config['logger'].warn( 'POS failed (failed to POS tag all tokens) : ' + strLine )
						raise Exception( 'failed to POS tag all tokens (see log for details)' )

					# parse tagger result
					strPOS = queueBufferOut.get().strip()
					listPOS = strPOS.split('\t')

					if len(listPOS) != 2 :
						raise Exception( 'POS failed : ' + repr(strPOS) )
					else :

						# force any tokens matching a URL or namespace to have a LINK post tag
						# and escape out the POS delimiter character to make sure serialized POS tags are not like //SYM
						strToken = listPOS[0]
						strPOS = listPOS[1]

						if strToken in listNewlineChars :
							strPOS = 'NEWLINE'
						else :

							listReplacementRegexName = dict_common_config['token_preservation_regex']
							for (strRegexName,strPOSTokenName) in listReplacementRegexName :
								rePattern = dict_common_config[ strRegexName ]
								if rePattern.match( strToken ) != None :
									strPOS = strPOSTokenName
									break

						listPOS = (strToken,strPOS)

						"""
						OLD
						if dict_common_config['regex_url'] != None :
							if dict_common_config['regex_url'].match( strToken ) != None :
								strPOS = 'URI'

						if dict_common_config['regex_namespace'] != None :
							if dict_common_config['regex_namespace'].match( strToken ) != None :
								strPOS = 'NAMESPACE'

						if strToken in listNewlineChars :
							strPOS = 'NEWLINE'
						
						listPOS = (strToken,strPOS)
						"""

						# add tuple to token set
						listTaggedSent.append( tuple(listPOS) )

				else :
					# add newline chat in without expecting a POS tag
					# label newlines as NEWLINE
					listTaggedSent.append( ( listSentTokens[nIndexOriginal],'NEWLINE' ) )

			# add POS tagged set even if its empty (e.g. emoty string)
			listResult.append( listTaggedSent )

		return listResult

def read_pipe_stdout( pipe_handle, queue_buffer, lines_expected = 1 ) :
	"""
	internal POS tagger process pipe callback function

	:param file file_handle: pipe handle to POS tagger output
	:param Queue.Queue() queue_buffer: queue where pipe output can be stored
	:param int lines_expected: number of lines expected so we do not read other sentences from pipe
	"""

	try :

		nCount = 0
		while nCount < lines_expected :
			# read UTF-8 data from TreeTagger
			strLine = pipe_handle.readline().decode( 'utf-8' )
			if len(strLine) > 0 :
				queue_buffer.put( strLine )
				nCount = nCount + 1
			else :
				return
	except :
		# PIPE work should be hard to fail
		return

def read_pipe_stderr( pipe_handle, queue_buffer ) :
	"""
	internal POS tagger process pipe callback function

	:param file file_handle: pipe handle to POS tagger errors
	:param Queue.Queue() queue_buffer: queue where pipe errors can be stored
	"""
	try :
		strLine = pipe_handle.read()
		if len(strLine) > 0 :
			queue_buffer.put( strLine )
	except :
		# PIPE work should be hard to fail
		return

def create_sent_trees( list_pos, dict_common_config, replace_brackets = True ) :
	"""
	create a set of nltk.Tree structures for sentences. sent delimiter characters are taken from dict_common_config['sent_token_seps'] and the period character

	:param list list_pos: POS tagged sentence e.g. [ ('And', 'CC'), ('now', 'RB'), ('for', 'IN'), ('something', 'NN'), ('completely', 'RB'), ('different', 'JJ') ]
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 
	:param bool replace_brackets: escape out tokens and POS tags that contain brackets so they are nltk.Tree safe using common_parse_lib.escape_tagged_token()

	:return: list of nltk.Tree sentence structures e.g. [ nltk.Tree(S And/CC now/RB for/IN something/NN completely/RB different/JJ), ... ]
	:rtype: list
	"""

	if not isinstance( list_pos, list ) :
		raise Exception( 'invalid list_pos' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	listSentSep = dict_common_config['sent_token_seps']

	# replace bracket chars in POS tag list
	listPOS = copy.deepcopy( list_pos )
	if replace_brackets == True :
		for nIndexPOS in range(len(listPOS)) :
			listPOS[nIndexPOS] = escape_tagged_token( listPOS[nIndexPOS] )

	listTrees = []
	nIndexLast = 0
	nIndexTarget = 0
	while( nIndexTarget < len(listPOS) ) :
		if (listPOS[nIndexTarget][0] in listSentSep) or (listPOS[nIndexTarget][0] == '.') :
			# make a sent unless its a single . character
			if nIndexTarget != nIndexLast :

				# make a tree from POS
				strPOSSerialized = serialize_tagged_list(
					listPOS[ nIndexLast:nIndexTarget ],
					dict_common_config = dict_common_config,
					serialization_style = 'tree',
					replace_brackets = replace_brackets )
				strTreeSerialized = '(S ' + strPOSSerialized + ')'
				treeObj = parse_serialized_tagged_tree( strTreeSerialized, dict_common_config = dict_common_config )
				listTrees.append( treeObj )

			nIndexLast = nIndexTarget + 1
		nIndexTarget = nIndexTarget + 1
	
	if (nIndexLast < nIndexTarget) and (nIndexLast < len(listPOS)) :
		# make a tree from POS
		strPOSSerialized = serialize_tagged_list(
			listPOS[ nIndexLast: ],
			dict_common_config = dict_common_config,
			serialization_style = 'tree',
			replace_brackets = replace_brackets )
		strTreeSerialized = '(S ' + strPOSSerialized + ')'
		treeObj = parse_serialized_tagged_tree( strTreeSerialized, dict_common_config = dict_common_config )
		listTrees.append( treeObj )

	return listTrees

def serialize_tagged_list( list_pos, dict_common_config, serialization_style = 'pos', replace_brackets = True ) :
	"""
	serialize POS tagged tokens (list)
	| note: the POS separator (e.g. '/') is replaced in all tokens and POS tags so it is always good for a separator in the serialization

	:param list list_pos: POS tagged sentence e.g. [ ('And', 'CC'), ('now', 'RB'), ('for', 'IN'), ('something', 'NN'), ('completely', 'RB'), ('different', 'JJ') ]
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 
	:param str serialization_style: either POS tag list style (pos) or sentence tree style (tree). pos style is 'and/CC now/RB ...'. tree style is '(CC and) (RB now) ...'
	:param bool replace_brackets: escape out tokens and POS tags that contain brackets so they are nltk.Tree safe using common_parse_lib.escape_tagged_token()

	:return: serialized POS tagged sentence in style requested e.g. 'new/NN york/NN' 
	:rtype: unicode
	"""

	if not isinstance( list_pos, list ) :
		raise Exception( 'invalid list_pos' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	strPOSsep = dict_common_config['pos_sep'][0]
	strPOSreplacement = dict_common_config['pos_sep'][1]

	# replace bracket chars in POS tag list
	listPOS = copy.deepcopy( list_pos )
	if replace_brackets == True :
		for nIndexPOS in range(len(listPOS)) :
			listPOS[nIndexPOS] = escape_tagged_token( listPOS[nIndexPOS] )

	listSerialized = []
	for nIndex in range(len(listPOS)) :
		strToken = listPOS[nIndex][0]
		strPOS = listPOS[nIndex][1]
		if serialization_style == 'pos' :
			# replace / character as is used to indicate a POS tag
			strToken = strToken.replace( strPOSsep,strPOSreplacement )
			strPOS = strPOS.replace( strPOSsep,strPOSreplacement )

			if nIndex == 0 :
				listSerialized.extend( [strToken,strPOSsep,strPOS] )
			else :
				listSerialized.extend( [' ',strToken,strPOSsep,strPOS] )
		elif serialization_style == 'tree' :
			if nIndex == 0 :
				listSerialized.extend( ['(',strPOS,' ',strToken,')'] )
			else :
				listSerialized.extend( [' (',strPOS,' ',strToken,')'] )
		else :
			raise Exception( 'unknown serialization style : ' + str(serialization_style) )

	# return serialized list
	# note: spaces already in list at right places
	return u''.join( listSerialized )

def serialize_tagged_tree( tree_sent, dict_common_config ) :
	"""
	serialize POS tagged tokens (tree). this function will go recursive if the tree has one or more subtrees.
	| note: the POS separator (e.g. '/') is replaced in all tokens and POS tags so it is always good for a separator in the serialization
	| note: if tokens contain the sent '(' character then the serialized form will be difficult to parse correctly e.g. '(S troub)le/NN yes/NN)' so it is best to escape out the () characters if this is an issue prior to calling this function. for example replace leaf '(' characters with '__OBC__'. 

	:param nltk.Tree tree_sent: POS tagged sentence e.g. (S And/CC now/RB for/IN something/NN completely/RB different/JJ)
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:return: serialized POS tagged sentence e.g. 'new/NN york/NN'
	:rtype: unicode
	"""

	if not isinstance( tree_sent, nltk.tree.Tree ) :
		raise Exception( 'invalid tree_sent')
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	strSerialized = '(' + tree_sent.label()
	listPOS = []
	for leaf in tree_sent :
		if isinstance( leaf, nltk.tree.Tree ) :
			if len(listPOS) > 0 :
				strSerialized = strSerialized + ' ' + ' '.join( listPOS )
				listPOS = []
			strSerialized = strSerialized + ' ' + serialize_tagged_tree( leaf, dict_common_config )
		else :
			# note: POS is already in serialized form e.g. 'London/NP' or '(NP London)'
			listPOS.append( leaf )
	if len(listPOS) > 0 :
		strSerialized = strSerialized + ' ' + ' '.join( listPOS )
	strSerialized = strSerialized + ')'

	return strSerialized

'''
# NOT NEEDED ANYMORE
def strip_serialized_POS_tags( tagged_sent, dict_common_config, serialization_style = 'pos' ) :
	"""
	strip out POS tags from a serialized POS tagged sentence and return the plain string.

	:param unicode tagged_sent: serialized POS tagged sentence from common_parse_lib.serialize_tagged_tree() or common_parse_lib.serialize_tagged_list()
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 
	:param str serialization_style: either POS tag list style (pos) or sentence tree style (tree). pos style is 'and/CC now/RB ...'. tree style is '(CC and) (RB now) ...'

	:return: plain text without POS tags or tree structures
	:rtype: unicode
	"""

	if (not isinstance( tagged_sent, str)) and (not isinstance( tagged_sent, unicode)) :
		raise Exception( 'invalid tagged_sent')
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	strPOSsep = dict_common_config['pos_sep'][0]
	listTokens = []

	if not strPOSsep in tagged_sent :
		raise Exception( 'tagged_sent not a POS tagged string (no "' + strPOSsep + '" POS separator found)')

	# regex to match POS tags without relying on spaces which might be included in the tokens (e.g. 'cat no 1/CAT_INDEX')
	rePattern = dict_common_config['regex_pos_parse']
	listTokens = []
	listMatches = rePattern.findall( tagged_sent )
	for strMatch in listMatches :
		nPosSep = strMatch.index( strPOSsep )
		listTokens.append( strMatch[:nPosSep] )

	# return serialized list of tokens (without POS tags)
	return ' '.join( listTokens )
'''

def parse_serialized_tagged_tree( serialized_tree, dict_common_config ) :
	"""
	parse a previously serialized tree
	| note: any leaf '(' characters must have been escaped out otherwise a parse error will occur (usually creating invalid subtrees). for example replace leaf '(' characters with '__OBC__'. 

	:param unicode serialized_tree: serialized tree structure containing POS tagged leafs from common_parse_lib.serialize_tagged_tree()
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:return: tree representing POS tagged sentence e.g. (S And/CC now/RB for/IN something/NN completely/RB different/JJ)
	:rtype: nltk.Tree
	"""

	if (not isinstance( serialized_tree, str)) and (not isinstance( serialized_tree, unicode)) :
		raise Exception( 'invalid serialized_tree')
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'invalid dict_common_config' )

	# leaf = tree children (e.g. (CAT_INDEX Cat. No.).
	# there might be any characters after the POS tag (inc whitespace). make sure leaf match is preceeded by a non bracket characterand a space.
	reLeaf = ur'(?<=[^()] )[^()]*'
	listBrackets = '()'

	# use NLTK parse function with this custom regex
	treeSent = nltk.Tree.fromstring( serialized_tree, brackets=listBrackets, node_pattern=None, leaf_pattern=reLeaf )

	# all done
	return treeSent

def escape_tagged_token( tuple_pos, open_bracket_replacement = '__OB__', close_bracket_replacement = '__CB__' ) :
	"""
	escape open and close brackets in a POS token to make it nltk.Tree safe

	:param tuple tuple_pos: tuple of tagged POS entry = (token, pos)
	:param unicode open_bracket_replacement: replacement token for open bracket
	:param unicode close_bracket_replacement: replacement token for close bracket

	:return: escaped POS token = (token, pos)
	:rtype: tuple
	"""

	listEntry = []
	listEntry.append( escape_token( tuple_pos[0], open_bracket_replacement, close_bracket_replacement ) )
	listEntry.append( escape_token( tuple_pos[1], open_bracket_replacement, close_bracket_replacement ) )
	return tuple( listEntry )

def unescape_tagged_token( tuple_pos, open_bracket_replacement = '__OB__', close_bracket_replacement = '__CB__' ) :
	"""
	unescape open and close brackets in a POS token

	:param tuple tuple_pos: tuple of tagged POS entry = (token, pos)
	:param unicode open_bracket_replacement: replacement token for open bracket
	:param unicode close_bracket_replacement: replacement token for close bracket

	:return: unescaped POS token = (token, pos)
	:rtype: tuple
	"""

	listEntry = []
	listEntry.append( unescape_token( tuple_pos[0], open_bracket_replacement, close_bracket_replacement ) )
	listEntry.append( unescape_token( tuple_pos[1], open_bracket_replacement, close_bracket_replacement ) )
	return tuple( listEntry )

def escape_token( token_str, open_bracket_replacement = '__OB__', close_bracket_replacement = '__CB__' ) :
	"""
	escape open and close brackets in a token to make it nltk.Tree safe

	:param unicode token_str: token test to process
	:param unicode open_bracket_replacement: replacement token for open bracket
	:param unicode close_bracket_replacement: replacement token for close bracket

	:return: unescaped text
	:rtype: unicode
	"""

	return token_str.replace( '(', open_bracket_replacement ).replace( ')', close_bracket_replacement )

def unescape_token( token_str, open_bracket_replacement = '__OB__', close_bracket_replacement = '__CB__' ) :
	"""
	unescape open and close brackets in a token

	:param unicode token_str: token test to process
	:param unicode open_bracket_replacement: replacement token for open bracket
	:param unicode close_bracket_replacement: replacement token for close bracket

	:return: unescaped text
	:rtype: unicode
	"""

	return token_str.replace( open_bracket_replacement, '(' ).replace( close_bracket_replacement, ')' )


def extract_matches( list_pos, pattern_dict, list_linguistic_labels, dict_common_config ) :
	"""
	extract entoty patterns from a set of regex patterns operating applied to POS tagged text
	return all matches

	:param list list_pos: tagged sent = [ (t1,p1),(t2,p2), ... ]
	:param dict pattern_dict: dict pattern for relationships = { 'pattern_type' : [ ( NE_type, ... ) | None, ( NE_type, ... ) | None, RegexObject,re.IGNORECASE | re.UNICODE | ... ] }
	:param dict list_linguistic_labels: list of lingistic labels so they can be differntiated from POS labels in sent trees (e.g. SOURCE)
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:returns : dict of rel types. each rel type entry is itself a dict of regex named group data { match_type : [ match1, match2 ... ] }. rel dict entry will be {} if regex does not have any named groups. the actual text returned is entirely dependant on the regex pattern.
	:rtype : dict
	"""

	if not isinstance( pattern_dict, dict ) :
		raise Exception( 'pattern_dict not a dict' )
	if not isinstance( list_linguistic_labels, list ) :
		raise Exception( 'list_linguistic_labels not a list' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'dict_common_config not a dict' )
	if not isinstance( list_pos, list ) :
		raise Exception( 'list_pos not a list' )

	# get a list of all sents (there might be a few if newline delimiter is present in text) in this text
	listTrees = create_sent_trees( list_pos, dict_common_config = dict_common_config, replace_brackets = True )

	# run patterns on all sent trees
	# listMatch = [(strMatch,nPosMatchStart,nPosMatchEnd,strGroupName ), ...]
	# listSentMatches = [ listMatch, ... ]
	listSentMatches = match_linguistic_patterns(
		list_sent_trees = listTrees,
		pattern_dict = pattern_dict,
		dict_common_config = dict_common_config )

	#dict_common_config['logger'].info('LIST_MATCH = ' + repr( listSentMatches ) )

	# apply sent match results to sent tree to make a linguistically annotated tree for each sent
	# this will handle match subsumption and overlaps
	listSentTreesAnnotated = annotate_sent_with_pattern_matches(
		list_sent_trees = listTrees,
		list_sent_matches = listSentMatches,
		dict_common_config = dict_common_config )

	#dict_common_config['logger'].info('LIST_TREE = ' + repr( listSentTreesAnnotated ) )

	# provide an aggregated list of top level match entities that have been identified in all the sents
	dictMatches = {}
	for treeSent in listSentTreesAnnotated :

		#dict_common_config['logger'].info('SENT = ' + repr( u' '.join( treeSent.leaves() ) ) )
		#dict_common_config['logger'].info('TREE = ' + serialize_tagged_tree( treeSent, dict_common_config = dict_common_config ) )

		walk_evidence_tree( treeSent, list_linguistic_labels, dict_common_config, dict_matches = dictMatches )

	return dictMatches


def walk_evidence_tree( tree_sent, list_linguistic_labels, dict_common_config, dict_matches = {} ) :
	"""
	walk sent tree for looking for known evidence labels. the tree will be recursively walked.

	:param nltk.Tree tree_sent: NLTK tree for sent annotated with POS tags and linguistic labels
	:param dict dict_matches: match results (data in this dict will be changed by recursive calls to this function)
	:param dict list_linguistic_labels: list of lingistic labels so they can be differntiated from POS labels in sent trees (e.g. SOURCE)
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:returns : dict of rel types. each rel type entry is itself a dict of regex named group data { match_type : [ match1, match2 ... ] }. rel dict entry will be {} if regex does not have any named groups. the actual text returned is entirely dependant on the regex pattern.
	:rtype : dict
	"""

	# debug
	#dict_common_config['logger'].info('TREE = ' + common_parse_lib.serialize_tagged_tree( tree_sent, dict_common_config = dict_common_config ) )

	for leaf in tree_sent :

		if isinstance( leaf, nltk.tree.Tree ) :

			# check entity type is a linguistic entity and not a POS label
			strEntityType = leaf.label()
			if strEntityType in list_linguistic_labels :

				# serialized text without POS tags
				strEntity = u' '.join( leaf.leaves() )

				# unescape out any brackets
				strEntity = unescape_token( strEntity )

				# DEBUG
				#dict_common_config['logger'].info('SENT = ' + repr( u' '.join( tree_sent.leaves() ) ) )
				#dict_common_config['logger'].info('TREE = ' + serialize_tagged_tree( tree_sent, dict_common_config = dict_common_config ) )
				#dict_common_config['logger'].info('TYPE = ' + repr(strEntityType) )
				#dict_common_config['logger'].info('MATCH = ' + repr(strEntity) )

				# add entity to match list
				if not strEntityType in dict_matches.keys() :
					dict_matches[ strEntityType ] = []
				dict_matches[ strEntityType ].append( strEntity )
			
			# recurse into tree to see if we have sub-labels to find
			walk_evidence_tree( leaf, list_linguistic_labels, dict_common_config, dict_matches )


def match_linguistic_patterns( list_sent_trees, pattern_dict, dict_common_config ) :
	"""
	for each sent tree execute a provided set of regex patterns to extract linguistic patterns.
	return all matches ready for sent annotation

	:param list list_sent_trees: list of sent trees to process = [nltk.Tree, ...]
	:param dict pattern_dict: dict pattern = { 'pattern_type' : [ RegexObject, ... }
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:returns : list of pattern matches for each sent = [ [ ( matched text, start index in original text, end index in original text, LINGUISTIC_LABEL, PATTERN_TYPE ), ... ], ... ]. length of this list == length of list_sent_trees
	:rtype : list
	"""

	if not isinstance( pattern_dict, dict ) :
		raise Exception( 'pattern_dict not a dict' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'dict_common_config not a dict' )
	if not isinstance( list_sent_trees, list ) :
		raise Exception( 'list_sent_trees not a list' )

	# label entities within each sent
	listResultSet = []
	for nTreeIndex in range(len(list_sent_trees)) :

		treeObj = list_sent_trees[ nTreeIndex ]
		if not isinstance( treeObj, nltk.Tree ) :
			raise Exception( 'sent tree index ' + str(nTreeIndex) + ' not a nltk.Tree object : ' + str(type(treeObj)) )

		# debug
		#dict_common_config['logger'].info('TREE = ' + repr( treeObj ) )

		strTree = serialize_tagged_tree( treeObj, dict_common_config )

		# debug
		#dict_common_config['logger'].info('TREE_STR = ' + repr( strTree ) )

		# apply regex removing matches from text as we go to avoid duplicate matches
		listResult = []
		for strPatternName in pattern_dict.keys() :

			# each pattern type gets a fresh copy of the text to try to match against
			strTextToMatch = copy.deepcopy( strTree )

			# loop sequentially on patterns so most permissive patterns can be put last
			for rePattern in pattern_dict[ strPatternName ] :

				# nothing to do?
				#if len(strTextToMatch) == 0 :
				#	break;

				bOK = True
				while bOK == True :
					matchObj = rePattern.match( strTextToMatch )
					if matchObj == None :
						bOK = False
					else :
						# get all named matches from this pattern
						# if a named match is optional it might have a None value
						for strGroupName in matchObj.groupdict().keys() :

							strMatch = matchObj.group( strGroupName )
							if strMatch != None :

								# replace matched text with filler characters to avoid it matching again (do not delete it as you might artifically create a new viable text from fragments)
								# unichr( 0xFFFF ) = unicode noncharacter
								# not providing any POS tag with the noncharacter sequence will (a) keep the length of the text identical and (b) make it very likely no further matches will occur with this removed text

								nPosMatchStart = matchObj.start( strGroupName )
								nPosMatchEnd = matchObj.end( strGroupName )
								nSize = (nPosMatchEnd - nPosMatchStart) + 1

								# need a replacement that will not match BUT will not prevent other matches, so keep the sent structure
								if nSize > 4 :
									strReplacement = u'(- ' + u'-'*(nSize-4) + u')'
								else :
									raise Exception( 'text match < 5 characters (invalid sent tree?) : ' + repr(strTree) )

								strTextToMatch = strTextToMatch[:nPosMatchStart] + strReplacement + strTextToMatch[nPosMatchEnd+1:]

								# add match to result
								listResult.append( (strMatch, nPosMatchStart, nPosMatchEnd, strGroupName, strPatternName ) )

								# debug
								#dict_common_config['logger'].info('PATTERN ' + strPatternName + ' = ' + rePattern.pattern )
								#dict_common_config['logger'].info('TREE_STR = ' + repr( strTree ) )
								#dict_common_config['logger'].info('MATCHED = ' + repr(strMatch) )
								#dict_common_config['logger'].info('RESULT = ' + repr((nPosMatchStart,nPosMatchEnd,strGroupName )) )
								#dict_common_config['logger'].info('TEXT LEFT = ' + repr(strTextToMatch) )

		listResultSet.append( listResult )

	# return list of linguistic patterns found in each sent ([] if none)
	return listResultSet

def annotate_sent_with_pattern_matches( list_sent_trees, list_sent_matches, dict_common_config ) :
	"""
	process a set of sent patterns and create sent annotations as nltk.Tree entries
	provided heuristics to handle conflicts where annotations apply to the same (or partially overlapping) tokens:
		*first process matches that are completely subsumed by other matches. subsumed matched will appear as subtrees
		*second resolve matches with identical tokens (choose first match option in list)
		*third resolve matches that overlap but do not subsume (choose left-most match in text)
		*remove void matches
	return a set of sent trees with sub-trees for all matches provided

	:param list list_sent_trees: list of sent trees to process = [nltk.Tree, ...]
	:param list list_sent_matches: list of matches for each sent from cultural_heritage_parse_lib.match_linguistic_patterns()
	:param dict dict_common_config: config object returned from common_parse_lib.get_common_config() 

	:returns : list of sent trees with known entities labelled as sub-trees = [nltk.Tree ...]
	:rtype : list
	"""

	if not isinstance( list_sent_trees, list ) :
		raise Exception( 'list_sent_trees not a list' )
	if not isinstance( dict_common_config, dict ) :
		raise Exception( 'dict_common_config not a dict' )
	if not isinstance( list_sent_matches, list ) :
		raise Exception( 'list_sent_matches not a list' )

	listAnnotatedSentTrees = []

	# label entities within each sent
	for nTreeIndex in range(len(list_sent_trees)) :

		treeObj = list_sent_trees[ nTreeIndex ]
		if not isinstance( treeObj, nltk.Tree ) :
			raise Exception( 'sent tree index ' + str(nTreeIndex) + ' not a nltk.Tree object : ' + str(type(treeObj)) )
		listMatches = copy.deepcopy( list_sent_matches[ nTreeIndex ] )

		# create a serialized sent e.g. (S (CD 12) (PM Ronin))
		strTree = serialize_tagged_tree( treeObj, dict_common_config )

		# handle conflicts of matches sharing identical text
		# (a) process matches that are completely subsumed by other matches first
		# (b) resolve matches with identical text (simply choose first match option)
		# (c) resolve matches that overlap but do not subsume (simply choose left-most match in text)
		# remove matches and order list as per above (without actually changing text yet)
		# match = ( matched text, start index in original text, end index in original text, LINGUISTIC_LABEL )

		#listMatches = sorted( listMatches, key=lambda entry: entry[1], reverse=True )

		#dict_common_config['logger'].info( 'MATCHES1 ' + repr(listMatches) )

		# identical token check
		for nIndexMatch1 in range(len(listMatches)) :
			if listMatches[nIndexMatch1] != None :

				nPosMatchStart1 = listMatches[nIndexMatch1][1]
				nPosMatchEnd1 = listMatches[nIndexMatch1][2]

				for nIndexMatch2 in range(nIndexMatch1+1,len(listMatches)) :
					if listMatches[nIndexMatch2] != None :

						nPosMatchStart2 = listMatches[nIndexMatch2][1]
						nPosMatchEnd2 = listMatches[nIndexMatch2][2]

						# remove identical matches (keeping the first to appear in the list)
						if (nPosMatchStart2 == nPosMatchStart1) and (nPosMatchEnd2 == nPosMatchEnd1) :
							listMatches[nIndexMatch2] = None
							#dict_common_config['logger'].info( 'PRUNE identical ' + repr(nIndexMatch2) )

		#dict_common_config['logger'].info( 'MATCHES2 ' + repr(listMatches) )

		# subsumption of token check
		nIndexMatch1 = 0
		while nIndexMatch1 < len(listMatches) :
			if listMatches[nIndexMatch1] != None :

				nPosMatchStart1 = listMatches[nIndexMatch1][1]
				nPosMatchEnd1 = listMatches[nIndexMatch1][2]

				nIndexMatch2 = nIndexMatch1 + 1
				while nIndexMatch2 < len(listMatches) :
					if listMatches[nIndexMatch2] != None :

						nPosMatchStart2 = listMatches[nIndexMatch2][1]
						nPosMatchEnd2 = listMatches[nIndexMatch2][2]

						# subsumption - check if match 2 is subsumed by match 1
						if (nPosMatchStart2 >= nPosMatchStart1) and (nPosMatchEnd2 <= nPosMatchEnd1) :
							# swap position so subsumed match comes first
							entryTemp = listMatches[nIndexMatch2]
							listMatches[nIndexMatch2] = listMatches[nIndexMatch1]
							listMatches[nIndexMatch1] = entryTemp

							#dict_common_config['logger'].info( 'SWAP ' + repr( (nIndexMatch1,nIndexMatch2) ) )

							# recheck this position using the new match
							break

						# subsumption - check if match 1 is subsumed by match 2
						elif (nPosMatchStart1 >= nPosMatchStart2) and (nPosMatchEnd1 <= nPosMatchEnd2) :
							# subsumption but in right order - dont check for overlaps
							#dict_common_config['logger'].info( 'SUBSUMPTION NOOP ' + repr( (nIndexMatch1,nIndexMatch2) ) )
							pass

						# overlap check (keep the first to appear in the list) - no need to consider subsumption as its checked previously
						elif ((nPosMatchStart2 < nPosMatchStart1) and (nPosMatchEnd2 >= nPosMatchStart1)) or ((nPosMatchStart2 <= nPosMatchEnd1) and (nPosMatchEnd2 > nPosMatchEnd1)) :
							listMatches[nIndexMatch2] = None
							#dict_common_config['logger'].info( 'PRUNE overlap ' + repr( (nIndexMatch1,nIndexMatch2) ) )

					# increment
					nIndexMatch2 = nIndexMatch2 + 1

			# increment
			nIndexMatch1 = nIndexMatch1 + 1

		#dict_common_config['logger'].info( 'MATCHES3 ' + repr(listMatches) )

		# prune matches
		nIndexMatch1 = 0
		while nIndexMatch1 < len(listMatches) :
			if listMatches[nIndexMatch1] == None :
				listMatches.pop(nIndexMatch1)
			else :
				nIndexMatch1 = nIndexMatch1 + 1

		#dict_common_config['logger'].info( 'MATCHES4 ' + repr(listMatches) )
		#dict_common_config['logger'].info( 'TREE1 ' + repr(strTree) )

		# loop on each match and replace matched POS tagged text with a tree structure representing the entity
		# change all text position offsets when we make these changes so the next set of matches are inserted in the correct position
		for nIndexMatch1 in range(len(listMatches)) :

			tupleMatch = listMatches[nIndexMatch1]
			nPosMatchStart1 = tupleMatch[1]
			nPosMatchEnd1 = tupleMatch[2]
			strEntityType = tupleMatch[3]

			# note: compute match text again we might get embedded matches within it
			strMatch = strTree[nPosMatchStart1:nPosMatchEnd1]

			# debug
			#dict_common_config['logger'].info('T1 = ' + repr((strMatch,nPosMatchStart1,nPosMatchEnd1,strEntityType )) )
			#dict_common_config['logger'].info('T2 = ' + repr(strTree) )
			#dict_common_config['logger'].info('T3 = ' + repr(strTree[:nPosMatchStart1]) )
			#dict_common_config['logger'].info('T4 = ' + repr(strTree[nPosMatchEnd1:]) )

			strTree = u'{:s}({:s} {:s}){:s}'.format(
				strTree[:nPosMatchStart1],
				strEntityType,
				strMatch,
				strTree[nPosMatchEnd1:] )

			nExtraCharacters = 3 + len(strEntityType)
			for nIndexMatch2 in range(nIndexMatch1+1,len(listMatches)) :
				nPosMatchStart2 = listMatches[nIndexMatch2][1]
				nPosMatchEnd2 = listMatches[nIndexMatch2][2]
				# no overlap (i.e. subsumption as we delete overlaps earlier), offset both start and end character index
				if nPosMatchStart2 > nPosMatchEnd1 :
					tupleMatchEntry = (
						listMatches[nIndexMatch2][0],
						listMatches[nIndexMatch2][1] + nExtraCharacters,
						listMatches[nIndexMatch2][2] + nExtraCharacters,
						listMatches[nIndexMatch2][3] )
					listMatches[nIndexMatch2] = tupleMatchEntry
				# overlap (i.e. subsumption as we delete overlaps earlier), offset end character index
				elif nPosMatchEnd2 >= nPosMatchStart1 :
					tupleMatchEntry = (
						listMatches[nIndexMatch2][0],
						listMatches[nIndexMatch2][1],
						listMatches[nIndexMatch2][2] + nExtraCharacters,
						listMatches[nIndexMatch2][3] )
					listMatches[nIndexMatch2] = tupleMatchEntry


		#dict_common_config['logger'].info( 'MATCHES6 ' + repr(listMatches) )
		#dict_common_config['logger'].info( 'TREE2 ' + repr(strTree) )
		#if 'Fashionista_com' in strTree :
		#	sys.exit()

		# parse the next tree text to make a NLTK tree structure
		treeSent = parse_serialized_tagged_tree( strTree, dict_common_config = dict_common_config )

		# add to output list
		listAnnotatedSentTrees.append( treeSent )

	# return list of NLTK trees for this tagged text with the linguistic annotations inserted as subtrees
	return listAnnotatedSentTrees

