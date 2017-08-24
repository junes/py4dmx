#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  dmx.py - _dev.py
#
#  Copyright 2016 Juergen Neumann <juergen@junes.eu>
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

__author__ = 'Juergen Neumann'
__copyright__ = 'Copyright 2016-2017, Juergen Neumann'
__license__ = 'GPL'
__version__ = '3'
__maintainer__ = 'Juergen Neumann'
__email__ = 'juergen@junes.eu'
__status__ = 'Development'
__doc__ = """
The aim of the script is to provide a set of python functions to play
with DeepaMehta's REST API.

When creating new topics, the script checks for exisiting topics with the same
name and will try to reuse them in composits, if possible (=aggregations).

So far the script has been tested and developed for objects with simple
cardinality, eg. one address, one telephone number, etc.

There are still some issues when there is more than one address in a composite.
Creating complex composites (like the provided json person example).

jpn - 20170231

"""

import os, sys, json, urllib, urllib2, cookielib, base64
import ConfigParser
import hashlib
import argparse

## The user we are modifying, e.g. when creating a new user
## This is supposed to become a command line option
dm_user = "new_user"
dm_pass = "you_should_use_a_better_password_here!"

## for simple topics
next_key = ""
next_value = ""

def read_config_file():
    """
    Put this content in your dmx.cfg:

    [Credentials]
    authname = admin
    password =

    [Connection]
    server = localhost
    port = 8080
    workspace = DeepaMehta
    """
    global config

    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    config_file_name = 'dmx.cfg'
    config_file=os.path.join(script_dir, config_file_name)
    ## if empty or missing, use these parameters
    config = ConfigParser.SafeConfigParser(
        {
            'authname': 'admin',
            'password': '',
            'server': 'localhost',
            'port': '8080',
            'workspace': 'DeepaMehta'
        }
    )
    if os.path.isfile(config_file):
        config.read(config_file)
        server = config.get('Connection', 'server')
        port = config.get('Connection', 'port')
        workspace = config.get('Connection', 'workspace')
    else:
        print("ERROR! Config file %s not found." % config_file)
        sys.exit(1)


def read_dmx_config(instance):
    """
    Reads the configuration data from /etc/deepamehta/$INSTANCE.conf
    and overwrites the config settings with new values.
    """
    global config
    dmx_params={}
    dmx_config_file=str('/etc/deepamehta/' + instance + '.conf')
    # print(dmx_config_file)
    if os.access(dmx_config_file, os.R_OK):
        with open(dmx_config_file) as f_in:
            lines = filter(None, (line.rstrip() for line in f_in))
    for ln in lines:
        # print(ln)
        if not ln[0] in ('', ' ', '#', ';'):
            key, val = ln.strip().replace(" ", "").split('=', 1)
            dmx_params[key.lower()] = val
    # print(dmx_params['org.osgi.service.http.port'])
    # print(dmx_params['dm4.security.initial_admin_password'])
    ## , dmx_params['dm4.security.initial_admin_password'])
    port=dmx_params['org.osgi.service.http.port']
    password=dmx_params['dm4.security.initial_admin_password']
    config.set('Credentials', 'password', password) # usualy the admin password
    config.set('Connection', 'port', port) # usualy the admin user

    for mandatory in ['org.osgi.service.http.port', 'dm4.security.initial_admin_password']:
        if mandatory not in dmx_params.keys():
            # open(os.environ['HOME']+'/.xmppacct','w').write('#Uncomment fields before use and type in correct credentials.\n#JID=romeo@montague.net/resource (/resource is optional)\n#PASSWORD=juliet\n')
            print("ERROR! Could not read config file %s." % dmx_config_file)
            sys.exit(0)


def import_payload(json_filename, default="payload.json"):
    """
    Here we open the file and import the content as json.
    """
    print("Reading file %s" % (json_filename))
    with open(json_filename, 'r') as data_file:
        payload_json = json.load(data_file)

    # Test if the payload is a valid json object and get it sorted.
    try:
        payload = json.loads(json.dumps(payload_json, indent=3, sort_keys=True))
        print("LenPayload: %s" % len(payload))
    except:
        print("ERROR! Could not read Payload. Not JSON?")
        sys.exit(1);

    pretty_print(payload)
    return(payload)


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
        choice = raw_input().lower()
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
    base64string = base64.encodestring("%s:%s" %
                    (authname, password)).replace("\n", "")
    return(base64string)


def get_session_id():
    """
    Creates an initial session and returns the session id.
    """
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/core/topic/0' % (server, port)
    req = urllib2.Request(url)
    req.add_header("Authorization", "Basic %s" % get_base64())
    req.add_header("Content-Type", "application/json")
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    try:
        test_url = opener.open(req)
    except urllib2.HTTPError, e:
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
    print("Read Data %s" % url)
    req = urllib2.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    try:
        response = (json.loads(urllib2.urlopen(req).read()))
    except urllib2.HTTPError, e:
        print('Read Data Error: '+str(e))
    except ValueError:
        print('WARNING! No JSON Object found.')
        try:
            response = urllib2.urlopen(req).read()
        except urllib2.HTTPError, e:
            print('Read Data Error: '+str(e))
        else:
            return(response)
    else:
        return(response)


def write_request(url, payload, workspace='DeepaMehta'):
    """
    Reads the data from a given URL.
    """
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/%s' % (server, port, url)
    jsessionid = get_session_id()
    print("Write Data %s" % url, payload)
    wsid = get_ws_id(workspace)
    req = urllib2.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s; dm4_workspace_id=%s" % (jsessionid, wsid))
    req.add_header("Content-Type", "application/json")
    try:
        response = (json.loads(urllib2.urlopen(req,
                    (json.dumps(payload))).read()))
    except urllib2.HTTPError, e:
        print('Write Data Error: '+str(e))
    else:
        return(response)


def create_user(dm_user, dm_pass):
    """
    This function creates a new user on the server.
    """
    # check if username exits
    users = get_items('dm4.accesscontrol.username').values()
    print(users)
    if dm_user in users:
        print("ERROR! User '%s' exists." % dm_user)
        sys.exit(1)
    else:
        # create user
        url = 'accesscontrol/user_account'
        hash_object = hashlib.sha256(dm_pass)
        dm_pass = '-SHA256-'+hash_object.hexdigest()
        payload = {'username' : dm_user, 'password' : dm_pass}
        topic_id = write_request(url, payload)["id"]
        print("New user '%s' was created with topic_id %s." % (dm_user, topic_id))
        return


def change_password(dm_user, dm_old_pass, dm_new_pass):
    """
    This function changes a user's password
    """
    base64string = base64.encodestring("%s:%s" %
                    (dm_user, dm_old_pass)).replace("\n", "")

    # get id of user_account (not user_name!)
    url = 'core/topic/by_type/dm4.accesscontrol.user_account?include_childs=false'
    topic_id = read_request(url)
    print("change Password - Topic ID of user: %s" % topic_id)

    # get id of private workspace
    url = 'core/topic?field=dm4.workspaces.name&search=Private%%20Workspace'
    wsnameid = read_request(url)[0]["id"]
    print("WSNAMEID: %s" % wsnameid)


    url = ('core/topic/%s/related_topics'
           '?assoc_type_uri=dm4.core.composition&my_role_type_uri='
           'dm4.core.child&others_role_type_uri=dm4.core.parent&'
           'others_topic_type_uri=dm4.workspaces.workspace' % str(wsnameid)
          )
    wsid = read_request(url)
    print("Change Password WS ID = %s" % response)

    # change password
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    url = 'http://%s:%s/core/topic/%s' % (server, port, topic_id)
    req = urllib2.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: 'PUT'
    # encrypt the new password
    hash_object = hashlib.sha256(dm_new_pass)
    dm_new_pass = '-SHA256-'+hash_object.hexdigest()
    payload = {
        'childs': {
            'dm4.accesscontrol.password': dm_new_pass
        }
    }
    try:
        response = (json.loads(urllib2.urlopen(req,
                    (json.dumps(payload))).read()))
    except urllib2.HTTPError, e:
        print('Change Password Error: '+str(e))
    else:
        print(response)


def get_ws_id(workspace):
    """
    This function gets the workspace ID for a workspace by its name.
    It's much faster to get it by its uri, if present.
    """
    print("Searching Workspace ID for %s" % workspace)
    # url = ('core/topic?field=dm4.workspaces.name&search="%s"' % urllib.quote(workspace, safe=''))
    url = ('core/topic?field=dm4.workspaces.name&search="%s"' % workspace.replace(' ', '%20'))
    wsnameid = read_request(url)[0]["id"]
    url = ('core/topic/%s/related_topics'
           '?assoc_type_uri=dm4.core.composition&my_role_type_uri='
           'dm4.core.child&others_role_type_uri=dm4.core.parent&'
           'others_topic_type_uri=dm4.workspaces.workspace' %
           str(wsnameid))
    ws_id = read_request(url)[0]["id"]
    print("WS ID = %s" % ws_id)
    return(ws_id)


def create_ws(workspace, ws_type):
    """
    This function creates a workspace with workspace uri
    (needed for id) on the server.
    """
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    uri = workspace.lower()+'.uri'
    url = ('http://%s:%s/workspace/%s/%s/dm4.workspaces.%s' %
            (server, port, workspace, uri, ws_type))
    req = urllib2.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    try:
        #response = (json.loads(urllib2.urlopen(req, data='')))
        response = urllib2.urlopen(req, data='')
    except urllib2.HTTPError, e:
        print('Create WS Error: '+str(e))
    else:
        print('Create WS: success')
        #return(response)


def create_member(workspace, dm_user):
    """
    This function creates a user memebrship association for
    the workspace on the server.
    """
    print("Creating Workspace membership for user %s in %s" % (dm_user, workspace))
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    wsid = get_ws_id(workspace)
    url = ('http://%s:%s/accesscontrol/user/%s/workspace/%s' %
            (server, port, dm_user, wsid))
    req = urllib2.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    try:
        urllib2.urlopen(req, data='')
    except urllib2.HTTPError, e:
        print('Create Member Error: '+str(e))
    else:
        print('Create Member: success')


def send_data(payload, workspace='DeepaMehta'):
    """
    This function sends the topics according to payload to
    the workspace name on the server.
    """
    url = 'core/topic/'
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def get_topic(topic_id):
    """
    This function fetches the data according to datapath from
    the server and returns the data.
    """
    url = ('core/topic/%s?include_childs=false' % topic_id)
    return(read_request(url))


def get_data(datapath):
    """
    This function fetches the data according to datapath from
    the server and returns the data.
    """
    url = ('core/%s?include_childs=true' % datapath)
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
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    url = ('http://%s:%s/core/topic/%s' %
            (server, port, topic_id))
    req = urllib2.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: 'DELETE'
    try:
        response = (json.loads(urllib2.urlopen(req).read()))
    except urllib2.HTTPError, e:
        print('Delete Topic Error: '+str(e))
    else:
        return(response)


def deep_inspect(obj):
    """
    This function is parsing a nested dictionary. Inspiration found here:
    http://stackoverflow.com/questions/15785719/how-to-print-a-dictionary-line-by-line-in-python
    """
    ref_ids = {}   # dict with aggrs ref_ids for an existing topic
    childs = {}    # dict with the childs of a topictype where all assocs are aggregations
    aggrs = {}     # dict with only the aggregated childs of a topictype with mixed or missing associations
    comp_refs = {} # dictionary with the ref_ids of the compositions
    multi_comps = {} # dict with many values per one composition key

    def __comprefs(obj, nested_level=0):
        nested_level += 1
        if type(obj) == dict and len(comp_refs) > 0:
            for k, v in obj.items():
                default_key = "EMPTY_KEY"
                r = comp_refs.get(k, default_key)
                if hasattr(v, '__iter__'):
                    print(str(nested_level)+'.dT'+nested_level*'    '+'key: %s' % k)
                    if r != "EMPTY_KEY":
                        val_len = len(obj[k])
                        if type(obj[k]) == dict and k in comp_refs.iterkeys():
                            print("dict_len: %s" % val_len)
                            ### hier sind wir für die einfachen copositions
                            for l in range(val_len):
                                obj[k] = comp_refs[k]
                        elif type(obj[k]) == list:
                            print("list_len: %s" % val_len)
                            for l in range(val_len):
                                try:
                                    print(obj[k][l]["childs"])
                                except:
                                    print("ERROR: "+str(type(obj[k])))
                                    pass
                                else:
                                    ### hier kommen die komplexen compositions
                                    list_of_values = multi_comps[k]
                                    # print(list_of_values[l])
                                    obj[k][l]["value"] = list_of_values[l]
                                    del obj[k][l]["childs"]
                    __comprefs(v, nested_level)
                else:
                    print(str(nested_level)+'.dF'+nested_level*'    '+"key = %s, value = %s" % (k,v))
                    if r != "EMPTY_KEY":
                        for val in childs.itervalues():
                            for key in val:
                                if key == k:
                                    del obj[k]
        elif type(obj) == list and len(comp_refs) > 0:
            for v in obj:
                if hasattr(v, '__iter__'):
                    __comprefs(v, nested_level)
                else:
                    print(str(nested_level)+'.lF'+nested_level*'    '+"key = %s, value = %s" % (k,v))
        elif type(obj) != dict and type(obj) != list and len(comp_refs) > 0:
            print(str(nested_level)+'.oF'+nested_level*'    '+"Object: %s" % obj)

    def __replacer(obj, nested_level=0):
        nested_level += 1
        comp_string = []
        child_key = ""
        if type(obj) == dict:
            for k, v in obj.items():
                if hasattr(v, '__iter__'):
                    print(str(nested_level)+'.dT'+nested_level*'    '+'key: %s' % k)
                    __replacer(v, nested_level)
                else:
                    # First we prepare the comp_string to search for
                    # a ref_id for the whole composite.
                    for val in childs.itervalues():
                        for key in val:
                            if key == k:
                                # print("REPLACER: comp_string.append %s" % obj[k])
                                comp_string.append(obj[k])

                    # Then we search the ref_id for each agrregated topic.
                    # comp_count = 0 # simple counter
                    for val in aggrs.itervalues():
                        for key in val:
                            if key == k:
                                # print(k+" ist in childs!")
                                # comp_string.append(obj[k])
                                data = get_items(key)
                                # print(data)
                                for key, val in data.iteritems():
                                    # print key, val
                                    if obj[k] == val:
                                        # Here we want to do some more research
                                        # on the topic itself. Especially if
                                        # we have more than one of it. (future)
                                        if "dm4.core.composition" in (get_related(key)[1]["assoc"]["type_uri"]):
                                            print("Houston, we have a problem: Topic %s has another composition association ..." % key)
                                        else:
                                            obj[k] = ("ref_id:%s" % key)
                                            #################
                                            # delete_topic(key)
                                            #################

            if len(comp_string) > 0:
                # print("len(comp_string) = %s" % len(comp_string))
                for child_key in childs.iterkeys():
                    data = get_items(child_key)
                    for key, val in data.iteritems():
                        c_found = 0
                        for c in comp_string:
                            if c in val:
                                c_found += 1
                        if len(comp_string) == c_found:
                            print("REPLACER: "+child_key+" "+" ".join(comp_string)+' exists. '+'ref_id: '+str(key))
                            comp_refs[child_key] = ("ref_id:%s" % key)
                            # wenn es davon auch mehrere gleiche gibt, wie soll
                            # dann damit verfahren werden? => checker ???
                            #################
                            # delete_topic(key)
                            #################
                            if nested_level > 0:
                                print("+++ EXIT!? (Level: %s) +++" % nested_level)

            default_key = "EMPTY_KEY"
            r = comp_refs.get(child_key, default_key)
            if r != "EMPTY_KEY":
                # print("comp_refs[child_key] = %s" % comp_refs[child_key])
                multi_comps.setdefault(child_key, []).append(comp_refs[child_key])

        elif type(obj) == list:
            for v in obj:
                if hasattr(v, '__iter__'):
                    __replacer(v, nested_level)
                else:
                    print(str(nested_level)+'.lF'+nested_level*'    '+"key = %s, value = %s" % (k,v))
        else:
            print(str(nested_level)+'.oF'+nested_level*'    '+"Object: %s" % obj)

    def __analyzer(k, v, nested_level):
        global next_key
        global next_value
        if k != "childs" and k != "assoc" and k != "value":
            if k == "type_uri":
                k = v
            data = get_data('topictype/'+k)
            data_type = data["data_type_uri"]
            print('\033[94m'+'type'+'\033[0m'+nested_level*'    '+data_type)
            comp_defs = [] # This is a list
            aggr_defs = [] # This is a list

            if data_type == "dm4.core.composite":
                for i in range(len(data["assoc_defs"])):
                    child = data["assoc_defs"][i]["role_2"]["topic_uri"]
                    assoc_type = data["assoc_defs"][i]["type_uri"]
                    print('\033[94m'+'child'+'\033[0m'+nested_level*'    '+"%s => %s" % (child, assoc_type))
                    if assoc_type == "dm4.core.composition_def":
                        comp_defs.append(child)
                    elif assoc_type == "dm4.core.aggregation_def":
                        """
                        In dieser Liste landen die per Aggregation
                        assoziierten Topics. Nur für diese müssen und können
                        wir nach ref_ids suchen.
                        """
                        aggr_defs.append(child)
                if len(comp_defs) == 0 and len(aggr_defs) != 0:
                    """
                    Diese Liste enthält alle Aggregation Childs für den
                    Composite Typen k. Die Liste brauchen wir später, um
                    ggf. die entsprechenden ref_ids für das komplette Composite
                    zu finden.
                    """
                    childs[k] = aggr_defs
                if len(aggr_defs) > 0:
                    """
                    Das Composite enthält sowohl Aggregations als auch
                    Compositions oder bei der Suche nach vorhandenen Aggregations
                    des kompletten Composits ist ein Wert noch nicht vorhanden.
                    Wir merken uns dehalb die Aggregations, um später
                    ggf. den Value gegen die ref_id eines vorhandenen Topics
                    auszutaucschen.
                    """
                    aggrs[k] = aggr_defs
            else:
                print('\033[93m'+'value'+nested_level*'    '+str(v)+'\033[0m')
                print("ANALYZER: next_key = %s" % k)
                next_key = k
        elif k == "value":
            print("ANALYZER: next_value = %s" % v)
            next_value = v

    def __checker(topic_type, topic_value):
        """
        Ich will eine check_topic Funktion bauen. Diese soll zuerst prüfen,
        ob es ein oder mehrere Topics mit diesem Wert gibt. Danach soll geprüft werden,
        ob jedes dieser Topics eventuell irgendwohin eine composition assoc hat.
        Dann soll geprüft werden, wer der creator und wer der owner des Topics ist (bin ich das?)
        und in welchem workspace es liegt. Dann soll genrelell (globale variable) entschieden
        werden, ob abgebrochen wird, oder ob das best geeignetse Topic als Referenz
        verwendet werden soll.
        """
        print("CHECKER TopicType: %s" % topic_type)
        found = 0
        topics = {}
        if topic_type != "childs" and topic_type != "assoc" and topic_type != "value" and topic_type != "type_uri":
            data = get_items(topic_type)
            # print("Topic_Value: %s" % topic_value)
            if len(data) > 0:
                for key, val in data.iteritems():
                    # print("CHECKER: Key: %s, Val: %s" % (key, val))
                    if val == topic_value:
                        found += 1
                        # print"CHECKER: %s zum %s. mal gefunden! %s" % (val, found, key)
                        topics[found] = key
            print"CHECKER: %s %s mal gefunden!" % (topic_value, found)
            if found >= 1:
                for k in topics.iterkeys():
                    # print("CHECKER Topic ID: %s" % topics[k])
                    creator = get_creator(topics[k])
                    modifier = get_modifier(topics[k])
                    workspace_id = get_topic_ws(topics[k])
                    workspace_owner = get_ws_owner(workspace_id)
                    print("TopicID: %s" % topics[k])
                    print("Creator: %s" % creator)
                    print("Modifier: %s" % modifier)
                    print("Workspace ID: %s" % workspace_id)
                    print("Workspace Owner: %s" % workspace_owner)
                    # Der nachfolgende Test sollte eine eigene Funktion werden.
                    try:
                        if "dm4.core.composition" in (get_related(topics[k])[1]["assoc"]["type_uri"]):
                            print("Houston, we have a problem: Topic %s has another composition association ..." % topics[k])
                    except:
                        pass
                    #################
                    # delete_topic(topics[k])
                    #################

    def __digger(obj, nested_level=0):
        global next_key
        global next_value
        nested_level += 1
        if type(obj) == dict:
            for k, v in obj.items():
                if hasattr(v, '__iter__'):
                    print(str(nested_level)+'.dT'+nested_level*'    '+'key: %s' % k)
                    __analyzer(k, v, nested_level)
                    __digger(v, nested_level)
                else:
                    print(str(nested_level)+'.dF'+nested_level*'    '+"key = %s, value = %s" % (k,v))
                    __checker(k, v)
                    __analyzer(k, v, nested_level)
                    print("next_key = %s, next_value = %s" % (next_key, next_value))
                    if next_key != "" and next_value != "":
                        print("hui!")
                        __checker(next_key, next_value)
                        next_key = ""
                        next_value = ""
        elif type(obj) == list:
            for v in obj:
                if hasattr(v, '__iter__'):
                    __digger(v, nested_level)
                else:
                    print(str(nested_level)+'.lF'+nested_level*'    '+"key = %s, value = %s" % (k,v))
        else:
            print(str(nested_level)+'.oF'+nested_level*'    '+"Object: %s" % obj)
        print("Nested Level max. = %s" % nested_level)

    print("\nDIGGER\n")
    __digger(obj)

    print("\nREPLACER\n")
    __replacer(obj)

    print("\nCOMPREFS\n")
    __comprefs(obj)

    pretty_print(obj)

    return(obj)


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
    global config
    read_config_file()
    # get_session_id()

    parser = argparse.ArgumentParser(description = 'This is a Python script \
             for DeepaMehta by Juergen Neumann <juergen@junes.eu>. It is free \
             software licensed under the GNU General Public License Version 3 \
             and comes with ABSOLUTELY NO WARRANTY.')
    parser.add_argument('-b','--by_type', type=str,help='Get all items of a TopicType by its topic.type.uri.', required=False)
    parser.add_argument('-c','--create_user', help='Create a user with -u username and -p password.', action='store_true', required=False, default=None)
    parser.add_argument('-d','--delete_topic', type=int, help='Detele a topic by id.', required=False)
    parser.add_argument('-f','--file', type=str,help='Creates a new topic from json file.', required=False)
    parser.add_argument('-i','--instance', type=str,help='Reads config data from /etc/deepamehta/$INSTANCE.conf.', required=False)
    parser.add_argument('-l','--login', help='Login as -u user with password -p instead of admin.', action='store_true', required=False, default=None)
    parser.add_argument('-m','--membership', help='Create a new workspace membership with -w workspace name and -n username of new member.', action='store_true', required=False, default=None)
    parser.add_argument('-n','--new_member', type=str, help='Provide the username of new member.', required=False)
    parser.add_argument('-p','--password', type=str, help='Provide a password.', required=False)
    parser.add_argument('-r','--get_related', type=int, help='Get all related items of a topic id.', required=False)
    parser.add_argument('-s','--get_session_id', help='Get a valid session id.', action='store_true', required=False, default=None)
    parser.add_argument('-t','--get_topic', type=int, help='Get all data of a topic id.', required=False)
    parser.add_argument('-u','--user', type=str, help='Provide a username.', required=False)
    parser.add_argument('-w','--workspace', type=str, help='Create a new workspace by name with -T type.', required=False)
    parser.add_argument('-T','--ws_type', type=str, help='Define Type of the new workspace.', required=False)
    args = parser.parse_args()
    argsdict = vars(args)

    ## action on arguments ##

    # instance must be first, cause it overwrites the default setting from config
    if argsdict['instance']:
        data = read_dmx_config(argsdict['instance'])

    if argsdict['file']:
        print("Importing json data from file %s" % (argsdict['file']))
        payload = import_payload(str(argsdict['file']))
        #~ # print(type(payload))
        payload_len = len(payload)
        #~ # print("payload_len: %s" % payload_len)
        if payload_len > 0:
            # dump(payload)
            deep_inspect(payload)
            # write data
            dm_action_id = (send_data(payload))
            print("CREATED: %s" % dm_action_id)
        else:
            print("ERROR! Missing data in file %s" % (argsdict['file']))

    if argsdict['create_user']:
        if (argsdict['user'] != None) and (argsdict['password'] != None):
            data = create_user(argsdict['user'], argsdict['password'])
        else:
            print("ERROR! Missing username or password.")

    if argsdict['by_type']:
        data = get_items(argsdict['by_type'])
        pretty_print(data)

    if argsdict['get_related']:
        data = get_related(argsdict['get_related'])
        pretty_print(data)

    if argsdict['get_topic']:
        data = get_topic(argsdict['get_topic'])
        pretty_print(data)

    if argsdict['workspace'] and (argsdict['ws_type'] != None) and not argsdict['member']:
        # Does not work with 'private' for now!
        if argsdict['ws_type'] in ["confidential", "collaborative", "public", "common"]:
            print("Creating new %s workspace %s" % (argsdict['ws_type'],argsdict['workspace']))
            data = create_ws(argsdict['workspace'], argsdict['ws_type'])
        elif argsdict['ws_type'] == "private":
            print("Sorry! %s is not working yet via scripting." % argsdict['ws_type'])
        else:
            print("ERROR! %s is not a valid workshop type." % argsdict['ws_type'])

    if argsdict['login']:
        if (argsdict['user'] != None) and (argsdict['password'] != None):
            config.set('Credentials', 'authname', argsdict['user']) # usualy the admin password
            config.set('Credentials', 'password', argsdict['password']) # usualy the admin password
        else:
            print("ERROR! Missing username or password.")

    if argsdict['get_session_id']:
        data = get_session_id()
        print(data)

    if argsdict['membership']:
        if (argsdict['workspace'] != None) and (argsdict['new_member'] != None):
            data = create_member(argsdict['workspace'], argsdict['new_member'])
        else:
            print("ERROR! Missing username of new member or missing workspace name.")

    if argsdict['delete_topic']:
        data = get_topic(argsdict['delete_topic'])
        if query_yes_no("Are you sure you want to delete topic id %s with value \"%s\"" % (argsdict['delete_topic'], data['value'])):
            print('yes')
            data = delete_topic(argsdict['delete_topic'])
            pretty_print(data)
        else:
            print('no')

    if len(sys.argv) < 2:
        parser.print_usage()
        print("Use -h or --help for more information.")
        parser.exit(1)


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))

# END.
