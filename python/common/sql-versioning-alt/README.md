
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)


# Application Name

SQLAlchemy Versioning library (LEAR Version)

## Technology Stack Used

- Python, Flask
- SQLAlchemy

## Third-Party Products/Libraries used and the License they are covered by

This project uses the following third-party libraries:

- Flask - BSD License
- SQLAlchemy - MIT License

Each library is subject to its own license, and the respective licenses can be found in their repositories.


## Project Status

As of 2024-10-10 in Development

## Documentation

GitHub Pages (https://guides.github.com/features/pages/) are a neat way to document you application/project.

## Security

TBD

## Files in this repository

```
sql-versioning/
├── sql_versioning    - versioning files
└── tests             - testing files
```

## Deployment (Local Development)

To set up the development environment on your local machine, follow these steps:

1. Developer Workstation Requirements/Setup:
    - Install Python 3.8+
    - Install Poetry
    - Install Docker
  
2. Setup
    - Fork and clone the repository

    - Set to use the local repo for the virtual environment:
        ```bash
        poetry config virtualenvs.in-project true
        ```
    - Install dependencies:
      ```bash
      poetry install
      ```

3. Running Tests
    - To run tests, use:
      ```bash
      poetry run pytest
      ```
    - In rare cases, if the test container doesn't start automatically, you can manually set up the testing database by running:
      ```bash
      docker-compose -f tests/docker-compose.yml up -d
      ```

## Deployment (OpenShift)

TBD

## Getting Help or Reporting an Issue

To report bugs/issues/feature requests, please file an [issue](../../issues).

## How to Contribute

If you would like to contribute, please see our [CONTRIBUTING](./CONTRIBUTING.md) guidelines.

Please note that this project is released with a [Contributor Code of Conduct](./CODE_OF_CONDUCT.md).
By participating in this project you agree to abide by its terms.

## License

    Copyright 2024 Province of British Columbia

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
