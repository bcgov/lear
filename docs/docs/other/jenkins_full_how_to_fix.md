
# Problem
Pipelines in Openshift aren't running. You have determined it's because the Jenkins storage is full.

**How did you determine this?**
The Jenkins pod log has a java error, which (among other things) says "Caused by: java.io.IOException: No space left on device".

**Where is the Jenkins pod?**
In the LEAR (tools) namespace; the pod is called jenkins-x-xxxxx
[https://console.pathfinder.gov.bc.ca:8443/console/project/gl2uos-tools/browse/pods](https://console.pathfinder.gov.bc.ca:8443/console/project/gl2uos-tools/browse/pods)

# Solution

## Clear out Jenkins storage (immediate solution)
1. Go into a terminal in the Jenkins pod in openshift.
2. go to folder that contains the job logs:
```cd /var/lib/jenkins/jobs/gl2uos-tools/jobs```
3. get list of pipelines in order of most used resources:
```du -csh * | sort -hr```
4. delete all numbered folders, ie: builds:
```ls | grep -P [0-9]+ - | xargs rm -rf L1```

## Decrease number of jenkins runs logged (longer term solution)
If this happens too often, decrease the number of jenkins "builds" (pipeline runs) stored in logs.

 1. Go to Jenkins [https://jenkins-gl2uos-tools.pathfinder.gov.bc.ca/](https://jenkins-gl2uos-tools.pathfinder.gov.bc.ca/)
 2. For each of the gl2uos-tools folders (pipelines), go to Configure > General (tab). Check "discard old builds", and set to a lower number. As of 2019-11-13 this number is 2 for simple (non-build) pipelines and 4 for build pipelines. Previously it was either unset (unlimited) or 10.
