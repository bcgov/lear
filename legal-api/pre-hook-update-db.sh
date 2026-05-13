#! /bin/sh
COMMAND=${1:-upgrade}
REVISION=${2:-}
echo starting $COMMAND $REVISION
export DEPLOYMENT_ENV=migration
flask db $COMMAND $REVISION
