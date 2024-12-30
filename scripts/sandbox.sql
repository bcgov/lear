-- These sequences will not be available in PROD until COLIN shutdown
CREATE SEQUENCE business_identifier_c START 2000000;
CREATE SEQUENCE business_identifier_bc START 2000000;

-- Update existing(SP/GP and Coops) business identifier sequences so they don't collide with prod.
-- Specifically, collisions are an issue with auth db "entities" table's business_identifier column as auth db is
-- using prod db for sandbox
ALTER SEQUENCE business_identifier_sp_gp RESTART WITH 3000000;
ALTER SEQUENCE business_identifier_coop RESTART WITH 3000000;
