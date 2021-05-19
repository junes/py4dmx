#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  dmx.py - _dev.py
#
#  Copyright 2019 DMX Systems <https://dmx.systems>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
"""
The aim of the script is to provide a set of python functions to play
with DMX's REST API.

jpn - 20170231

"""

from __future__ import print_function

__author__ = 'Juergen Neumann <juergen@dmx.systems>'
__copyright__ = 'Copyright 2019, DMX Systems <https://dmx.systems>'
__license__ = 'GPL 3+'
__version__ = '0.3'
__maintainer__ = 'Juergen Neumann'
__email__ = 'juergen@dmx.systems'
__status__ = 'Development'
__doc__ = """
The aim of the script is to provide a set of python functions to play
with DMX's REST API.

jpn - 20170231

"""

import os
import sys
import platform
import json
import base64
import configparser
import hashlib
import argparse
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from timeit import default_timer as timer
from datetime import timedelta


## define global variables
VERBOSE = False     # VERBOSE mode (True|False)
JSESSIONID = None   # the first result of get_session_id
wsid_cache = {}     # global dictionary to cache worspace ids
config = configparser.ConfigParser()


def create_default_config():
    """
    This function creates the initial config object.
    """
    global config
    ## config is the ConfigParser instance that holds the config params
    sample_config = """
    [Credentials]
    authname = admin
    password =

    [Connection]
    protocol = http
    server = localhost
    port = 8080
    path = /
    workspace = DMX
    """
    config.read_string(sample_config)
    if VERBOSE:
        for section in config.sections():
            for (key, val) in config.items(section):
                print("CREATE DEFAULT CONFIG : %s: %s=%s" % (section, key, val))
    return


def read_default_config_file():
    """
    Reads the config parameter from file ./dmx.cfg
    """
    global config
    ## if parameter is empty or missing, use these parameters
    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    config_file_name = 'dmx.cfg'
    config_file = os.path.join(script_dir, config_file_name)
    if os.path.isfile(config_file):
        if VERBOSE:
            print("DEFAULT CONFIG FILE : reading file %s." % config_file)
        config.read(config_file)
    else:
        if VERBOSE:
            print("DEFAULT CONFIG FILE : Config file not found. Creating %s with default settings." % config_file)
        config_file = open(os.path.join(script_dir, config_file_name),'w')
        config.write(config_file)
        config_file.close()
    if VERBOSE:
        for section in config.sections():
            for (key, val) in config.items(section):
                print("DEFAULT CONFIG FILE : %s: %s=%s" % (section, key, val))
    return


def read_dmx_config_properties_file(config_file='config.properties'):
    """
    Reads the configuration data from '/path/to/dmx/config.properties'
    and overwrites the config settings with new values.
    """
    global config
    dmx_params = {}
    if os.access(config_file, os.R_OK):
        if VERBOSE:
            print("DMX CONFIG PROPERTIES: reading file %s." % config_file)
        with open(config_file) as f_in:
            lines = [_f for _f in (line.rstrip() for line in f_in) if _f]
    else:
        print("ERROR! Could not read config file %s." % (config_file))
        sys.exit(1)
    for this_line in lines:
        if not this_line[0] in ('', ' ', '#', ';'):
            try:
                key, val = this_line.strip().replace(" ", "").split('=', 1)
            except ValueError:
                print("INFO: No value found for %s in %s" % (key, config_file))
            else:
                dmx_params[key.lower()] = val

    port = dmx_params['org.osgi.service.http.port']
    password = dmx_params['dmx.security.initial_admin_password']
    config.add_section('Credentials')
    config.set('Credentials', 'authname', 'admin') # usualy the admin user
    config.set('Credentials', 'password', password) # usualy the admin password
    config.add_section('Connection')
    config.set('Connection', 'server', 'localhost') # usualy localhost
    config.set('Connection', 'port', port) # usualy 8080
    config.set('Connection', 'workspace', 'DMX') # usualy DMX

    for mandatory in ['org.osgi.service.http.port', 'dmx.security.initial_admin_password']:
        if mandatory not in list(dmx_params.keys()):
            print("ERROR! Could not read %s in config file %s." % (mandatory, config_file))
            sys.exit(1)
    return


def check_payload(payload=None):
    """
    This function checks the payload to be send to server and makes sure
    it is a valid json format.
    """
    if VERBOSE:
        print("CHECK PAYLOAD : TYPE = %s" % type(payload))
        print("CHECK PAYLOAD : LEN = %s" % len(payload))
        print("CHECK PAYLOAD : INPUT = %s" % payload)
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    try:
        payload = json.loads(json.dumps(payload, indent=3, sort_keys=True))
    except:
        print("ERROR! Could not read Payload. Not JSON?")
        sys.exit(1)
    else:
        if VERBOSE:
            print("CHECK PAYLOAD : OUTPUT = %s" % payload)
        return(payload)


def read_file(filename):
    """
    Here we open the file and read the content.
    """
    if VERBOSE:
        print("Reading file %s" % (filename))
    with open(filename, 'r') as data_file:
        data = data_file.read()
    data_file.close()
    if VERBOSE:
        print("READ FILE DATA: \n%s" % data)
    return(data)


def query_yes_no(question, default="no"):
    """
    Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
    It must be "yes" (the default), "no" or None (meaning
    an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def check_response(data):
    """
    This function returns a nicely formatted JSON string, if possible.
    """
    ##
    try:
        response = json.loads(data)
    except:
        if VERBOSE:
            print('CHECK RESPONSE : is not JSON (CHECK RESPONSE exception!)')
            print('CHECK RESPONSE : TYPE = %s' % type(response))
            print('CHECK RESPONSE : is "%s".' % response)
            print('CHECK RESPONSE : return "OK".')
        return("OK")
    else:
        if VERBOSE:
            print('CHECK RESPONSE : is JSON')
            print("CHECK RESPONSE : TYPE = %s" % type(response))
            pretty_print(response)
        return(response)


def get_base_64():
    """
    This function returns the authentication string for the user against DMX
    """
    authname = config.get('Credentials', 'authname') # usualy the admin user
    password = config.get('Credentials', 'password') # usualy the admin password
    if VERBOSE:
        print("GET BASE64 : authname = %s, password = %s" % (authname, password))
    authstring = bytes((str(authname + ':' + password)), 'UTF-8')
    base64string = (base64.b64encode(authstring)).decode('UTF-8')
    if VERBOSE:
        print("GET BASE64 : base64string = %s" % base64string)
    return(base64string)


def set_host_url(url):
    """
    This function sets the global config params to a given URL.
    """
    global config
    host_url = urllib.parse.urlparse(url)
    if VERBOSE:
        print("SET HOST URL URLPARSE : Protocol = %s" % host_url.scheme)
        print("SET HOST URL URLPARSE : Server = %s" % host_url.hostname)
        print("SET HOST URL URLPARLE : Port = %s" % host_url.port)
        print("SET HOST URL URLPARSE : Path = %s" % host_url.path)
    config.set('Connection', 'protocol', host_url.scheme)
    config.set('Connection', 'server', host_url.hostname)
    if host_url.scheme == 'https' and host_url.port is None:
        config.set('Connection', 'port', '443')
    elif host_url.scheme == 'http' and host_url.port is None:
        config.set('Connection', 'port', '80')
    else:
        config.set('Connection', 'port', str(host_url.port))
    if host_url.path is None:
        config.set('Connection', 'path', '/')
    else:
        config.set('Connection', 'path', str(host_url.path.rstrip('/') + '/'))
    if VERBOSE:
        for (key, val) in config.items('Connection'):
            print("SET HOST URL CONFIG ITEMS : %s=%s" % (key, val))
    return


def get_host_url():
    """
    This function returns the host_url string.
    """
    protocol = config.get('Connection', 'protocol')
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    path = config.get('Connection', 'path')
    host_url = '%s://%s:%s%s' % (protocol, server, port, path)
    if VERBOSE:
        print('HOST_URL : %s' % host_url)
    return(str(host_url))


def get_response(url='', payload=None, wsid=None, method='GET'):
    """
    Sends data to a given URL and returns the plain response.
    """
    jsessionid = get_session_id()
    host_url = get_host_url()
    ## Do all relevant string replacements for url here and only here!
    url = host_url + (url.replace(' ', '%20').replace('"', '%22'))
    req = urllib.request.Request(url)
    if payload is None:
        payload = '{}'.encode('utf-8')
    else:
        # payload = payload.encode('utf-8')
        payload = json.dumps(payload).encode('utf-8')
        print(payload)
    if VERBOSE:
        print("GET RESPONSE : Calling %s with method %s" % (url, method))
        print("GET RESPONSE : JSESSIONID = %s, wsid = %s" % (jsessionid, wsid))
        print("GET RESPONSE : Payload = %s" % payload)
    if method == 'GET':
        req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    else:
        req.add_header("Cookie", "JSESSIONID=%s; dmx_workspace_id=%s" % (jsessionid, wsid))
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: method
    try:
        response = urllib.request.urlopen(req, payload).read()
    except urllib.error.HTTPError as error_message:
        print('GET RESPONSE : Request Data Error: '+str(error_message))
        sys.exit(1)
    else:
        if VERBOSE:
            print("GET RESPONSE : TYPE = %s, len = %s" % (type(response), len(response)))
        if len(response)==0 and method=='POST':
            if VERBOSE:
                print('GET RESPONSE : return "OK" (%s)' % method)
            return("OK")
        elif len(response)!=0 and method=='DELETE':
            if VERBOSE:
                print('GET RESPONSE : return "OK" (%s)' % method)
            return("OK")
        else:
            response=check_response(response)
            return(response)

def get_session_id():
    """
    Creates an initial session and returns the session id.
    """
    global JSESSIONID
    if not JSESSIONID:
        if VERBOSE:
            print("GET_SESSION_ID : get new id for user %s" %
                  config.get('Credentials', 'authname'))
        host_url = get_host_url()
        url = host_url + 'core/topic/0'
        if VERBOSE:
            print("GET_SESSION_ID : url = %s" % url)
        req = urllib.request.Request(url)
        base_64_string = get_base_64()
        req.add_header("Authorization", "Basic %s" % base_64_string)
        req.add_header("Content-Type", "application/json")
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        try:
            opener.open(req)
        except urllib.request.HTTPError as error_message:
            print('Get Session ID Error: '+str(error_message))
        else:
            for cookie in cookie_jar:
                if cookie.name == "JSESSIONID":
                    JSESSIONID = cookie.value
        if VERBOSE:
            print("JSESSIONID: %s" % JSESSIONID)
    else:
        if VERBOSE:
            print("GET_SESSION_ID : use existing id")
    return(JSESSIONID)


def read_request(url):
    """
    Reads the data from a given URL.
    """
    ## TODO
    ## Replace read_request with get_response
    ##
    if VERBOSE:
        print("READ REQUEST : url = %s" % url)
    response = get_response(url)
    return(response)


def write_request(url, payload=None, workspace=None, method='POST', expect_json=True):
    """
    Writes the data to a given URL.
    """
    ## TODO
    ## Replace write_request with get_response
    ##
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    wsid = get_ws_id(workspace)
    if VERBOSE:
        print("WRITE REQUEST : workspace = %s has wsid = %s" % (workspace, wsid))
    response = get_response(url, payload, wsid, method)
    return(response)


def delete_request(url):
    """
    Sends the request with method 'DELETE'.
    """
    if VERBOSE:
        print("DELETE REQUEST : url = %s" % url)
    response = get_response(url, method='DELETE')
    return(response)


def get_ws_id(workspace):
    """
    This function gets the workspace ID for a workspace by its name.
    It's much faster to get it by its uri, if present.
    """
    global wsid_cache
    if workspace in wsid_cache:
        if VERBOSE:
            print("GET_WS_ID : Workspace ID for workspace %s from cache: %s" % (workspace, wsid_cache[workspace]))
        return wsid_cache[workspace]
    ## else
    if VERBOSE:
        print("GET_WS_ID : Searching Workspace ID for workspace %s" % workspace)
    url = ('core/topics/query/"%s"?topicTypeUri=dmx.workspaces.workspace_name'
           % workspace)
    ## find the workspace_name in the result
    response = get_response(url)
    topics = response["topics"]
    for topic in topics:
        ## find the workspace_name in the result
        if topic['typeUri'] == 'dmx.workspaces.workspace_name':
            wsnameid = (topic['id'])
            break
    if VERBOSE:
        print("GET WS ID : wsnameid = %s" % wsnameid)
    url = ('core/topic/%s/related-topics'
           '?assocTypeUri=dmx.core.composition&myRoleTypeUri='
           'dmx.core.child&othersRoleTypeUri=dmx.core.parent&'
           'othersTopicTypeUri=dmx.workspaces.workspace' %
           str(wsnameid))
    response = get_response(url)
    ## TODO - check if still needed:
    ## The following is a workarround to fix
    ## Pylint3 Error: Sequence index is not an int, slice,
    ## or instance with __index__ (invalid-sequence-index)
    topic = json.loads(json.dumps(response[0]))
    topic_id = topic['id']
    wsid_cache[workspace] = topic_id
    if VERBOSE:
        print("WS ID = %s" % topic_id)
    return(topic_id)


def get_topicmap_id(tm_name):
    """
    This function gets the Topic ID for a topicmap by its name.
    It's much faster to get it by its uri, if present.
    """
    if VERBOSE:
        print("GET_TOPICMAP_ID : Searching Topic ID for topicmap %s" % tm_name)
    url = ('core/topics/query/"%s"?topicTypeUri=dmx.topicmaps.topicmap_name'
           % tm_name)
    ## find the workspace_name in the result
    response = get_response(url)
    topics = response["topics"]
    for topic in topics:
        ## find the workspace_name in the result
        if topic['typeUri'] == 'dmx.topicmaps.topicmap_name':
            tm_name_id = (topic['id'])
            # print('topicmap_id=', topic_id)
            break
    if VERBOSE:
        print("GET_TOPICMAP_ID : tm_name_id = %s" % tm_name_id)
    url = ('core/topic/%s/related-topics'
           '?assocTypeUri=dmx.core.composition&myRoleTypeUri='
           'dmx.core.child&othersRoleTypeUri=dmx.core.parent&'
           'othersTopicTypeUri=dmx.topicmaps.topicmap' %
           str(tm_name_id))
    response = get_response(url)
    ## TODO - check if still needed:
    ## The following is a workarround to fix
    ## Pylint3 Error: Sequence index is not an int, slice,
    ## or instance with __index__ (invalid-sequence-index)
    topic = json.loads(json.dumps(response[0]))
    topic_id = topic['id']
    if VERBOSE:
        print("WS ID = %s" % topic_id)
    if VERBOSE:
        print("MAP ID = %s" % topic_id)
    return(topic_id)


def create_user(dm_user='testuser', dm_pass='testpass'):
    """
    This function creates a new user on the server.
    """
    ## check if username exits
    users = list(get_items('dmx.accesscontrol.username').values())
    if VERBOSE:
        print("CREATE USER : users=%s" % users)
    if dm_user in users:
        print("ERROR! User '%s' exists." % dm_user)
        sys.exit(1)
    else:
        ## create user
        url = 'access-control/user-account'
        hash_object = hashlib.sha256(dm_pass.encode('UTF-8'))
        dm_pass = '-SHA256-'+hash_object.hexdigest()
        payload = {'username' : dm_user, 'password' : dm_pass}
        topic_id = write_request(url, payload)["id"]
        if VERBOSE:
            print("CREATE USER : topic_id = %s" % topic_id)
            print("CREATE USER : New user '%s' was created with topic_id %s." % (dm_user, topic_id))
        return(topic_id)


def create_topicmap(tm_name, tm_type='dmx.topicmaps.topicmap', workspace=None):
    """
    This function creates a new topicmap on the server.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    ## check if topicmap exits (globally!!!)
    maps = list(get_items('dmx.topicmaps.topicmap').values())
    if VERBOSE:
        print("CREATE TOPICMAP : %s" % tm_name)
        print("CREATE TOPICMAP : maps = %s" % maps)
    if tm_name in maps:
        topic_id = get_topicmap_id(tm_name)
        if VERBOSE:
            print("INFO: Map '%s' exists (ID %s)." % (tm_name, topic_id))
    else:
        url = ('topicmaps?name=%s&topicmapTypeUri=%s' % (tm_name, tm_type))
        ## for the moment, this requires an empty json string exactly like this
        payload = json.loads('{"": ""}')
        topic_id = write_request(url, payload, workspace)["id"]
        if VERBOSE:
            print("New topicmap '%s' was created with topic_id %s." % (tm_name, topic_id))
    return(topic_id)


def create_ws(workspace, ws_type, uri=''):
    """
    This function creates a workspace with workspace uri
    (needed for id) on the server.
    """
    ## `uri` is optional.
    if not uri:
        uri = workspace.lower()+'.uri'
    url = ('workspaces?name=%s&uri=%s&sharingModeUri=dmx.workspaces.%s' %
           (workspace, uri, ws_type))
    topic_id = write_request(url, expect_json=True)["id"]
    return(topic_id)


def create_member(workspace=None, dm_user='username'):
    """
    This function creates a user memebrship association for
    the workspace on the server.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    if VERBOSE:
        print("CREATE MEMBER : Creating Workspace membership for user %s in %s" %
              (dm_user, workspace))
    wsid = get_ws_id(workspace)
    url = ('access-control/user/%s/workspace/%s' %
           (dm_user, wsid))
    response = write_request(url, expect_json=False)
    return(response)


def create_note(title, body, workspace=None):
    """
    This function creates a new note with text body
    in the workspace on the server.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    if VERBOSE:
        print("CREATE NOTE : Creating a new note %s with text body %s in workspace %s" %
              (title, body, workspace))
    url = 'core/topic/'
    payload = json.dumps(
        {
            "children": {
                "dmx.notes.text": body,
                "dmx.notes.title": title
            },
            "typeUri": "dmx.notes.note"
        }
    )
    payload = json.loads(payload)
    if VERBOSE:
        print("NEW NOTE: %s" % payload)
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def send_data(payload, workspace=None):
    """
    This function sends the topics according to payload to
    the workspace name on the server.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    if VERBOSE:
        print("SEND DATA: sending data to workspace '%s'" % workspace)
    url = 'core/topic/'
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def create_assoc(payload, workspace=None):
    """
    This function sends the assocs according to payload to
    the workspace name on the server.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    if VERBOSE:
        print("SEND DATA: sending data to workspace '%s'" % workspace)
    url = 'core/assoc/'
    assoc_id = write_request(url, payload, workspace)["id"]
    return(assoc_id)


def send_post(url, workspace=None):
    """
    This function sends a POST request to custom (a plugin) REST resource.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    if VERBOSE:
        print("SEND POST : Sending POST to '%s' in Workspace %s" %
              (url, workspace))
    response = write_request(url, workspace)
    return(response)


def reveal_topic(workspace, map_id, topic_id, x_val=0, y_val=0, pinned=False):
    """
    This function reveales a topic (id) on a topicmap (id) at
    position x, y, pinned or unpinned
    """
    if pinned:
        pinned = str('true')
    else:
        pinned = str('false')
    url = ('topicmaps/%s/topic/%s' % (map_id, topic_id))
    payload = json.loads(
        '{ "dmx.topicmaps.x": %s, "dmx.topicmaps.y": %s, \
        "dmx.topicmaps.visibility": true, "dmx.topicmaps.pinned": %s }'
        % (x_val, y_val, pinned)
    )
    response = write_request(url, payload, workspace, expect_json=False)
    return(response)


def reveal_assoc(map_id, assoc_id):
    """
    This function reveales an assoc (id) on a topicmap (id)
    """
    # payload = {"": ""}
    url = ('topicmaps/%s/assoc/%s' % (map_id, assoc_id))
    payload = json.loads(
        '{ "dmx.topicmaps.visibility": true, "dmx.topicmaps.pinned": false }'
    )
    response = write_request(url, payload, expect_json=False)
    return(response)



def import_vcard(vcard_file, workspace=None):
    """
    This function imports data from a vcard file and creates a person topic.
    """
    ## if workspace in None, the default workspace should come from config:
    if workspace is None:
        workspace = config.get('Connection', 'workspace')
    version = platform.python_version().split('.')
    if VERBOSE:
        print("PYTHON VERSION : %s" % version)
    if int(version[0]) < 3 or int(version[1]) < 6:
        print('SORRY! VCARD option requires Python 3.6 or higher.')
        ## make pylint3 happy:
        ModuleNotFoundError = ''
        sys.exit(0)
    else:
        try:
            import vobject
        except ImportError as err:
            print(err)
            print('Please install module python3-vobject')
            sys.exit(0)

    payload = read_file(vcard_file)
    # ~ if VERBOSE:
        # ~ print("VCARD FILE:\n%s" % payload)
    vcard = vobject.readOne(payload)
    if VERBOSE:
        vcard.prettyPrint()

    ## firstname
    first_name = ''
    try:
        first_name = vcard.n.value.given
    except:
        pass

    ## lastname
    last_name = ''
    try:
        last_name = vcard.n.value.family
    except:
        pass

    ## tel
    tel_mobile = ''
    tel_home = ''
    tel_work = ''
    try:
        for tel in vcard.contents["tel"]:
            if tel.params["TYPE"] in [
                    ["CELL", "VOICE"],
                    ["VOICE", "CELL"],
                    ["CELL"],
                    ["MOBILE"],
                    ["MOBIL"]
                ]:
                tel_mobile = tel.value
            if tel.params["TYPE"] in [
                    ["HOME", "VOICE"],
                    ["VOICE", "HOME"],
                    ["HOME"],
                    ["VOICE"]
                ]:
                tel_home = tel.value
            if tel.params["TYPE"] in [
                    ["WORK", "VOICE"],
                    ["VOICE", "WORK"],
                    ["WORK"]
                ]:
                tel_work = tel.value
    except KeyError:
        pass

    ## bday
    birthday = [None] * 3 # create an empty list with 3 fields
    birthday[0] = '' # year
    birthday[1] = '' # month
    birthday[2] = '' # day
    try:
        bday = vcard.bday.value
    except AttributeError:
        pass
    else:
        birthday = bday.split('-')

    ## note
    try:
        note = vcard.note.value
    except:
        note = ''

    ## address ##
    ## home
    adr_home_street = ''
    adr_home_code = ''
    adr_home_city = ''
    adr_home_region = ''
    adr_home_country = ''
    ## work
    adr_work_street = ''
    adr_work_code = ''
    adr_work_city = ''
    adr_work_region = ''
    adr_work_country = ''
    try:
        for adr in vcard.contents["adr"]:
            if adr.params["TYPE"] in [["HOME"], ["PRIVATE"]]:
                adr_home_street = adr.value.street
                adr_home_code = adr.value.code
                adr_home_city = adr.value.city
                adr_home_region = adr.value.region
                adr_home_country = adr.value.country
            if adr.params["TYPE"] in [["WORK"], ["OFFICE"]]:
                adr_work_street = adr.value.street
                adr_work_code = adr.value.code
                adr_work_city = adr.value.city
                adr_work_region = adr.value.region
                adr_work_country = adr.value.country
    except KeyError:
        pass

    ## email
    emails_to_create = []
    try:
        for email in vcard.contents["email"]:
            email_adr = email.value.lower()
            if hasattr(email, "type_param"):
                email_adr_type = email.type_param.lower()
                if email_adr_type == "internet":
                    emails_to_create.append({"value": email_adr})
    except KeyError:
        pass
    emails_to_create = json.loads(json.dumps(emails_to_create))

    ## create payload
    url = 'core/topic/'
    payload = json.dumps(
        {
            "typeUri": "dmx.contacts.person",
            "children": {
                "dmx.datetime.date#dmx.contacts.date_of_birth": {
                    "dmx.datetime.day": birthday[2],
                    "dmx.datetime.month": birthday[1],
                    "dmx.datetime.year": birthday[0]
                },
                "dmx.contacts.person_description": note,
                "dmx.contacts.email_address": emails_to_create,
                "dmx.contacts.person_name": {
                    "dmx.contacts.first_name": first_name,
                    "dmx.contacts.last_name": last_name
                },
                "dmx.contacts.phone_number#dmx.contacts.phone_entry": [
                    {
                        "value": tel_home,
                        "assoc": {
                            "children": {
                                "dmx.contacts.phone_label": "ref_uri:dmx.contacts.home_phone"
                            }
                        }
                    },
                    {
                        "value": tel_work,
                        "assoc": {
                            "children": {
                                "dmx.contacts.phone_label": "ref_uri:dmx.contacts.work_phone"
                            }
                        }
                    },
                    {
                        "value": tel_mobile,
                        "assoc": {
                            "children": {
                                "dmx.contacts.phone_label": "ref_uri:dmx.contacts.mobile"
                            }
                        }
                    }
                ],
                "dmx.contacts.address#dmx.contacts.address_entry": [
                    {
                        "children": {
                            "dmx.contacts.street": adr_home_street,
                            "dmx.contacts.postal_code": adr_home_code,
                            "dmx.contacts.city": adr_home_city,
                            "dmx.contacts.region": adr_home_region,
                            "dmx.contacts.country": adr_home_country
                        },
                        "assoc": {
                            "children": {
                                "dmx.contacts.address_label": {
                                    "value": "ref_uri:dmx.contacts.home_address"
                                }
                            }
                        }
                    },
                    {
                        "children": {
                            "dmx.contacts.street": adr_work_street,
                            "dmx.contacts.postal_code": adr_work_code,
                            "dmx.contacts.city": adr_work_city,
                            "dmx.contacts.region": adr_work_region,
                            "dmx.contacts.country": adr_work_country
                        },
                        "assoc": {
                            "children": {
                                "dmx.contacts.address_label": "ref_uri:dmx.contacts.work_address"
                            }
                        }
                    }
                ]
            }
        }

    )
    payload = json.loads(payload)
    if VERBOSE:
        print("IMPORT VCARD : new person: %s" % payload)
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def get_topic(topic_id):
    """
    This function fetches the data according to datapath from
    the server and returns the data.
    """
    url = ('core/topic/%s?children=true' % topic_id)
    return(read_request(url))


def get_data(datapath):
    """
    This function fetches the data according to datapath from
    the server and returns the data.
    """
    url = ('core/%s?children=true' % datapath)
    return(read_request(url))


def get_items(topictype):
    """
    This function searches for topics of the specified topictype and
    returns the items, if exists
    """
    dm_items = {} # for dictionary
    data = get_data('topics/type/%s' % topictype)
    try:
        total = len(data)
    except:
        print("Error while trying to get items.")
        total = 0
        pass
    if total > 0:
        for i in range(total):
            dm_items.update(
                {(data[i]["id"]): (data[i]["value"])}
            )
    return(dm_items)


def get_related(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('core/topic/%s/related-topics?' % topic_id)
    return(read_request(url))


def get_creator(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('access-control/object/%s/creator' % topic_id)
    return(read_request(url))


def get_modifier(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('access-control/object/%s/modifier' % topic_id)
    return(read_request(url))


def get_topic_ws(topic_id):
    """
    This function fetches the topic's workspace id according to topic_id from
    the server and returns the data.
    """
    url = ('workspace/object/%s' % topic_id)
    return(read_request(url))


def get_ws_owner(workspace_id):
    """
    This function fetches the owner of a workspace id from
    the server and returns the data.
    """
    url = ('access-control/workspace/%s/owner' % workspace_id)
    return(read_request(url))


def delete_topic(topic_id):
    """
    This function deletes a topic by its id from the server.
    """
    if VERBOSE:
        print("DELETE TOPIC : deleting topic with id '%s'" % topic_id)
    url = ('core/topic/%s' % topic_id)
    response = delete_request(url)
    return(response)


def pretty_print(data):
    """
    This function just prints the json data in a pretty way. :)
    """
    print(json.dumps(data, indent=3, sort_keys=True))
    return


def main(args):
    """
    ToDo:
    # change_password(user, password, 'new_pass')
    """
    global VERBOSE    # verbose mode (True|False)
    global JSESSIONID # can be entered via command line
    global config     # the gloabl server access params

    parser = argparse.ArgumentParser(
        description='This is a Python script \
        for DMX by Juergen Neumann <juergen@dmx.systems>. It is free \
        software licensed under the GNU General Public License Version 3 \
        and comes with ABSOLUTELY NO WARRANTY.'
    )
    parser.add_argument(
        '-b', '--by_type',
        type=str,
        help='Get all items of a TopicType by its topic.type.uri.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-B', '--note_body',
        type=str,
        help='Provide a text for the body of a new note.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-c', '--config_properties',
        type=str,
        help='Reads config data from dmx config properties file.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-C', '--create_user',
        help='Create a user with -u username and -p password.',
        action='store_true',
        required=False,
        default=None
    )
    parser.add_argument(
        '-d', '--delete_topic',
        type=int,
        help='Detele a topic by id.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='Creates a new topic from json file in a specified workspace \
              with -f file name and -w workspace name.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-i', '--topic_id',
        type=str,
        help='Provide a numerical topic id.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-J', '--JSESSIONID',
        type=str,
        help='Provide an existing JSESSIONID to authenticate. (Do not login again.)',
        required=False,
        default=None
    )
    parser.add_argument(
        '-l', '--login',
        help='Login as -u user with password -p instead of admin.',
        action='store_true',
        required=False,
        default=None
    )
    parser.add_argument(
        '-m', '--membership',
        help='Create a new workspace membership with -w workspace name \
              and -n username of new member.',
        action='store_true',
        required=False,
        default=None
    )
    parser.add_argument(
        '-M', '--create_topicmap',
        type=str,
        help='Create a new topicmap with given name in a specified workspace \
              with -M map name and -w workspace name.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-n', '--new_member',
        type=str,
        help='Provide the username of new member.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-N', '--create_note',
        type=str,
        help='Create a new note with given title and body in a specified workspace \
              with -N title, -B body and and -w workspace name.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-o', '--topicmap_id',
        type=str,
        help='Provide a numerical topicmap id.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-p', '--password',
        type=str,
        help='Provide a password.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-r', '--get_related',
        type=int,
        help='Get all related items of a topic id.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-R', '--reveal_topic',
        help='Reveal a topic on a topicmap in a specified workspace \
              with -w workspace name.',
        action='store_true',
        required=False,
        default=None
    )
    parser.add_argument(
        '-P', '--topicmap_pinned',
        type=str,
        help='Provide a boolen (True|False) if topic should be pinned \
              on topicmap. (default: False)',
        required=False,
        default=None
    )
    parser.add_argument(
        '-s', '--get_session_id',
        help='Get a valid session id.',
        action='store_true',
        required=False,
        default=None
    )
    parser.add_argument(
        '-S', '--ws_sharing_mode',
        type=str,
        help='Set the sharing mode of the new workspace.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-SP', '--send_post',
        help='Sends simple POST request to given resource endpoint. \
              Use in conjunction with -w for e.g. triggering imports.',
        default=None
    )
    parser.add_argument(
        '-t', '--get_topic',
        type=int,
        help='Get all data of a topic id.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-T', '--ws_type',
        type=str,
        help='DEPRICATED! Use -S instead. (Define Type of the new workspace.)',
        required=False,
        default=None
    )
    parser.add_argument(
        '-u', '--user',
        type=str,
        help='Provide a username.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-U', '--URL',
        type=str,
        help='Provide the host URL.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-v', '--VERBOSE',
        help='Enable VERBOSE mode.',
        action='store_true',
        required=False,
        default=None
    )
    parser.add_argument(
        '-V', '--import_vcard',
        type=str,
        help='Create a new person topic in a specified workspace \
              from given vcard file, -V filename and and -w workspace name.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-w', '--workspace',
        type=str,
        help='Create a new workspace by name with -T type or just the \
              name of a workspace.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-x', '--topicmap_x',
        type=str,
        help='Provide a numerical x position for topic on topicmap.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-y', '--topicmap_y',
        type=str,
        help='Provide a numerical y position f topic on topicmap.',
        required=False,
        default=None
    )
    parser.add_argument(
        '-Y', '--yes',
        help='Imply "yes" to any question (for script mode).',
        action='store_true',
        required=False,
        default=None
    )

    args = parser.parse_args()
    argsdict = vars(args)

    ##########################################
    ## action on arguments (order matters!) ##
    ##########################################
    ##
    ## These functions shall not include logic, but only check and interpret the
    ## arguments and then call a funtion (ideally named like argument) to do
    ## the computing.
    ##
    ## enable VERBOSE mode
    if argsdict['VERBOSE']:
        VERBOSE = True

    ## create initial config instance from ConfigParser with defaults
    create_default_config()

    ## read config_properties must be first, because it sets the default setting for config
    ## unless ALL required params are entered via command line.
    if (
        argsdict['URL'] and
        argsdict['login'] and
        argsdict['user'] and
        (argsdict['password'] or argsdict['password']=="")
    ):
        pass
    elif argsdict['config_properties']:
        read_dmx_config_properties_file(argsdict['config_properties'])
    else:
        read_default_config_file()

    ## if a JESSIONID is entered via command line, then use it.
    if argsdict['JSESSIONID']:
        JSESSIONID = (argsdict['JSESSIONID'])

    ## if a URL. is entered via command line, then use it.
    if argsdict['URL']:
        if argsdict['URL'] is not None:
            set_host_url(argsdict['URL'])
        # else:
        #    ## Todo: why do we refer to username or workspace name here at all?
        #    print("ERROR! Missing username of new member or missing workspace name.")

    ## login is next, as one may want to manually set who logs in
    if argsdict['login']:
        if (argsdict['user'] != None) and (argsdict['password'] != None):
            config.set('Credentials', 'authname', argsdict['user']) # usualy the admin
            config.set('Credentials', 'password', argsdict['password']) # usualy the admin password
        else:
            print("ERROR! Missing username and/or password.")

    if argsdict['file']:
        ##
        ## Todo: This function needs rewrinting! The logic of importing data from
        ## json file should be in a separate function.
        ##
        if VERBOSE:
            print("ARGSDICT FILE: Importing json data from file %s" % (argsdict['file']))
        payload = read_file(str(argsdict['file']))
        if VERBOSE:
            print("JSON DATA FROM FILE:\n%s" % payload)
        payload = json.loads(payload)
        payload_len = len(payload)
        if argsdict['workspace']:
            if payload_len > 0:
                if VERBOSE:
                    print("WORKSPACE: %s" % argsdict['workspace'])
                data = send_data(payload, argsdict['workspace'])
                print(data)
            else:
                print("ERROR! Missing data in file %s" % (argsdict['file']))
        else:
            print("ERROR! Missing workspace declaration.")

    if argsdict['import_vcard']:
        if VERBOSE:
            print("Importing vcard data from file %s" % (argsdict['import_vcard']))
        if argsdict['workspace']:
            data = import_vcard(
                argsdict['import_vcard'],
                argsdict['workspace']
            )
            print(data)
        else:
            print("ERROR! Missing workspace declaration.")

    if argsdict['create_user']:
        if (argsdict['user'] and argsdict['password']):
            data = create_user(argsdict['user'], argsdict['password'])
            print(data)
        else:
            print("ERROR! Missing username or password.")

    if argsdict['create_topicmap']:
        ## TODO
        ## still missing: set type of new map via option (default is topicmap)
        ##
        argsdict['m_type'] = 'dmx.topicmaps.topicmap'
        if (argsdict['create_topicmap'] != None) and (argsdict['workspace'] != None):
            data = create_topicmap(
                argsdict['create_topicmap'], argsdict['m_type'], argsdict['workspace']
            )
            print(data)
        else:
            print("ERROR! Missing name of new topicmap or missing workspace name.")

    if argsdict['create_note']:
        if argsdict['note_body'] and argsdict['workspace']:
            data = create_note(
                argsdict['create_note'], argsdict['note_body'], argsdict['workspace']
            )
            print(data)
        else:
            print("ERROR! Missing body of new note or missing workspace name.")

    if argsdict['by_type']:
        data = get_items(argsdict['by_type'])
        pretty_print(data)

    if argsdict['get_related']:
        data = get_related(argsdict['get_related'])
        pretty_print(data)

    if argsdict['get_topic']:
        data = get_topic(argsdict['get_topic'])
        pretty_print(data)

    if argsdict['workspace'] and (argsdict['ws_type']) and not argsdict['membership']:
        ## TODO - chekc if still true:
        ## Does not work with 'private' for now!
        ##
        if argsdict['ws_type'] in ["confidential", "collaborative", "public", "common"]:
            if VERBOSE:
                print("Creating new %s workspace %s" %
                      (argsdict['ws_type'], argsdict['workspace']))
            data = create_ws(argsdict['workspace'], argsdict['ws_type'])
            print(data)
        elif argsdict['ws_type'] == "private":
            print("Sorry! %s is not working yet via scripting." % argsdict['ws_type'])
        else:
            print("ERROR! %s is not a valid workshop type." % argsdict['ws_type'])

    if argsdict['get_session_id']:
        data = get_session_id()
        print(data)

    if argsdict['membership']:
        if (argsdict['workspace'] != None) and (argsdict['new_member'] != None):
            data = create_member(argsdict['workspace'], argsdict['new_member'])
            print(data)
        else:
            print("ERROR! Missing username of new member or missing workspace name.")

    if argsdict['send_post']:
        data = send_post(argsdict['send_post'], argsdict['workspace'])
        pretty_print(data)

    if argsdict['delete_topic']:
        data = get_topic(argsdict['delete_topic'])
        if (not (argsdict['yes']) and query_yes_no(
                "Are you sure you want to delete topic id %s with value \"%s\"" %
                (argsdict['delete_topic'], data['value']))):
            print('yes')
            data = delete_topic(argsdict['delete_topic'])
            print(data)
        elif argsdict['yes']:
            data = delete_topic(argsdict['delete_topic'])
            print(data)
        else:
            print('no')

    if argsdict['reveal_topic']:
        if (
                (argsdict['workspace'] != None) and
                (argsdict['topic_id'] != None) and
                (argsdict['topicmap_id'] != None)
            ):
            workspace = argsdict['workspace']
            topicmap_id = argsdict['topicmap_id']
            topic_id = argsdict['topic_id']
            if argsdict['topicmap_x']:
                topicmap_x = argsdict['topicmap_x']
            else:
                topicmap_x = 20
            if argsdict['topicmap_y']:
                topicmap_y = argsdict['topicmap_y']
            else:
                topicmap_y = 20
            if argsdict['topicmap_pinned'] == "True":
                topicmap_pinned = argsdict['topicmap_pinned']
            else:
                topicmap_pinned = False
            data = reveal_topic(
                workspace,
                topicmap_id,
                topic_id,
                topicmap_x,
                topicmap_y,
                topicmap_pinned
            )
            print(data)
        else:
            print('ERROR! Missing topic_id or missing topicmap_id \
                   or missing workspace name.')

    if len(sys.argv) < 2:
        parser.print_usage()
        print('Use -h or --help for more information.')
        parser.exit(1)

    ## How long did it take?
    try:
        start_time
    except NameError:
        pass
    else:
        end_time = timer()
        if VERBOSE:
            print("MAIN : Elapsed time:", timedelta(seconds=end_time-start_time))
    if VERBOSE:
        print("MAIN : Exit.")



if __name__ == '__main__':
    start_time = timer()
    if sys.version_info < (3, 0):
        print('ERROR! This program requires python version 3 or higher.')
        sys.exit(1)
    else:
        sys.exit(main(sys.argv))


## END.
