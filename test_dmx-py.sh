#!/bin/bash

if [ "$1" == "-v" ]; then
    VERBOSE='-v'
else
    VERBOSE=""
fi

PY4DMX='./dmx.py'
# NUNC="$( date +"%F_%T" )"
# ':' in WS NAME is a problem when creating a topic!
NUNC="$( date +"%F_H-%M-%S" )"
USER="User_${NUNC}"
# PASS="$( pwgen -sn 25 1 )"
PASS="$( pwgen -syn 25 1 | sed s'/\%/\-/g' | sed s'/\:/\_/g' | sed s'/\"/\+/g')"
PASS="$( pwgen -sn 25 1 )"
WORKSPACE="WS_${NUNC}"
WORKSPACE_TYPE='collaborative'
NOTE_FILE='./note_example.json'

create_user () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new user '${USER}' with password '${PASS}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -C -u "${USER}" -p "${PASS}" )"
    echo "${RESULT}"
    # RESULT="$( echo "${RESULT}" | grep "New user '${USER}' was created with topic_id " )"
    # if [ "${RESULT}" != "" ]; then
    #    echo "INFO: ${RESULT}"
    #    echo "INFO: create_user test successful."
    # else
    #    echo "ERROR! create_user test failed."
    #    exit 1
    # fi
}

user_login () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Login new user '${USER}' with password '${PASS}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -s -u "${USER}" -p "${PASS}" )"
    echo "${RESULT}"
    #RESULT="$( echo "${RESULT}" | grep "New user '${USER}' was created with topic_id " )"
    #if [ "${RESULT}" != "" ]; then
    #    echo "INFO: ${RESULT}"
    #    echo "INFO: create_user test successful."
    #else
    #    echo "ERROR! create_user test failed."
    #    exit 1
    #fi
}


create_workspace () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new workspace '${WORKSPACE}' with sharing mode '${WORKSPACE_TYPE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -w "${WORKSPACE}" -T "${WORKSPACE_TYPE}" )"
    echo "${RESULT}"
    #RESULT="$( echo "${RESULT}" | grep "New user '${USER}' was created with topic_id " )"
    #if [ "${RESULT}" != "" ]; then
    #    echo "INFO: ${RESULT}"
    #    echo "INFO: create_user test successful."
    #else
    #    echo "ERROR! create_user test failed."
    #    exit 1
    #fi
}

create_member () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new workspace member '${USER}' in '${WORKSPACE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -m -w "${WORKSPACE}" -n "${USER}" )"
    echo "${RESULT}"
    #RESULT="$( echo "${RESULT}" | grep "New user '${USER}' was created with topic_id " )"
    #if [ "${RESULT}" != "" ]; then
    #    echo "INFO: ${RESULT}"
    #    echo "INFO: create_user test successful."
    #else
    #    echo "ERROR! create_user test failed."
    #    exit 1
    #fi

}

create_note () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new note ${NOTE_FILE} as user '${USER}' in workspace '${WORKSPACE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -l -u ${USER} -p ${PASS} -f ${NOTE_FILE} -w ${WORKSPACE} )"
    echo "${RESULT}"
    #RESULT="$( echo "${RESULT}" | grep "New user '${USER}' was created with topic_id " )"
    #if [ "${RESULT}" != "" ]; then
    #    echo "INFO: ${RESULT}"
    #    echo "INFO: create_user test successful."
    #else
    #    echo "ERROR! create_user test failed."
    #    exit 1
    #fi

}









# # add testuser to demo workspaces
# /usr/bin/python3 /usr/local/src/py4dmx/dmx.py -m -w "Qualitative Research Sample Data" -n "testuser"
# /usr/bin/python3 /usr/local/src/py4dmx/dmx.py -m -w "Vegan Cooking Sample Data" -n "testuser"
# /usr/bin/python3 /usr/local/src/py4dmx/dmx.py -m -w "DMX User Guide Sample Data" -n "testuser"

## create a note
#cat <<EOF >/tmp/testuser_note.json
#{ 
#    "typeUri": "dmx.notes.note",
#    "children": {
#        "dmx.notes.title": "About the private workspace",
#        "dmx.notes.text": "This is the first note on the untitled topicmap in the private workspace of the testuser. Only the testuser can read and write content in this workspace. You can find out more about <a href='https://dmx.readthedocs.io/en/latest/user.html#introduction-to-workspaces-and-sharing-modes'>workspaces and their sharing modes</a> in our documentation.</p><br><p>BTW: You <u>can</u> <b>use</b> <i>simple</i> <b>text formatting</b> in the text field of a note.</p>"
#    }
#}
#EOF
#echo -e "\nCreating Testnote:\n$( cat /tmp/testuser_note.json)"
#NOTE="$( IFS=$'\n' /usr/bin/python3 /usr/local/src/py4dmx/dmx.py -l -u "testuser" -p "testpass" -f /tmp/testuser_note.json -w "Private Workspace" )"
#rm /tmp/testuser_note.json

#echo -e "\nCreating Testnote:\n$( cat /tmp/testuser_note.json)"
#NOTE="$( IFS=$'\n' /usr/bin/python3 /usr/local/src/py4dmx/dmx.py -l -u "testuser" -p "testpass" -f /tmp/testuser_note.json -w "Private Workspace" )"
#rm /tmp/testuser_note.json

## reveal note on topicmap
#echo -e "\nReveal Note On Topicmap:\n"
#WS_ID="$( echo "$NOTE" | grep "WS ID = " | tail -n1 | awk -F' ' '{ print $NF }' )"
#echo "WS ID: ${WS_ID}"
## TOPIC_ID="$( echo "$NOTE" | grep "CREATED: " | tail -n1 | awk -F' ' '{ print $NF }' )"
#TOPIC_ID="$( echo "$NOTE" | tail -n1 | awk -F' ' '{ print $NF }' )"
#echo "TOPIC ID: ${TOPIC_ID}"
#TOPICMAP_ID="$( IFS=$'\n' /usr/bin/python3 /usr/local/src/py4dmx/dmx.py -l -u "testuser" -p "testpass" -r ${WS_ID} | grep -A1 -B1 '"dmx.topicmaps.topicmap"' | grep id | tail -n1 | awk -F' ' '{ print $2 }' | sed 's/\,//' )"
#echo "TOPICMAP ID: ${TOPICMAP_ID}"
#BASE64=$( echo -n "testuser:testpass" | base64 )
#curl -s -H "Authorization: Basic ${BASE64}" \
#        -H "Content-Type: application/json" \
#        -H "Cookie: dmx_workspace_id=${WS_ID}" \
#        10.0.1.82:8080/topicmap/${TOPICMAP_ID}/topic/${TOPIC_ID} \
#        -d '{ "dmx.topicmaps.x": 210, "dmx.topicmaps.y": 230, "dmx.topicmaps.visibility": true, "dmx.topicmaps.pinned": true }' >/dev/null





### main ###
echo -e "\nTest:"
create_user
user_login
create_workspace
create_member
create_note
