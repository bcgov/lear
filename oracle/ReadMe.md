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
	    - copy needed setup/password scripts edited for new user into container
	    - set permissions for all folders and files needed
	    - set user to one we created
	    - run password add script
	    - expose port
	    - run init script to setup oracle
	    - will have local permission issues with /ORCL, but this won’t be the case in openshift
- build image (docker build `<path to folder containing dockerfile + bin folder with scripts>` -t `<image name>`)
- push image to openshift (I used script from bcdevops repo: https://github.com/BCDevOps/openshift-developer-tools) 
	- ./oc-push-image.sh -i `<image name>` -n `<name space>`
- ##### NOTE: Each environment will need its own image built from a different dockerfile because each one has it's own set of user ids available (i.e. the uid=1003919999 exists in 'tools' but not 'dev')

##### Deployment Steps:
- deploy the image 
- go into deployment configuration:
	- remove storage from /ORCL (if automatically created)
	- create 2 pvcs with 24G for /ORCL and /ORCL_base
	    - the 2nd one on /ORCL_base is used to keep a copy of the original data (this is how we ensure a baseline for all our tests)
- edit the .yaml for the deployment config
    - add *runAsUser:* `<userid specified in Dockerfile>` under *spec: template: spec: containers: securityContext:*
	    - this will set the userid for the container as long as it is an id within the range of your namespace (which you can find with `oc describe project <namespace name>`) and provided the id is not being used
	- add *supplementalGroups: -0 -54321 -54322* under *spec: template: spec: securityContext*
	- ##### NOTE: The two above are in *different* securityContexts
- edit resource limits for the deployment and under *Memory* change *Limit* to 2G
    - For faster performance I raised the limit on *Cores* = 2 and *Memory* = 8G
- add environment variables:
    - ORACLE_SID = ORCLCDB
    - ORACLE_PDB = oracle1
		
### Importing CDEV

The steps for importing CDEV are:

1. Getting the dumpfile into the container
    - it's too big to include in the image (the container will crash when it tries to deploy it)
    - mount an empty pvc with enough space onto a container and use the `oc rsync <source> <oracle-pod-name>:<destination>` command to upload the dumpfile into it.
    - mount this pvc onto the oracle container (I put it on */import*)
    
2. Setup the blank database for import
    - create test_dir for import within container: `mkdir /ORCL/dumpfs` (do this within the deployed container)
    - connect to the db as sysdba (`$ORACLE_HOME/bin/sqlplus / as sysdba`) and setup the a user for the import:
    
    ```
    CREATE USER c##cdev IDENTIFIED BY tiger DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE temp QUOTA 5M ON system QUOTA UNLIMITED on USERS;
    GRANT CONNECT, RESOURCE, DBA TO c##cdev;
    GRANT CREATE PROCEDURE TO c##cdev;
    GRANT CREATE PUBLIC SYNONYM TO c##cdev;
    GRANT CREATE SEQUENCE TO c##cdev;
    GRANT CREATE SESSION TO c##cdev;
    GRANT CREATE SNAPSHOT TO c##cdev;
    GRANT CREATE SYNONYM TO c##cdev;
    GRANT CREATE TABLE TO c##cdev;
    GRANT CREATE TRIGGER TO c##cdev;
    GRANT CREATE VIEW TO c##cdev;
    GRANT SELECT ANY DICTIONARY to c##cdev;
    GRANT CREATE TYPE TO c##cdev;
    CREATE OR REPLACE DIRECTORY test_dir AS '/ORCL/dumpfs/';
    GRANT READ, WRITE ON DIRECTORY test_dir TO c##cdev;
    exit
    ```

3. Import from the dumpfile 
    - copy the dumpfile into the test_dir folder: `cp /import/<dumpfile> /ORCL/dumpfs`
    - import db: `$ORACLE_HOME/bin/impdp c##cdev/tiger schemas=COLIN_MGR_DEV REMAP_SCHEMA=COLIN_MGR_DEV:c##cdev REMAP_TABLESPACE=COLIN_TAB:USERS REMAP_TABLESPACE=COLIN_IDX:USERS directory=TEST_DIR dumpfile=cdev_20190621.dmp logfile=impdpCDEV.log`
    - ##### NOTE: There will be several failures in the logs - this is expected
    - after import finishes connect via sql developer and delete failing EVENT/FILING triggers (there should be 1 FILING trigger that still works)

4. Clean up
    - remove the /ORCL/dumpfs folder (no longer needed)
        - *rm -r /ORCL/dumpfs*
    - shutdown the database
        - *$ORACLE_HOME/bin/sqlplus / as sysdba*
        - *database shutdown*
    - create a copy of the /ORCL folder into /ORCL_base (used to refresh the data on each deploy from the pipeline)
        - *cp -a /ORCL/. /ORCL_base/*
    - in the deployment configuration unmount the pvc containing the import (no longer needed)
