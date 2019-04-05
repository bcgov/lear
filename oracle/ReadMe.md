## Oracle Container

We have oracle running in our lear dev namespace. To deploy an oracle image you need to:
 - layer the original docker image because you cannot run the container as the oracle or root userid in our openshift environment
 - edit the deployment storage and set to run as a specific userid

#### How to layer the image and deploy successfully:
##### Image Steps: 
- get the oracle 12.2.0.1 enterprise docker image
- once in openshift can’t run as root or oracle user so you will have permission errors that cause the container to fail. Solution: layer image by creating a new dockerfile.
    - ##### Dockerfile:
	    - pull oracle image
	    - set user as root
	    - add a new user that we can set in deployment config (highest one available in lear dev namespace should always be available because default is lowest one not used) and add to groups
	    - copy needed setup/password scripts edited for new user into container, set permissions for all folders and files needed, set user to one we created, run password add script, expose port, run init script to setup oracle
	    - will have local permission issues with /ORCL, but this won’t be the case in openshift
- build image (docker build <path to folder containing dockerfile + bin folder with scripts> -t <image name>
- push image to openshift (I used script from bcdevops repo: https://github.com/BCDevOps/openshift-developer-tools) 
	- ./oc-push-image.sh -i `<image name>` -n `<name space>`

##### Deployment Steps:
- deploy the image 
- go into deployment configuration:
	- remove storage from /ORCL (if automatically created)
	- create pvc with 8G (may be able to use less - 4G is used right away) and add it for /ORCL
- edit the .yaml for the deployment config and add *runAsUser:* `<userid specified in Dockerfile>` under *spec: template: spec: container: securityContext:*
	- this will set the userid for the container as long as it is an id within the range of your namespace (which you can find with `oc describe project <namespace name>`) and provided the id is not being used
- edit resource limits for the deployment and under *Memory* change *Limit* to 2G
		
