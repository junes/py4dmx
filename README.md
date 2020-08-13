py4dmx - dmx.py
===============


The aim of this python script is to provide a set of python functions to play
with DMX's REST API. (There are still some issues! ;-))

It requires Python Version 3.6 or higher for best results. If you want to test
the VCARD import make sure the vobject module is installed (python3-vobject).

Copy `dmx.cfg.example` to `dmx.cfg` and adjust it to your needs.


Some examples:

 * `dmx.py --help`  
   shows the list of options.

 * `dmx.py -s`  
   reads server setting and credentials from config file dmx.cfg to login and to return
   the current session id.

 * `dmx.py -v -s`  
   reads server setting and credentials from config file dmx.cfg to login and to return
   the current session id with verbose output.

 * `dmx.py -s -l -u "myusername" -p "mypassword"`  
   will login user "myusername" into DMX and output the current session id.

 * `dmx.py -l -u "myusername" -p "mypassword" -U https://dmx.example.com -s`  
   will login user "myusername" into DMX instance at URL https://dmx.example.com
   and output the current session id.

 * `dmx.py -C -u "myusername" -p "mypassword"`  
   creates a new user with user name "myusername" and password "mypassword".

 * `dmx.py -c /etc/dmx/config.properties -s`  
   uses the config file /etc/dmx/config.properties to read server settings and 
   admin password from there to login to server and output the current session id.

 * `dmx.py -l -u "myusername" -p "mypassword" -m -w "my shared workspace" -n "pied.piper"`  
   adds the user with username "pied.piper" to my workspace named "my shared workspace".

 * `dmx.py -f note_example.json -w "DMX"`  
   creates a new note topic from file note_example.json in workspace "DMX".

 * `dmx.py -N "foo" -B "bar" -w "Private Workspace"`  
   creates a new note topic with title "foo" and body "bar" in workspace "Private Workspace".

 * `dmx.py -M "my topicmap" -w "Private Workspace"`  
   creates a new topicmap "my topicmap" in workspace "Private Workspace".  

 * `dmy.py -R -i 1234 -o 5678 -x 150 -y 150 -P True -w "Private Workspace"`  
   reveales a topic with id 1234 on topicmap with id 4567 at position x=150 and y=150 in pinned mode.

 * `dmy.py -V vcard.vcf -w "Private Workspace"`  
   imports the contents of file vcard.vcf to a person topic in workspace "Private Workspace".


Copyright (c) 2019 DMX Systems <https://dmx.systems>    
License: GNU General Public License Version 3    
Author: Juergen Neumann <juergen@dmx.systems>    
Source: https://git.dmx.systems/dmx-contrib/py4dmx
Version: 0.3

## Version History

**0.3** -- Aug 13, 2020

* Chores:
    * adopt to DM5.0

**0.2**

**0.1**
