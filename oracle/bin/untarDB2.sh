#!/bin/sh
#
# $Header: dbaas/docker/build/dbsetup/setup/untarDB.sh rduraisa_docker_122_image/4 2017/03/02 13:26:10 rduraisa Exp $
#
# untarDB.sh
#
# Copyright (c) 2016, 2017, Oracle and/or its affiliates. All rights reserved.
#
#    NAME
#      untarDB.sh - untar database bits and tarball
#
#    DESCRIPTION
#      untar and remove DB bits
#
#    NOTES
#      run as root
#
#    MODIFIED   (MM/DD/YY)
#    rduraisa    03/02/17 - Modify scripts to build for 12102 and 12201
#    xihzhang    10/25/16 - Remove EE bundles
#    xihzhang    09/06/16 - Optimize build
#    xihzhang    06/14/16 - Add EE edition
#    xihzhang    05/23/16 - Creation
#

echo `date`

# basic parameters
SETUP_DIR=/home/oracle/setup
LOG_DIR=$SETUP_DIR/log
BITS_DIR=/tmp/dbsetup/dbtar
DB_BIT=$BITS_DIR/db12.2.0.1.0.tar.gz
DBF_BIT=$BITS_DIR/dbf_12201.tar.gz
ORACLE_HOME=/u01/app/oracle/product/12.2.0/dbhome_1

if [[ $EXISTING_DB = true ]];
then
  echo "External DB Files Exist. Setup DB Install area and startup database instance"
  tar -zxf $DB_BIT -C / 2>&1
else
  echo "External DB Files don't Exist. Setup DB Install area, Copy DB files and startup database instance"

  # create directory
  mkdir -p /u01 /u02 /u03 /u04

  # DB bits
  tar -zxf $DB_BIT -C / 2>&1 &
  tar -zxf $DBF_BIT -C /ORCL 2>&1 &

  # wait for the tar operation to complete
  wait

fi

# end
