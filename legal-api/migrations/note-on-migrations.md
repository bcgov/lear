The migrations folder is only here so that the SRE script picks up that it should run the migration script for this project ('pre-hook-update-db.sh').

Migrations live in the business-registry-model located in lear/python/common. They are imported as a dependency and flask db upgrade/downgrade will still be run on the legal-api image via the existing SRE flow.