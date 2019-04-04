# Installation of Postgres using parameterized templates. #


In the file postgresql-build.lear.param, the git repo url is defined and used, so this must exist in github to work.



## Build postgres image ##

1) Login to openshift, change project to tools. 

2) In the command line, navigate to local directory (eg project: lear in windows "c:/Data/Projects/lear/lear-db" )

3) Configure build parameters to be correct. See '.param' files.

4) Run command to build image:  

	oc process -f openshift\templates\postgresql-build.json --param-file=openshift\postgresql-build.lear.param | oc create -f -

5) Tag the image properly:
   oc tag gl2uos-tools/postgresql gl2uos-tools/postgresql:latest


## Deployment to dev environment ##

6) Tag image for dev deploy:

     oc tag gl2uos-tools/postgresql:latest gl2uos-tools/postgresql:dev
   
7) Change project to dev 

8) Configure deployment parameters to be correct. Parameters like image tag, user name and password, etc.

9) Deploy the image to dev environment.
  	
        oc process -f openshift\templates\postgresql-deploy.json --param-file=openshift\postgresql-deploy.lear.dev.param | oc create -f -

   
## Deploy to test and prod environments - Repeat steps 6 to 9 ##


#### Tag image command examples. ####   
      
   test:    oc tag gl2uos-tools/postgresql:latest gl2uos-tools/postgresql:test     
   
   prod:    oc tag gl2uos-tools/postgresql:latest gl2uos-tools/postgresql:prod  
     
   
#### Deploy command examples. ####  
   
   test:    oc process -f openshift\templates\postgresql-deploy.json --param-file=openshift\postgresql-deploy.lear.test.param | oc create -f -
    	
   prod:    oc process -f openshift\templates\postgresql-deploy.json --param-file=openshift\postgresql-deploy.lear.prod.param | oc create -f -
   