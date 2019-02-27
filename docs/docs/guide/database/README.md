# Overview

The longterm direction for LEAR is to use [PostgreSQL](https://www.postgresql.org/) as the primay database containing the _System of Record_ (SOR).

The current SOR is an Oracle 12c database housed in the legacy datacenter.

## PostgreSQL

Postgres is used to hold the _Work in Progress_ (WIP), as well as act as a local cache of the SOR data in updated model more closely matching the Business Domain and longterm data management approach.

In order to provide a HA (High Availability) postgres database, including enterprise class support, the Registry is using the [EnterpriseDB](https://www.enterprisedb.com/) distribution.

## PostgreSQL Backups

Backups of EnterpriseDB are stored on the CSI platform's NFS services which is part of the corporate backup and recovery environment.

## Oracle

The corporate registry SOR is in an Oracle 12c RDBMS. This runs in the legacy datacenter and is accessed directly from the CSI PaaS.

## Oracle Backups

DXC Advanced Solutions provides OPS DBA support and services to the Registry, so they fully manage backup / recovery / patching / configuration, etc. All activity is managed via a standard ticket request process.
