#!/usr/bin/env bash
# 
# Top level script to launch OpenMPI program on top of Mesos
# Usage: ./ompirun.sh PATH_TO_MESOS_PROJECT MESOS_MASTER
#        Assume Mesos build dir is PATH_TO_MESOS_PROJECT/build/
#
# This script does:
# 1. Find the eggs from MESOS_BUILD_DIR
# 2. Call Mesos framework mrun.py
if [ $# -ne 2 ]; then
 echo "Usage: ./mrun.sh  PATH_TO_MESOS_PROJECT "
 echo "Assume build dir is PATH_TO_MESOS_PROJECT/build/"
 exit
fi
MESOS_SOURCE_DIR=$1
MESOS_BUILD_DIR=$MESOS_SOURCE_DIR/build
MESOS_MASTER=$2
echo "Find eggs in ${MESOS_SOURCE_DIR}"
# Use colors for errors.
. ${MESOS_SOURCE_DIR}/support/colors.sh

# Force the use of the Python interpreter configured during building.
test ! -z "${PYTHON}" && \
  echo "${RED}Ignoring PYTHON environment variable (using /usr/bin/python)${NORMAL}"

PYTHON=/usr/bin/python

SETUPTOOLS=`echo ${MESOS_BUILD_DIR}/3rdparty/setuptools-*/`

# Just warn in the case when build with --disable-bundled.
test ! -e ${SETUPTOOLS} && \
  echo "${RED}Failed to find ${SETUPTOOLS}${NORMAL}"

PROTOBUF=`echo ${MESOS_BUILD_DIR}/3rdparty/protobuf-*/python/`

test ! -e ${PROTOBUF} && \
  echo "${RED}Failed to find ${PROTOBUF}${NORMAL}"

MESOS_EGGS=$(find ${MESOS_BUILD_DIR}/src/python/dist -name "*.egg" | tr "\\n" ":")

export PYTHONPATH="${SETUPTOOLS}:${PROTOBUF}:${MESOS_EGGS}"
python /ws/ompirun.py  -n 4  --docker_image=ubuntu:orted -v master@$MESOS_MASTER /ws/a.out
