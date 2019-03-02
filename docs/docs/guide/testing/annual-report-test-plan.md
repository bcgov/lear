# Annual Report Test Plan

## Features to be tested

### Login
More for Relationships team, but our app must handle presentation of appropriate messages  
- Valid login  
- Invalid login  
- Connectivity failed  

### Dashboard
Pending implementation details but could include the following:  
- View list of your coops (and other entities?)  
- View a single coop  
- Single coop status/tombstone  
- Single coop filing history/ledger  

### Annual Report Flow
Enter/confirm AGM date, registered office address, and current list of directors.
If a director is added/removed then a NOC Directors filing is also ledgered.
If the registered office address is changed then a NOC Registered Office Address filing is also ledgered.

**Inputs**  
Data of Financial Year End  
- Don’t believe this is editable? TBC  

**AGM Date**  
- Confirm which date range is valid?  
- When multiple are outstanding, does the correct one come up first? 
- Confirm that the correct list of directors is presented based on AGM date entered. 

**Registered Office Physical Address for COOP**  
- Must be a physical address  
- Many variations  


**List of directors**  
- One director must be BC resident  
- "Majority" must be "ordinarily" resident of Canada  
- Min 1 / Max ?  
- Appointment Date for new directors
- Cessation Date for anyone that is ceased
- When changed as part of AR filing, date of change = AGM date (must not be in the future)
- When completed as a stand-alone filing, a date of change is entered by client (must not be in the future)

**Certification check-box or similar**  
Depends on how it's implemented

### Review outputs (certified docs., receipts, confirmation emails, et c.)  
- Should be set up so that we can trigger the letters without completing a filing  

### Payment
More for Relationships team, but our app must handle presentation of appropriate messages  
- Approved  
- Declined  
- Invalid/expired  
- Connectivity failed  

### Features not to be tested
1. Internal details of authentication  
2. Internal details of payment  
  
The coops application will use these external services, but their inner workings will not be tested by the entity team. Success and failure paths must be tested from the coops side to confirm that the correct user-facing messages are presented.
  
### Resources
Link to test data/credentials  
Link to test URLs  

### General comments
- Validating addresses and saving director data will be the biggest challenges with this filing.
- Performance testing should be part of the e2e suite from the beginning
- We should rely heavily on test fixtures to handle the many variations present in address and director data.
- QA resource to work with business to define test data for the fixtures.