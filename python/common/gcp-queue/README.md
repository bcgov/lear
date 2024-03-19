[![License](https://img.shields.io/badge/License-BSD%203%20Clause-blue.svg)](LICENSE)


# Application Name
GCP Queue Flask Module


## Technology Stack Used
* Python, Flask
* GCP pubsub & auth

## Adding to your project
This can be added to your _pyproject.toml_ 
```yaml
[tool.poetry.dependencies]
...
gcp-queue = { git = "https://github.com/bcgov/lear.git", subdirectory = "python/common/gcp-queue", branch = "feature-legal-name" }
```

## Getting Started Contributing

# setup
Fork the repo and submitted a PR with accompanning tests.

Set to use the local repo for the virtual environment
```bash
poetry config virtualenvs.in-project true
```
Install the dependencies
```bash
poetry install
```

Configure the .env

## How to Contribute

If you would like to contribute, please see our [CONTRIBUTING](./CONTRIBUTING.md) guidelines.

Please note that this project is released with a [Contributor Code of Conduct](./CODE_OF_CONDUCT.md).
By participating in this project you agree to abide by its terms.

## License
Copyright © 2023 Province of British Columbia

Licensed under the BSD 3 Clause License, (the "License");
you may not use this file except in compliance with the License.
The template for the license can be found here
   https://opensource.org/license/bsd-3-clause/

Redistribution and use in source and binary forms,
with or without modification, are permitted provided that the
following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
