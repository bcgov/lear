
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/bcgov/lear/branch/master/graph/badge.svg?flag=business-digital-credentials)](https://codecov.io/gh/bcgov/lear/tree/master/queue_services/business-digital-credentials)

# Application Name

BC Registries - Digital Business Card credentials queue service

## Technology Stack Used
* poetry
* Python, Flask
* Postgres -  SQLAlchemy, psycopg2-binary & alembic

## Project Status
As of 2025-08-14 in Production on Google Cloud Platform

## Documentation

### Local Dev Setup
Refer to the Makefile for specifics

**Build and run locally**
```
make build
make run
```

To run locally with hot reload can use `make run-dev`.

If you need to make changes to dependent modules (such as the ones in python/common like *business-registry-digital-credentials* or *business-registry-model*) those can be developed locally and loaded in with `run-dev` with hot reload. See commented out docker command setup in makefile for examples.

**Test**

```
poetry install
make lint 
make test
```

## Security

## Getting Help or Reporting an Issue

To report bugs/issues/feature requests, please file an [issue](../../issues).

## How to Contribute

If you would like to contribute, please see our [CONTRIBUTING](./CONTRIBUTING.md) guidelines.

Please note that this project is released with a [Contributor Code of Conduct](./CODE_OF_CONDUCT.md).
By participating in this project you agree to abide by its terms.

## License

    Copyright 2020 Province of British Columbia

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

