py4dmx - dmx.py

The aim of this python script is to provide a set of python functions to play
with DeepaMehta's REST API.

When creating new topics, the script checks for exisiting topics with the same
name and will try to reuse them in composits, if possible (=aggregations).

So far the script has been tested and developed for objects with simple
cardinality, eg. one address, one telephone number, etc.

There are still some issues when there is more than one address in a complex
composites (like the provided json person example).

Some examples:

 * dmx.py -s
   reads server setting and credentials from config file dmx.cfg to login and to return
   the current session id.

 * dmx.py -s -l -u "myusername" -p "mypassword"
   will login user "myusername" into deepamehta and output the current session id.

 * dmx.py -i "deepamehta" -s
   looks into the config file /etc/deepamehta/deepamehta.conf to read server settings and 
   admin password from there to login to server and output the current session id.

 * dmx.py -l -u "myusername" -p "mypassword" -m -w "my shared workspace" -n "pied.piper"
   adds the user with username "pied.piper" to my workspace named "my shared workspace"

 * dmx.py -i "otherdeepamehta" -c -u "otherusername" -p "otherpassword"
   creates a new user "otherusername" with "otherpassword" in instance "otherdeepamehta"


Copyright (c) 2016-2017, Juergen Neumann, GNU General Public License Version 3
