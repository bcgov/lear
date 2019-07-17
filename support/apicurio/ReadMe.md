Installation of Apicurio - data mocking software.
=================================================

To install Apicurio, use the yml config files on the github site:

You will need a postgres database previously installed to use this.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
https://github.com/Apicurio/apicurio-studio/tree/master/distro/openshift
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the yml file locally. For Lear we used : apicurio-template.yml

Installing:
-----------

1.  Before you start installing, edit the yml file:

    -   change the keycloak.realm to sbc (or whatever realm you want to use from
        keycloak)

    -   change the keycloak.ssl-required to none.

2.  In openshift, make sure your in the correct project then go to "Add to
    Project"

3.  Select "Import YAML/JSON" from the drop down.

4.  Choose a yml file (apicurio-template.yml)

5.  Fill in some values:

    -   Set database parameters: PostgreSQL Connection Username / Password

    -   Set host = "mock-lear-tools.pathfinder.gov.bc.ca" or whatever url your
        openshift has. This is your apicurio home page.

    -   Authentication Route Name: Set keycloak host =
        "sso-dev.pathfinder.gov.bc.ca" or whatever keycloak service you have.
        This provides security for the site.

    -   Keycloak Admin Username/ Password

6.  Select "Create", this will start all of the image builds and deployments
    needed.

7.  After deployment has started, go to the apicurio deployment and under
    "Actions", choose "Edit Health Checks" and turn off the "Readiness" and
    "Liveness" probes. This will cause apicurio to re-deploy and make it work
    correctly.

>   \*Can configure these properly later.
