**Prerequisites**  
 - Oracle client installed on your machine (Oracle InstantClient is suggested)     
 - Make (not required but ideal)    
 - openshift access to LEAR dev  
 - have the dev requirements installed, in addition to the prod requirements  
   > pip install -r requirements/dev.txt   
    
**Unit tests**  
1. Refresh the oracle-dev pod in LEAR dev namespace, using the pipeline "oracle-dev-refresh-pipeline"   
   - this restarts the oracle database in the pod with data in a set state; takes 5-10 minutes.  
2. port-forward to the oracle-dev pod  
   > oc port-forward oracle-dev-xxx-xxxxx 1111:1521  
3. set the TEST_ORACLE_* settings in .env to connect to this port-forwarded oracle pod on port 1111 (or whichever port you chose in step 2)  
4. run the pytests either through your development tool's UI, or via the command line:  
   > pytest  
  
Note - multiple runs will possibly yield different results after the first one.    
    
**Postman tests**  
1. Do same steps above to get oracle-dev pod refreshed and port-forwarded (steps 1-3)  
2. In postman, import the postman test suite from tests/postman  
3. In postman, import the postman environment for local testing  
4. Run the colin API; optionally set port if you do not want the default 5000  
   > flask run --port=xxxx  
5. check that the settings are correct by executing the first test first - basically a health check  
6. run the complete suite of postman tests; these will change the data so after the first run, subsequent runs will fail.