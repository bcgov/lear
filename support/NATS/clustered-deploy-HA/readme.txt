Files:

nats-deploy.yml
nats-service.yml
postgres-deploy.yml
postgres-service.yml
scripts.sql

Installation:

1) Allocate stroage for postgres

2) Allocate space for a very small volume mount ( 100 mb or less)

3) Run postgres-deploy.yml

4) Run postges-service.yml 

5) Create the database in postgres (nats-db or like that)

6) Run the scripts.sql in the postgres database. This creates the tables used by NATS

7) Edit the nats-deploy.yml script:
	a) change namspace to your namespace
	b) change image to your nats image
	c) note: the "cluster_log_path" value point to the small volume mount (called /mnt/natsdata)
	d) note: the "sql_source" value should point to your postgres database
	
8) Run nats-deploy.yml

9) Run nats-service.yml

   Check logs to determine if nats is connected to database


	