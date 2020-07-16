## Parties Table Data Fix

### Getting the Parties that might need to be fixed / added
SQL for setup
- Get the counts for the parties connected to party roles `select count(*) as b, party_id from party_roles group by (party_id);`
- Select the counts that are only above 1 (these are the only possible parties that might need a change) `select party_id from (select count(*) as b, party_id from party_roles group by (party_id)) as a where b > 1 order by b desc;`
- Select the party_id, party_role_id, business_id from the above list (this will give all the necessary info we need to change things if necessary)
`select id, party_id, business_id from party_roles where party_id in (select party_id from (select count(*) as b, party_id from party_roles group by (party_id)) as a where b > 1 order by b desc) order by party_id;`

### Verify / add new parties
Verify the party info for each party that spans more than 1 business_id. You can accomplish this by comparing `select * from parties where id=<party_id you are verifying>` with the get current directors call in postman for the colin-api.
- ensure there is a different entry in the party table (for the party being verified) for the party roles of each business (the party can be the same for the party_roles within each business). To add a new entry into the parties table: 
    - `insert into addresses (address_type, street, city, region, country, postal_code) values (<values for each one>)` 
    - `insert into parties (party_type, first_name, middle_initial, last_name, delivery_address_id) values (<values for each, address_id should be from above>)`
    - `update party_roles set party_id=<id from above insert> where id=<party_role_id you are updating>`
