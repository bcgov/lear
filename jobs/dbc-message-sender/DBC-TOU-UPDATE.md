## BC Wallet Digital Business Card Terms-of-Use Update Instructions
Run to send a message to connections indicating the Digital Business Card terms of use has been updated. Takes a list of Connection IDs and sends messages through Traction to each connection

The user with the BC Wallet (provided they have not uninstalled the app or deleted the connection) will get a message (see screenshots) indicating the ToU has been updated and where they can find it. Receivers will include active connections:
- Where the credential is in "issued" state
- Where the credential is not revoked
- Users with multiple credentials (for more than 1 business for example) will not recieve duplicate messages
So anyone in a state where they would need to come back and get a new DBC (revoked, or deleted their app) would just see the new ToU when coming back to the BCROS system anyways.

These instructions could be tweaked to accommodate other messaging needs if desired. **At this point there are a low enough number of DBC issued users that the script can just accommodate looping through. If this needs to be done and the count is getting to the 10s/100s of thousands or anything, consider other architecture, or run this in batches**

#### Get List of connection IDs
The script takes in a list of connection IDs for Traction connections to send a message to.

In the DBC TOU update use case that corresponds to the conditions listed above. To get the list of IDs corresponding to relevant BC Wallet users, can get someone who is able to query the business database in the production environment to run this query:

```sql
SELECT DISTINCT ON (u.id) dcn.connection_id, u.id
FROM dc_credentials dc
INNER JOIN dc_business_users dbu ON dbu.id = dc.business_user_id
INNER JOIN users u ON dbu.user_id = u.id
INNER JOIN dc_connections dcn ON dcn.business_user_id = dbu.id
WHERE dc.is_issued = true
AND dc.is_revoked = false
-- AND dc.date_of_issue < ('2025-07-24 15:16:00' AT TIME ZONE 'America/Los_Angeles')  -- can include a date range
ORDER BY u.id, dcn.connection_id;
```

(can adjust as needed for different conditions, like including a date range etc, if different requirements ever come up)

Take the connection IDs column and copy into the `connections.txt` file that the script will use.

Should just be one ID per line, so the file should just look like

```
abc-123
xyz-456
... etc
```

#### Get Traction credentials
Use the production Traction URL, Tenant ID, and API key. These for production can be found in 1password vault, or gotten from the Business-API YAML.

#### Set up config
In the `message-sender.py` script set the URL and credentials. Set the input and output file names desired (or leave defaults). Set the message text you wish to send. For a ToU update it would be something like:

```
Hello, this is update you that the Digital Business Card Terms of Use has been updated. You can find the new TOU by logging in to your Registries Dashboard or visiting https://www2.gov.bc.ca/gov/content/employment-business/business/managing-a-business/permits-licences/digital-business-card-terms-of-use
```

See the "Configuration" section in the README for config descriptions

#### Run script

Ensure config values are right, requirements are installed (see README), and execute the script.

Progress will log out as the script runs. An audit file will be created at the end.