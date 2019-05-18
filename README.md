
py4dmx - dmx.py

The aim of this python script is to provide a set of python functions to play
with DMX's REST API.

There are still some issues!

Some examples:

 * dmx.py -s
   reads server setting and credentials from config file dmx.cfg to login and to return
   the current session id.

 * dmx.py -s -l -u "myusername" -p "mypassword"
   will login user "myusername" into DMX and output the current session id.

 * dmx.py -c /etc/dmx/config.properties -s
   looks into the config file /etc/dmx/config.properties to read server settings and 
   admin password from there to login to server and output the current session id.

 * dmx.py -l -u "myusername" -p "mypassword" -m -w "my shared workspace" -n "pied.piper"
   adds the user with username "pied.piper" to my workspace named "my shared workspace"


Copyright (c) 2019 DMX Systems <https://dmx.systems>    
License: GNU General Public License Version 3    
Author: Juergen Neumann <juergen@dmx.systems>    
