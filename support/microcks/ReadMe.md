Installation of Microcks - data mocking software.
=================================================

To install Microcks, use the yml config files on the Microcks github site:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
https://github.com/microcks/microcks/tree/master/install/openshift
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the yml file locally. For Lear we used :
openshift-persistent-no-keycloak-template-https.yml

Installing:
-----------

1.  Before you start installing, edit the yml file:

    -   change the keycloak.realm to sbc (or whatever realm you want to use from
        keycloak)

    -   change the keycloak.ssl-required to none.

2.  In openshift, make sure your in the correct project then go to "Add to
    Project"

3.  Select "Import YAML/JSON" from the drop down.

4.  Choose a yml file (openshift-persistent-no-keycloak-template-https.yml)

5.  Fill in some values:

    -   Set host = "mock-lear-tools.pathfinder.gov.bc.ca" or whatever url your
        openshift has. This is the microcks dashboard.

    -   Set keycloak host = "sso-dev.pathfinder.gov.bc.ca" or whatever keycloak
        service you have. This provides security for the site.

6.  Select "Create", this will start all of the image builds and deployments
    needed.

7.  After deployment has started, go to the microcks deployment and under
    "Actions", choose "Edit Health Checks" and turn off the "Readiness" and
    "Liveness" probes. This will cause microcks to re-deploy and make it work
    correctly.

>   \*Can configure these later.

Configure Keycloak:
-------------------

1.  Add client "microcks-app-js" to your keycloak clients.

2.  Edit client "microcks-app-js" adding the host
    ("mock-lear-tools.pathfinder.gov.bc.ca") to the list of Valid Redirect URIs.

3.  Set baseURL=/\* , Admin URL=/ , Web Origins=\* . (The same as other sites)

4.  Set the Access Type = public

5.  Add an user to keycloak and give them the role "admin" (or use your idir).
    This will be the admin account for microcks so someone unauthorized can't
    mess with your mock JSON.
