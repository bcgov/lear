# Investigating Entity Filer errors

This document contains various troubleshooting steps that you can follow to
identify and resolve `entity-filer` errors (eg, stuck filings).

These steps are common across Dev/Test/Prod environments.

## Identifying Errors

- check Sentry logs
- check Openshift logs

### Sentry

 1. open target project (eg, "entity-dev")
 2. click on errors to see details
 3. look at task traces if available
 4. identify the reported error
 5. note the event date-time

### Openshift

1. open target project (eg, "LEAR (dev)")
2. open Applications -> Pods
3. watch for invalid statuses
4. click pod name for details (eg", entity-filer-dev-xxx-yyy")
5. click Metrics tab
   - what to look for?
6. click Logs tab
   - look for ERRORs at the date-time reported in Sentry

- how to force a new pod creation?
- etc

## Resource Utilization Issues

- how to check full memory?
- how to check full db?
- etc

## Reset Pipelines

- where and what are these?
- how do you use these?
- what else needs to be done:
   - delete all rows in colin-event-id table?
- what about resetting the queue?
- what about cleaning up Postgres (Lear) db?
- how to deal with corp num collisions?
- other collisions?
- etc

## Clearing the Queue
_how?_

## Fixing Data
_future_

# Contacts

- who to contact for various issues?
- OPS contact?
- COLIN db contact?
- Openshift (devops) contact? or Rocketchat channel?

# References

- [Sentry](https://sentry.io/organizations/registries/projects/)
- [Openshift](https://console.pathfinder.gov.bc.ca:8443/console/projects)
- [Entity docs](https://github.com/bcgov/entity/tree/master/docs)
- [Lear docs](https://github.com/bcgov/lear/tree/master/docs)
- direct links to architecture diagrams?
- direct links to HOWTOs?
- etc
