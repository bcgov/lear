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
- build image (docker build `<path to folder containing dockerfile + bin folder with scripts>` -t `<image name>`
- push image to openshift (I used script from bcdevops repo: https://github.com/BCDevOps/openshift-developer-tools) 
	- ./oc-push-image.sh -i `<image name>` -n `<name space>`

##### Deployment Steps:
- deploy the image 
- go into deployment configuration:
	- remove storage from /ORCL (if automatically created)
	- create pvc with 24G (may be able to use less - 4G is used right away, but CTST + dumpfile = ~22G) and add it for /ORCL
- edit the .yaml for the deployment config
    - add *runAsUser:* `<userid specified in Dockerfile>` under *spec: template: spec: container: securityContext:*
	    - this will set the userid for the container as long as it is an id within the range of your namespace (which you can find with `oc describe project <namespace name>`) and provided the id is not being used
	- add *supplementalGroups: -0 -54321 -54322* under *spec: template: spec: securityContext*
	- ##### NOTE: The two above are in *different* securityContexts
- edit resource limits for the deployment and under *Memory* change *Limit* to 2G
		
### Importing CTST

The steps for importing CTST are:

1. Getting the dumpfile into the container
    - it's too big to include in the image (the container will crash when it tries to deploy it)
    - mount an empty pvc with enough space onto a container and use the `oc rsync` command to upload the dumpfile into it.
    - mount this pvc onto the oracle container (I put it on */import*)
    
2. Setup the blank database for import
    - create test_dir for import within container: `mkdir /ORCL/dumpfs` (do this within the deployed container)
    - connect to the db as sysdba (`$ORACLE_HOME/bin/sqlplus / as sysdba`) and setup the a user for the import:
    
    ```
    CREATE USER c##<username> IDENTIFIED BY <password> DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE temp QUOTA 5M ON system QUOTA UNLIMITED on USERS;
    GRANT CONNECT, RESOURCE, DBA TO c##<username>;
    GRANT CREATE PROCEDURE TO c##<username>;
    GRANT CREATE PUBLIC SYNONYM TO c##<username>;
    GRANT CREATE SEQUENCE TO c##<username>;
    GRANT CREATE SESSION TO c##<username>;
    GRANT CREATE SNAPSHOT TO c##<username>;
    GRANT CREATE SYNONYM TO c##<username>;
    GRANT CREATE TABLE TO c##<username>;
    GRANT CREATE TRIGGER TO c##<username>;
    GRANT CREATE VIEW TO c##<username>;
    GRANT SELECT ANY DICTIONARY to c##<username>;
    GRANT CREATE TYPE TO c##<username>;
    CREATE OR REPLACE DIRECTORY test_dir AS '/ORCL/dumpfs/';
    GRANT READ, WRITE ON DIRECTORY test_dir TO c##<username>;
    exit
    ```

3. Import from the dumpfile 
    - copy the dumpfile into the test_dir folder: `cp /import/<dumpfile> /ORCL/dumpfs`
    - import db: `$ORACLE_HOME/bin/impdp c##<username>/<password> schemas=COLIN_MGR_TST REMAP_SCHEMA=COLIN_MGR_TST:c##<username> REMAP_TABLESPACE=COLIN_TAB:USERS REMAP_TABLESPACE=COLIN_IDX:USERS directory=TEST_DIR dumpfile=<dumpfile>.dmp logfile=impdpCTST.log`