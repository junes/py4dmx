py4dmx - dmx.py

The aim of this python script is to provide a set of python functions to play
with DeepaMehta's REST API.

When creating new topics, the script checks for exisiting topics with the same
name and will try to reuse them in composits, if possible (=aggregations).

So far the script has been tested and developed for objects with simple
cardinality, eg. one address, one telephone number, etc.

There are still some issues when there is more than one address in a complex
composites (like the provided json person example).

Copyright (c) 2016-2017, Juergen Neumann, GNU General Public License Version 3
