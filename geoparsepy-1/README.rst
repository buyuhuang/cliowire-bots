geoparsepy project
==================
geoparsepy is a Python geoparsing library that will extract and disambiguate locations from text. It uses a local OpenStreetMap database which allows very high and unlimited geoparsing throughput, unlike approaches that use a third-party geocoding service (e.g.  Google Geocoding API).

Geoparsing is based on named entity matching against OpenStreetMap (OSM) locations. All locations with names that match tokens will be selected from a target text sentence. This will result in a set of OSM locations, all with a common name or name variant, for each token in the text. Geoparsing included the following features :
* *token expansion* using location name variants (i.e. OSM multi-lingual names, short names and acronyms)
* *token expansion* using location type variants (e.g. street, st.)
* *token filtering* of single token location names against WordNet (non-nouns), language specific stoplists and peoples first names (nltk.corpus.names.words()) to reduce false positive matches
* *prefix checking* when matching in case a first name prefixes a location token(s) to avoid matching peoples full names as locations (e.g. Victoria Derbyshire != Derbyshire)

Location disambiguation is the process of choosing which of a set of possible OSM locations, all with the same name, is the best match. Location disambiguation is based on an evidential approach, with evidential features detailed below in order of importance:
* *token subsumption*, rejecting smaller phrases over larger ones (e.g. 'New York' will prefer [New York, USA] to [York, UK])
* *nearby parent region*, preferring locations with a parent region also appearing within a semantic distance (e.g. 'New York in USA' will prefer [New York, USA] to [New York, BO, Sierra Leone])
* *nearby locations*, preferring locations with closeby or overlapping locations within a semantic distance (e.g. 'London St and Commercial Road' will select from road name choices with the same name based on spatial proximity)
* *nearby geotag*, preferring locations that are closeby or overlapping a geotag
* *general before specific*, rejecting locations with a higher admin level (or no admin level at all) compared to locations with a lower admin level (e.g. 'New York' will prefer [New York, USA] to [New York, BO, Sierra Leone]

Currently the following languages are supported:
* English, French, German, Italian, Portuguese, Russian, Ukrainian
* All other languages will work but there will be no language specific token expansion available

geoparsepy works with Python 2.7 and has been tested on Windows 10, Windows 2012 Server, Ubuntu 14.04 LTS and Ubuntu 16.04 LTS.

This geoparsing algorithm uses a large memory footprint (e.g. 12 Gbytes RAM for global cities), RAM size proportional to the number of cached locations, to maximize matching speed. It can be naively parallelized, with multiple geoparse processes loaded with different sets of locations and the geoparse results aggregated in a last process where location disambiguation is applied. This approach has been validated across an APACHE Storm cluster running both Windows 2010 Server and Ubuntu 16.04 LTS. Run in 64bit mode.

Feature suggestions and/or bug reports can be sent to {geoparsepy}@it-innovation.soton.ac.uk. We do not however offer any software support beyond the examples and API documentation already provided.


Scientific publications
-----------------------
Middleton, S.E. Middleton, L. Modafferi, S. "Real-time Crisis Mapping of Natural Disasters using Social Media", Intelligent Systems, IEEE , vol.29, no.2, pp.9,17, Mar.-Apr. 2014

Middleton, S.E. Krivcovs, V. "Geoparsing and Geosemantics for Social Media: Spatio-Temporal Grounding of Content Propagating Rumours to support Trust and Veracity Analysis during Breaking News", ACM Transactions on Information Systems (TOIS), 34, 3, Article 16 (April 2016), 26 pages. DOI=10.1145/2842604 

A benchmark geoparse dataset is also available for free from the University of Southampton’s Web Observatory (https://web-001.ecs.soton.ac.uk/). Search for ‘GEOPARSE TWITTER BENCHMARK DATASET’ to find it.


geoparsepy user documentation
-----------------------------
https://pythonhosted.org/geoparsepy/readme.html


geoparsepy API documentation
----------------------------
https://pythonhosted.org/geoparsepy/index.html

The software is copyright 2016 University of Southampton IT Innovation Centre, UK (http://www.it-innovation.soton.ac.uk). It was created over a 5 year period under EU FP7 projects TRIDEC (grant agreement number 258723) and REVEAL (grant agreement number 610928). This software can only be used for research, education or evaluation purposes. A free commercial license is available on request to {geoparsepy}@it-innovation.soton.ac.uk. The University of Southampton IT Innovation Centre is open to discussions regarding collaboration in future research projects relating to this work.


geoparsepy license
----------------------------
https://pythonhosted.org/geoparsepy/license.html


Python libs needed
------------------
Python libs: psycopg2 >= 2.5, nltk >= 3.2, numpy >= 1.7, shapely >= 1.5
Database: PostgreSQL >= 9.3 and PostGIS >= 2.1 database loaded with database image containing global cities

For LINUX deployments the following is needed: sudo apt-get install libgeos-dev libgeos-3.4.2 libpq-dev
