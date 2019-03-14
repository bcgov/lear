#!/bin/sh
#
# $Header: dbaas/docker/build/dbsetup/setup/startupDB.sh rduraisa_docker_122_image/2 2017/03/02 13:26:09 rduraisa Exp $
#
# startupDB.sh
#
# Copyright (c) 2016, 2017, Oracle and/or its affiliates. All rights reserved.
#
#    NAME
#      startupDB.sh - startup database
#
#    DESCRIPTION
#      <short description of component this file declares/defines>
#
#    NOTES
#      run as learDev or root
#
#    MODIFIED   (MM/DD/YY)
#    rduraisa    03/02/17 - Modify scripts to build for 12102 and 12201
#    xihzhang    10/25/16 - Remove EE bundles
#    xihzhang    05/23/16 - Creation
#

# check user
USER=`whoami`
if [ "$USER" == "root" ]
then
    su - oracle <<EOF
    /bin/bash /home/oracle/setup/startupDB2.sh
EOF
exit 0
fi

if [ "$USER" != "learDev" ]
then
    echo "StartupDB.sh needs to be executed by user : learDev"
    echo "Please switch user and try again"
    exit 1
fi

# basic parameters
BASH_RC=/home/oracle/.bashrc
source ${BASH_RC}

# logfile
START_LOG=/home/oracle/setup/log/startupDB.log
echo `date`
echo `date` >> $START_LOG

# startup db
echo "start database"
echo "start database" >> $START_LOG
sqlplus / as sysdba  2>&1 >> $START_LOG <<EOF
startup;
exit;
EOF

# start listener
echo "start listener"
echo "start listener" >> $START_LOG
lsnrctl start  >> $START_LOG

echo "The database is ready for use ."
echo "" >> $START_LOG

# end

