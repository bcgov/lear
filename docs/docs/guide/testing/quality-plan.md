# Quality Plan
This is the high-level quality plan for the COOP registries application. This platform will later be used to host all entity types. Current MVP is limited to Annual Report, Change of Address and Change of Director filings.

### Philosophy 
Testing aims to catch unexpected behaviour before code is moved into production. Effort-wise it is 'cheaper' to catch issues as early as possible. A developer should be able to write the first tests based off of the Acceptance Criteria in the ticket. If the Acceptance Criteria are unclear, then clarify what you need prior to starting the task. From there, the normal testing pyramid applies - cover as much as possible with unit and integration tests, then add manual and browser-level end-to-end tests.  

The highest value (read: most tests) should be placed on securing the legacy database, and on the quality of the user experience.

Testing and quality go beyond writing tests. As much as possible, design code that can be tested easily. For example, the main UI controls should have coherently named IDs for easy browser automation. APIs should be designed to return extra details about downstream outcomes to ease testing. Layering in tracing as early as possible also helps with detecting issues as quickly as possible after code is deployed into production.

Having an extensive test suite is important, but it is also important that all resources know how to run the tests. Ideally, the deployment pipelines would run all tests that are available for each component of the application. Pre-commit testing is being planned and reviewed so that as many tests as possible can be run locally prior to moving into the dev environment. Pending link to section describing local dev setup for testing

Manual testing will be completed by both devs and QA resource(s). Repetitive manual tests, or tests that require long set-up/complex test data should considered candidates for future automation.

### Roles
Developers will write unit and integration tests for each pull request they work on. They will also put in place test fixtures and other test apparatus needed to run tests at all layers.
QA resource(s) will expand existing test suites as needed with a focus on end-to-end tests. QA will work to define when code is ready to be released into production. 

### QA Ticket Flow in ZenHub
**Step 1 - The QA team will work ahead of development, creating QA tasks for each story in the backlog.**

In sprint planning and backlog grooming, QA will work with the team to ensure that all acceptance criteria and testable details are entered at the story level. Sometimes, between planning and when a ticket is worked on, details regarding a story can change. In such cases, the story must be kept up to date so that it reflects the "as-built" spec. As much detail as possible should be included in the story, within reason. For example, please include the following:
- Which fields/labels will be present? (could be in a mock-up)
- Which actions can a user take?  
- Which business rules will run/not run?
- What are the expected validation messages/warnings/pop-ups?
- Which portion of the flow is in scope and which portions can be expected to be incomplete?

In some cases, the story will refer to supporting documentation that can't be summarised as part of the story description. In such cases, simply provide a link to your resource. Please ensure that it is a reference to a document in an un-ambiguous state. Un-ambiguous in this case means that it represents a final "as-built" description of what should be present with no outstanding TBD or question marks.

**Step 2 - Tasks that have completed code review can be moved into the "Ready for QA" pipeline**

Once a task has completed dev code review, it will have passed all local tests, been built in Dev with all pipeline tests completed. Tasks can then move into the Ready for QA pipeline. Here again, it is important that the task contain some basic information that will allow a QA resource to begin testing without having to bother the developer too much. For technical tasks, please include the following:
- Any URLs or endpoints that are related to testing the task 
- Basic steps to exercise  the feature in the task

In some cases, QA won't feel the need to test an item that arrives in this pipeline. It is still expected that all tasks will be placed in this pipeline for review. Developers are welcome to signal whether they feel testing is needed or not.

### Pre-release checklist
Prior to moving into production, the following steps should be completed or confirmed:
1. Create a pre-release checklist ticket in ZenHub using issue template
2. Update version number in the code being released
3. Create a draft release in GitHub and confirm the correct commits are present
4. Add version # and release # to pre-release checklist ticket
5. Dev to send commit list to QA (or otherwise publish changelog)
6. QA to schedule the release with staff/clients (daytime's best or when staff are available for rollback)
7. All dev/test pipeline test suites green
8. Dev/QA chat to plan prod verification testing (unless already automated)
9. Release the code to production and complete prod verification
10. Finalise/publish the release in GitHub, tagging it