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

from __future__ import print_function

__author__ = 'Juergen Neumann <juergen@dmx.systems>'
__copyright__ = 'Copyright 2019, DMX Systems <https://dmx.systems>'
__license__ = 'GPL'
__version__ = '3'
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

## define global variables
config = []       # The data required to access and login to dmx
verbose = False   # verbose mode (True|False)
jsessionid = ""   # The session ID


def read_config_file():
    """
    Put this content in your dmx.cfg:

    [Credentials]
    authname = admin
    password =

    [Connection]
    server = localhost
    port = 8080
    workspace = DMX
    """
    global config

    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    config_file_name = 'dmx.cfg'
    config_file = os.path.join(script_dir, config_file_name)
    ## if empty or missing, use these parameters
    # ~ config = configparser.SafeConfigParser()
    config = configparser.SafeConfigParser()
    # config.read(DEFAULT_CONFIG)
    if os.path.isfile(config_file):
        config.read(config_file)
    else:
        print("ERROR! Config file %s not found." % config_file)
        sys.exit(1)


def read_dmx_config(config_properties):
    """
    Reads the configuration data from '/path/to/dmx/config.properties'
    and overwrites the config settings with new values.
    """
    global config
    config = configparser.SafeConfigParser()
    dmx_params = {}
    dmx_config_file = str(config_properties)
    if os.access(dmx_config_file, os.R_OK):
        with open(dmx_config_file) as f_in:
            lines = [_f for _f in (line.rstrip() for line in f_in) if _f]
    for ln in lines:
        if not ln[0] in ('', ' ', '#', ';'):
            try:
                key, val = ln.strip().replace(" ", "").split('=', 1)
            except ValueError:
                print("INFO: No value found for %s in %s" % (key, dmx_config_file))
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
            print("ERROR! Could not read config file %s." % dmx_config_file)
            sys.exit(0)

    return


def check_payload(payload):
    """
    This function checks the payload to be send to server and makes sure
    it is a valid json format.
    """
    if verbose:
        print("CHECK_PAYLOAD: %s" % payload)
        print("PAYLOAD TYPE = %s" % type(payload))
    ## make sure payload is a dict before we send it
    ## Test if the payload is a valid json object and get it sorted.
    try:
        payload = json.loads(json.dumps(payload, indent=3, sort_keys=True))
    except:
        print("ERROR! Could not read Payload. Not JSON?")
        sys.exit(1)
    else:
        if verbose:
            print("LenPayload: %s" % len(payload))
            pretty_print(payload)
        return(payload)

    # ~ if isinstance(payload, str):
        # ~ payload=json.loads(payload)
        # ~ if verbose:
            # ~ print("Retyped payload to 'dict': %s" % payload)
    # ~ return(payload)


# ~ def import_payload(json_filename, default="payload.json"):
    # ~ """
    # ~ Here we open the file and import the content as json.
    # ~ """
    # ~ if verbose:
        # ~ print("Reading file %s" % (json_filename))
    # ~ with open(json_filename, 'r') as data_file:
        # ~ payload = json.load(data_file)
    # ~ return(payload)


def read_file(filename, default="payload.file"):
    """
    Here we open the file and read the content.
    """
    if verbose:
        print("Reading file %s" % (filename))
    with open(filename, 'r') as data_file:
        data = data_file.read()
    data_file.close()
    if verbose:
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


def get_base64():
    """
    This function returns the authentication string for the user against DM
    """
    authname = config.get('Credentials', 'authname') # usualy the admin user
    password = config.get('Credentials', 'password') # usualy the admin password
    authstring = bytes((str(authname + ':' + password)), 'UTF-8')
    base64string = (base64.b64encode(authstring)).decode('UTF-8')
    return(base64string)


def get_session_id():
    """
    Creates an initial session and returns the session id.
    """
    global jsessionid
    if not jsessionid:
        server = config.get('Connection', 'server')
        port = config.get('Connection', 'port')
        url = 'http://%s:%s/core/topic/0' % (server, port)
        req = urllib.request.Request(url)
        req.add_header("Authorization", "Basic %s" % get_base64())
        req.add_header("Content-Type", "application/json")
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        try:
            test_url = opener.open(req)
        except urllib.request.HTTPError as e:
            print('Get Session ID Error: '+str(e))
        else:
            for c in cj:
                if c.name == "JSESSIONID":
                    jsessionid = c.value
    return(jsessionid)


def read_request(url):
    """
    Reads the data from a given URL.
    """
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/%s' % (server, port, url)
    jsessionid = get_session_id()
    if verbose:
        print("Read Data %s" % url)
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    try:
        response = (json.loads(urllib.request.urlopen(req).read().decode('UTF-8')))
    except urllib.error.HTTPError as e:
        print('Read Data Error: '+str(e))
    except ValueError:
        print('WARNING! No JSON Object found.')
        try:
            response = urllib.request.urlopen(req).read()
        except urllib.error.HTTPError as e:
            print('Read Data Error: '+str(e))
        else:
            if verbose and response:
                print("RESPONSE TYPE = %s" % type(response))
                # ~ print(response)
            return(response)
    else:
        if verbose:
            print("RESPONSE TYPE = %s" % type(response))
            pretty_print(response)
        return(response)


def write_request(url, payload=None, workspace='DMX', method='POST', expect_json=True):
    """
    Writes the data to a given URL.
    """
    ### The wsid is used for the Cockie here!
    ### Not for the payload - this might be confusing
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/%s' % (server, port, url)
    jsessionid = get_session_id()
    if verbose:
        print("Write Data %s" % url)
    wsid = get_ws_id(workspace)
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s; dmx_workspace_id=%s" % (jsessionid, wsid))
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: method
    if payload:
        payload = check_payload(payload)
    if payload and expect_json:
        if verbose:
            print('Sending with payload. Expecting JSON response.')
        if payload == {"": ""}:
            ## This needs fixing. It is a workarround to recevie empty JSON as
            ## required in 'create_topicmap' function.
            payload = {}
        try:
            response = (
                json.loads(urllib.request.urlopen(
                    req, (json.dumps(payload)).encode('UTF-8')
                ).read().decode('UTF-8'))
            )
        except urllib.error.HTTPError as e:
            print('Write Data Error: '+str(e))
            json_error = {"id": "FAILED!"}
            response = json.loads(json.dumps(json_error))
            if verbose:
                print("RESPONSE: %s" % response)
            return(response)
        except json.decoder.JSONDecodeError as e:
            print('JSON Decoder Error: '+str(e))
        else:
            if verbose:
                print("RESPONSE TYPE = %s" % type(response))
                pretty_print(response)
            return(response)
    elif payload:
        if verbose:
            print('Sending data with payload. Not expecting JSON response.')
        if payload == {"": ""}:
            ## This needs fixing. It is a workarround to recevie empty JSON as
            ## required in 'create_topicmap' function.
            payload = {}
        try:
            response = (
                urllib.request.urlopen(
                    req, (json.dumps(payload)).encode('UTF-8')
                ).read().decode('UTF-8')
            )
            # ~ response = (urllib.request.urlopen(req, payload).read())
        except urllib.error.HTTPError as e:
            print('Write Data Error: '+str(e))
        except json.decoder.JSONDecodeError as e:
            print('JSON Decoder Error: '+str(e))
        else:
            if verbose:
                print("RESPONSE TYPE = %s" % type(response))
                # ~ print(response)
            return("OK")
    elif expect_json:
        if verbose:
            print('Sending data without payload. Expecting JSON response.')
        try:
            response = (json.loads(urllib.request.urlopen(req).read().decode('UTF-8')))
        except urllib.error.HTTPError as e:
            print('Write Data Error: '+str(e))
        except json.decoder.JSONDecodeError as e:
            print('JSON Decoder Error: '+str(e))
        else:
            response = json.loads(json.dumps(response))
            if verbose:
                print("RESPONSE TYPE = %s" % type(response))
                pretty_print(response)
            return(response)
    else:
        # This can be deleted, right?
        # if no payload
        if verbose:
            print('Got no payload. Got no expectation on response.')
        try:
            ## response = (json.loads(urllib.request.urlopen(req).read()))
            response = (urllib.request.urlopen(req).read().decode('UTF-8'))
        except urllib.error.HTTPError as e:
            print('Write Data Error: '+str(e))
        except json.decoder.JSONDecodeError as e:
            print('JSON Decoder Error: '+str(e))
        else:
            # is response json?
            try:
                response = json.loads(response)
            except:
                if verbose:
                    print("RESPONSE is not JSON")
                    print("RESPONSE TYPE = %s" % type(response))
                    # ~ print(response)
                return("OK")
            else:
                if verbose:
                    print("RESPONSE is JSON")
                    print("RESPONSE TYPE = %s" % type(response))
                    pretty_print(response)
                return(response)


def create_user(dm_user='testuser', dm_pass='testpass'):
    """
    This function creates a new user on the server.
    """
    # check if username exits
    users = list(get_items('dmx.accesscontrol.username').values())
    if verbose:
        print("USERS: %s" % users)
    if dm_user in users:
        print("ERROR! User '%s' exists." % dm_user)
        sys.exit(1)
    else:
        # create user
        url = 'accesscontrol/user_account'
        hash_object = hashlib.sha256(dm_pass.encode('UTF-8'))
        dm_pass = '-SHA256-'+hash_object.hexdigest()
        payload = {'username' : dm_user, 'password' : dm_pass}
        ## payload = json.dumps({'username' : dm_user, 'password' : dm_pass})
        # topic_id = write_request(url, payload)["id"]
        topic_id = write_request(url, payload)["id"]
        ## debug
        if verbose:
            print("TOPIC_ID = %s" % topic_id)
            print("New user '%s' was created with topic_id %s." % (dm_user, topic_id))
        return(topic_id)


def create_topicmap(tm_name, tm_type='dmx.topicmaps.topicmap', workspace='DMX'):
    """
    This function creates a new topicmap on the server.
    """
    # check if topicmap exits (globally!!!)
    maps = list(get_items('dmx.topicmaps.topicmap').values())
    if verbose:
        print("CREATE TOPICMAP: %s" % tm_name)
        print("TOPICMAPS: %s" % maps)
    if tm_name in maps:
        print("ERROR! Map '%s' exists." % tm_name)
        sys.exit(1)
    else:
        # url = ('topicmap?name="%s"&topicmap_type_uri="%s"&private=false' % (tm_name.replace(' ', '%20'), tm_type))
        url = ('topicmap?name=%s&topicmap_type_uri=%s' % (tm_name.replace(' ', '%20'), tm_type))
        # for the moment, this requires an empty json string exactly like this
        data = {"": ""}
        try:
            payload = json.loads(json.dumps(data, indent=3, sort_keys=True))
            if verbose:
                print("LenPayload: %s" % len(payload))
        except:
            print("ERROR! Could not read Payload. Not JSON?")
            sys.exit(1)

        ## debug
        if verbose:
            pretty_print(payload)

        #topic_id = write_request(url)["id"]
        topic_id = write_request(url, payload, workspace)["id"]
        # print("New topicmap '%s' was created with topic_id %s." % (tm_name, topic_id))
        return(topic_id)


def change_password(dm_user, dm_old_pass, dm_new_pass):
    """
    This function changes a user's password
    """
    ###
    ### Needs testing and might need adopting to DMX
    ###
    base64string = base64.encodestring(
        "%s:%s" % (dm_user, dm_old_pass)
    ).replace("\n", "")

    # get id of user_account (not user_name!)
    url = 'core/topic/by_type/dmx.accesscontrol.user_account?children=false'
    topic_id = read_request(url)
    print("change Password - Topic ID of user: %s" % topic_id)

    # get id of private workspace
    url = 'core/topic?type_uri=dmx.workspaces.workspace_name&query=Private%%20Workspace'
    wsnameid = read_request(url)["topics"][0]["id"]
    url = ('core/topic/%s/related_topics'
           '?assoc_type_uri=dmx.core.composition&my_role_type_uri='
           'dmx.core.child&others_role_type_uri=dmx.core.parent&'
           'others_topic_type_uri=dmx.workspaces.workspace' % str(wsnameid)
          )
    wsid = read_request(url)
    print("Change Password WS ID = %s" % wsid)

    # change password
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    url = 'http://%s:%s/core/topic/%s' % (server, port, topic_id)
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: 'PUT'
    # encrypt the new password
    hash_object = hashlib.sha256(dm_new_pass)
    dm_new_pass = '-SHA256-'+hash_object.hexdigest()
    payload = {
        'children': {
            'dmx.accesscontrol.password': dm_new_pass
        }
    }
    try:
        response = (
            json.loads(
                urllib.request.urlopen(
                    req, (json.dumps(payload))
                ).read()
            )
        )
    except urllib.error.HTTPError as e:
        print('Change Password Error: '+str(e))
    else:
        print(response)


def get_ws_id(workspace):
    """
    This function gets the workspace ID for a workspace by its name.
    It's much faster to get it by its uri, if present.
    """
    if verbose:
        print("GET_WS_ID: Searching Workspace ID for %s" % workspace)
    url = ('core/topic?type_uri=dmx.workspaces.workspace_name'
           '&query="%s"' % workspace.replace(' ', '%20'))
    # find the workspace_name in the result
    topics = read_request(url)["topics"]
    for topic in topics:
        # find the workspace_name in the result
        if topic['typeUri'] == 'dmx.workspaces.workspace_name':
            wsnameid = (topic['id'])
            break
    if verbose:
        print("WS NAME ID = %s" % wsnameid)
    url = ('core/topic/%s/related_topics'
           '?assoc_type_uri=dmx.core.composition&my_role_type_uri='
           'dmx.core.child&others_role_type_uri=dmx.core.parent&'
           'others_topic_type_uri=dmx.workspaces.workspace' %
           str(wsnameid))
    topic_id = read_request(url)[0]["id"]
    if verbose:
        print("WS ID = %s" % topic_id)
    return(topic_id)


def create_ws(workspace, ws_type, uri=''):
    """
    This function creates a workspace with workspace uri
    (needed for id) on the server.
    """
    ### `uri` is optional.
    if not uri:
        uri = workspace.lower()+'.uri'
    url = ('workspace?name=%s&uri=%s&sharing_mode_uri=dmx.workspaces.%s' %
           (workspace.replace(' ', '%20'), uri.replace(' ', '%20'), ws_type))
    topic_id = write_request(url, expect_json=True)["id"]
    # ~ response = write_request(url, expect_json=True)
    return(topic_id)


def create_member(workspace='DMX', dm_user='testuser'):
    """
    This function creates a user memebrship association for
    the workspace on the server.
    """
    if verbose:
        print("Creating Workspace membership for user %s in %s" % (dm_user, workspace))
    wsid = get_ws_id(workspace)
    url = ('accesscontrol/user/%s/workspace/%s' %
           (dm_user, wsid))
    # topic_id = write_request(url)
    response = write_request(url, expect_json=False)
    return(response)


def create_note(title, body, workspace='Private Workspace'):
    """
    This function creates a new note with text body
    in the workspace on the server.
    """
    if verbose:
        print("Creating a new note %s with text body %s in workspace %s" %
              (title, body, workspace))

    # ~ wsid = get_ws_id(workspace)
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
    if verbose:
        print("NEW NOTE: %s" % payload)
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def send_data(payload, workspace='DMX'):
    """
    This function sends the topics according to payload to
    the workspace name on the server.
    """
    if verbose:
        print("VERBOSE: %s" % verbose)
        print("SEND_DATA: sending data to workspace '%s'" % workspace)
    url = 'core/topic/'
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def reveal_topic(workspace, map_id, topic_id, x=0, y=0, pinned=False):
    """
    This function reveales a topic (id) on a topicmap (id) at
    position x, y, pinned or unpinned
    """
    if pinned:
        pinned = str('true')
    else:
        pinned = str('false')
    url = ('topicmap/%s/topic/%s' % (map_id, topic_id))
    payload = json.loads(
        '{ "dmx.topicmaps.x": %s, "dmx.topicmaps.y": %s, \
        "dmx.topicmaps.visibility": true, "dmx.topicmaps.pinned": %s }'
        % (x, y, pinned)
    )
    response = write_request(url, payload, workspace, expect_json=False)
    return(response)


def import_vcard(vcard_file, workspace):
    """
    This function imports data from a vcard file and creates a person topic.
    """

    version = platform.python_version().split('.')
    if verbose:
        print ("VERSION: %s" % version)
    if int(version[0]) < 3 or int(version[1]) < 6:
        print('SORRY! VCARD option requires Python 3.6 or higher.')
        sys.exit(0)
    else:
        try:
            import vobject
        except ModuleNotFoundError as err:
            # Error handling
            print(err)
            print('Please install module python3-vobject')
            sys.exit(1)

    payload = read_file(vcard_file)
    # ~ if verbose:
        # ~ print("VCARD FILE:\n%s" % payload)
    vcard = vobject.readOne(payload)
    if verbose:
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
        pass

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
    if verbose:
        print("NEW PERSON: %s" % payload)
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
    data = get_data('topic/by_type/%s' % topictype)
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
    url = ('core/topic/%s/related_topics?' % topic_id)
    return(read_request(url))


def get_creator(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('accesscontrol/object/%s/creator' % topic_id)
    return(read_request(url))


def get_modifier(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('accesscontrol/object/%s/modifier' % topic_id)
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
    url = ('accesscontrol/workspace/%s/owner' % workspace_id)
    return(read_request(url))


def delete_topic(topic_id):
    """
    This function deletes a topic by its id from the server.
    """
    ###
    ### Still needs to be adopted to make use of write_request
    ###
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    url = ('http://%s:%s/core/topic/%s' %
           (server, port, topic_id))
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: 'DELETE'
    try:
        response = (json.loads(urllib.request.urlopen(req).read()))
    except urllib.error.HTTPError as e:
        print('Delete Topic Error: '+str(e))
    else:
        return(response)


def pretty_print(data):
    """
    This function just prints the json data in a pretty way. :)
    """
    # print("Data: %s" % type(data))
    print(json.dumps(data, indent=3, sort_keys=True))
    return


def main(args):
    """
    ToDo:
    # change_password(user, password, 'new_pass')
    """
    global verbose # set verboe mode
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
        '-v', '--verbose',
        help='Enable verbose mode.',
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


    args = parser.parse_args()
    argsdict = vars(args)

    ## action on arguments (order matters!) ##
    """
    These functions shall not include logic, but only check and interpret the
    arguments and then call a funtion (ideally named like argument) to do
    the computing.
    """
    # enable verbose mode
    if argsdict['verbose']:
        verbose = True
    else:
        verbose = False

    # instance must be first, cause it overwrites the default setting from config
    if argsdict['config_properties']:
        # ~ data = read_dmx_config(argsdict['config_properties'])
        read_dmx_config(argsdict['config_properties'])
    else:
        read_config_file()

    # login is next, as one may want to manually set who logs in
    if argsdict['login']:
        if (argsdict['user'] != None) and (argsdict['password'] != None):
            config.set('Credentials', 'authname', argsdict['user']) # usualy the admin password
            config.set('Credentials', 'password', argsdict['password']) # usualy the admin password
        else:
            print("ERROR! Missing username or password.")

    if argsdict['file']:
        """
        This function needs rewrinting! The logic of importing data from
        json file should be in a separate function.
        """
        if verbose:
            print("Importing json data from file %s" % (argsdict['file']))
        # ~ payload = import_payload(str(argsdict['file']))
        payload = read_file(str(argsdict['file']))
        if verbose:
            print("JSON DATA FROM FILE:\n%s" % payload)
        # ~ payload = json.load(payload)
        # ~ payload = json.dumps(payload)
        payload = payload.replace('\n', '')
        payload = json.loads(payload)
        payload = check_payload(payload)
        payload_len = len(payload)
        if argsdict['workspace']:
            if payload_len > 0:
                if verbose:
                    print("WORKSPACE: %s" % argsdict['workspace'])
                data = send_data(payload, argsdict['workspace'])
                print(data)
            else:
                print("ERROR! Missing data in file %s" % (argsdict['file']))
        else:
            print("ERROR! Missing workspace declaration.")

    if argsdict['import_vcard']:
        if verbose:
            print("Importing vcard data from file %s" % (argsdict['import_vcard']))
        if argsdict['workspace']:
            data = import_vcard(argsdict['import_vcard'], argsdict['workspace'])
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
    # still missing: set type of new map via option (default is topicmap)
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
        # Does not work with 'private' for now!
        if argsdict['ws_type'] in ["confidential", "collaborative", "public", "common"]:
            if verbose:
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

    if argsdict['delete_topic']:
        data = get_topic(argsdict['delete_topic'])
        if query_yes_no("Are you sure you want to delete topic id %s with value \"%s\"" %
                        (argsdict['delete_topic'], data['value'])):
            print('yes')
            data = delete_topic(argsdict['delete_topic'])
            pretty_print(data)
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


if __name__ == '__main__':
    # import sys
    ## debug
    # print(sys.version_info)
    if (sys.version_info < (3, 0)):
        print('ERROR! This program requires python version 3 or highter.')
        sys.exit(1)
    else:
        sys.exit(main(sys.argv))

# END.
