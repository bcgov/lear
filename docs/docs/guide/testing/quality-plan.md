# Quality Plan
This is the high-level for the COOP registries application. This platform will later be used to host all entity types. Current MVP is limited to Annual Report, Change of Address and Change of Director filings.

### Philosophy 
Testing aims to catch unexpected behaviour before code is moved into production. Effort-wise it is 'cheaper' to catch issues as early as possible. A developer should be able to write the first tests based off of the Acceptance Criteria in the ticket. If the Acceptance Criteria are unclear, then clarify what you need prior to starting the task. From there, the normal testing pyramid applies - cover as much as possible with unit and integration tests, then add manual and browser-level end-to-end tests.  

The highest value (read: most tests) should be placed on securing the legacy database, and on the quality of the user experience.

Testing and quality go beyond writing tests. As much as possible, design code that can be tested easily. For example, the main UI controls should have coherently named IDs for easy browser automation. APIs should be designed to return extra details about downstream outcomes to ease testing. Layering in tracing as early as possible also helps with detecting issues as quickly as possible after code is deployed into production.

Having an extensive test suite is important, but it is also important that all resources know how to run the tests. Ideally, the deployment pipelines would run all tests that are available for each component of the application. Pre-commit testing is being planned and reviewed so that as many tests as possible can be run locally prior to moving into the dev environment. Pending link to section describing local dev setup for testing

Manual testing will be completed by both devs and QA resource(s). Repetitive manual tests, or tests that require long set-up/complex test data should considered candidates for future automation.

### Roles
Developers will write unit and integration tests for each pull request they work on. They will also put in place test fixtures and other test apparatus needed to run tests at all layers.
QA resource(s) will expand existing test suites as needed with a focus on end-to-end tests. QA will work to define when code is ready to be released into production. 

### Pre-release checklist
Prior to moving into production, the following steps should be completed or confirmed:
1. Update version number in the code being released
2. Create a draft release in GitHub and confirm the correct commits are present
3. Dev to send commit list to QA (or otherwise publish changelog)
4. QA to schedule the release with staff/clients (daytime's best or when staff are available for rollback)
5. All dev/test pipeline test suites green
6. Dev/QA chat to plan prod verification testing (unless already automated)
7. Release the code to production and complete prod verification
8. Finalise/publish the release in GitHub, tagging it