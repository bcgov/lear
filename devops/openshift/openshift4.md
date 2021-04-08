
Openshift 4 Migration:

Pre:

1. Modify dc.yaml, pipeline.yaml, bc.yaml and *.jenkins
2. Copy configmap or secret from OCP3 to OCP4 for each application
3. Create rocketchat secret in tools namepsace

Tools Namespace:

1. Create artifactory creds through this https://github.com/BCDevOps/OpenShift4-Migration/issues/51

2. Install Jenkins from Openshift Catalog;

3. RBAC and Network Security Policies:
    ```
	cd devops
	oc delete externalnetwork,networksecuritypolicy  -n 6e0e49-tools -l app=sbc-auth
	oc process -f openshift/templates/tools-image-puller-rbac.yaml -o yaml | oc apply -f - -n 6e0e49-tools
    oc process -f openshift/templates/tools-jenkins-rbac.yaml -o yaml | oc apply -f - -n 6e0e49-tools
    oc process -f openshift/templates/tools-nsp.yaml -o yaml | oc apply -f - -n 6e0e49-tools
    ```

4. BuildConfig, ImageStream and Pipeline for each application:
    ```
	cd `project folder`
	oc delete dc,bc,is,networksecuritypolicy  -n 6e0e49-tools -l app=`application name`
	oc process -f openshift/templates/bc.yaml -o yaml | oc apply -f - -n 6e0e49-tools
	oc process -f openshift/templates/pipeline.yaml -p TAG=`env name dev/test/prod` -o yaml | oc apply -f - -n 6e0e49-tools
    ```

Dev/Test/Prod Namespace:

1. Install database:
    ```
	cd db
	oc delete all,svc,route,dc,secret,networksecuritypolicy,persistentvolumeclaim -n 6e0e49-dev -l app=postgresql-keycloak
	oc process -f openshift/templates/keyclaok-db.yaml -o yaml | oc apply -f - -n 6e0e49-dev

	oc delete all,svc,route,dc,secret,networksecuritypolicy,persistentvolumeclaim -n 6e0e49-dev -l app=postgresql
	oc process -f openshift/templates/auth-db.yaml -o yaml | oc apply -f - -n 6e0e49-dev

	oc delete all,svc,route,dc,secret,networksecuritypolicy,persistentvolumeclaim -n 6e0e49-dev -l app=postgresql-notify
	oc process -f openshift/templates/notify-db.yaml -o yaml | oc apply -f - -n 6e0e49-dev
    ```

2. 	RBAC and Network Security Policies:
    ```
	cd devops
	oc delete externalnetwork,networksecuritypolicy  -n 6e0e49-dev -l app=sbc-auth
    oc process -f openshift/templates/jenkins-edit-rbac.yaml -o yaml | oc apply -f - -n 6e0e49-dev
	oc process -f openshift/templates/nsp.yaml -o yaml | oc apply -f - -n 6e0e49-dev
    ```

3. Keycloak
    ```
	cd keycloak
	oc delete all,svc,route,dc,networksecuritypolicy,secret -n 6e0e49-dev -l app=auth-keycloak
    oc process -f openshift/templates/dc.yaml -p TAG=dev -o yaml | oc apply -f - -n 6e0e49-dev
    ```

4. Deploymentconfig
    ```
    cd `project folder`
    oc delete all,svc,route,dc,networksecuritypolicy,secret -n 6e0e49-dev -l app=
    oc process -f openshift/templates/dc.yaml -p TAG=dev -o yaml | oc apply -f - -n 6e0e49-dev
    # manually modify yaml to add the env section into dc (copy it from OCP3)
    ```

5. Data Migration
    1) [install pvc migrator in both OCP3 and OCP4](https://github.com/BCDevOps/StorageMigration/blob/master/CrossClusterDataSteps.md)
    3) OCP4:
        #### Create all the roles that exits in OCP3 db
        ```
        CREATE ROLE auth;
        CREATE ROLE notify;
        CREATE ROLE notifytester;
        CREATE ROLE notifyuser;
        CREATE ROLE postgres;
        CREATE ROLE tester;
        ```
        #### mount db pvc to PVC Migrator
        #### startup PVC Migrator service
    2) OCP3:
        #### Stop all connect to db Applications
        #### Backup
        #### If upgrade postgres: Dump data:
        ```
        pg_dumpall -U postgres -h localhost -p 5432 > /var/lib/pgsql/data/dump/dumpall.sql
        ```
        #### Stop database
        #### Mount db pvc to PVC Migrator
        #### Startup PVC Migrator
        #### Copy userdata foler(or dumpall.sql) to target folder
        #### Stop PVC Migrator
    3) OCP4:
        #### Stop PVC Migrator
        #### Startup db
        #### If upgrade postgres
        ```
        psql -U postgres -W -f /path/dumpall.sql
        ```
        #### Double check the secret

6. Backup
    ```
	cd db/backup
	oc delete all,svc,route,dc,secret,networksecuritypolicy,persistentvolumeclaim -n 6e0e49-dev -l app=backup
	oc process -f backup.yaml -p TAG=dev -p TAG_UPPER=DEV -o yaml | oc apply -f - -n 6e0e49-dev
    ```



