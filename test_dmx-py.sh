#!/bin/bash

if [ "$1" == "-v" ]; then
    VERBOSE='-v'
else
    VERBOSE=""
fi

PY4DMX='./dmx.py'
# NUNC="$( date +"%F_%T" )"
# ':' in WS NAME is a problem when creating a topic!
NUNC="$( date +"%F_%H-%M-%S" )"
USER="User_${NUNC}"
# PASS="$( pwgen -sn 25 1 )"
PASS="$( pwgen -syn 25 1 | sed s'/\%/\-/g' | sed s'/\:/\_/g' | sed s'/\"/\+/g')"
PASS="$( pwgen -sn 25 1 )"
WORKSPACE="WS_${NUNC}"
WORKSPACE_TYPE='collaborative'
TOPICMAP="MAP_${NUNC}"
NOTE_FILE='./note_example.json'
PERSON_FILE='./person_example.json'
VCARD_FILE='./person_example.vcf'

create_user () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new user '${USER}' with password '${PASS}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -C -u "${USER}" -p "${PASS}" )"
    echo "${RESULT}"
}

user_login () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Login new user '${USER}' with password '${PASS}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -s -u "${USER}" -p "${PASS}" )"
    JSESSIONID=${RESULT}
    echo "${RESULT}"
}

test_session_id () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Login with existing sessionid ${JSESSIONID}."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -J ${JSESSIONID} -s )"
    echo "${RESULT}"
}

create_workspace () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new workspace '${WORKSPACE}' with sharing mode '${WORKSPACE_TYPE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -w "${WORKSPACE}" -T "${WORKSPACE_TYPE}" )"
    WORKSPACE_ID=$( tail -n1 <<< ${RESULT} )
    echo "${RESULT}"
}

create_member () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new workspace member '${USER}' in '${WORKSPACE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -m -w "${WORKSPACE}" -n "${USER}" )"
    echo "${RESULT}"
}

create_note () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new note ${NOTE_FILE} as user '${USER}' in workspace '${WORKSPACE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -l -u ${USER} -p ${PASS} -f ${NOTE_FILE} -w ${WORKSPACE} )"
    NOTE_ID=$( tail -n1 <<< ${RESULT} )
    echo "${RESULT}"
}

create_person () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new person topic ${PERSON_FILE} as user '${USER}' in workspace '${WORKSPACE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -l -u ${USER} -p ${PASS} -f ${PERSON_FILE} -w ${WORKSPACE} )"
    PERSON_ID=$( tail -n1 <<< ${RESULT} )
    echo "${RESULT}"
}

create_topicmap () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Creating new topicmap in workspace '${WORKSPACE}'."
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -l -u ${USER} -p ${PASS} -M "${TOPICMAP}" -w "${WORKSPACE}" )"
    TOPICMAP_ID=$( tail -n1 <<< ${RESULT} )
    echo "${RESULT}"
}

reveal_topic () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Revealing topic ${NOTE_ID} on ${TOPICMAP} in workpace ${WORKSPACE}".
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -l -u ${USER} -p ${PASS} -R -i ${NOTE_ID} -o ${TOPICMAP_ID} -x 150 -y 150 -P True -w ${WORKSPACE} )"
    echo "${RESULT}"
}
import_vcard () {
    echo -e "--\n${FUNCNAME[0]}:"
    if [ ${VERBOSE} ]; then
        echo "INFO: Importing person topic from vcard ${VCARD_FILE} in workpace ${WORKSPACE}".
    fi
    RESULT="$( ${PY4DMX} ${VERBOSE} -l -u ${USER} -p ${PASS} -V ${VCARD_FILE} -w ${WORKSPACE} )"
    echo "${RESULT}"
}

### main ###
echo -e "\nRun Tests:"
create_user
user_login
test_session_id
create_workspace
create_member
create_note
create_person
create_topicmap
reveal_topic
import_vcard
