# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CORS pre-flight decorator.

A simple decorator to add the options method to a Request Class.
"""
# from functools import wraps
import time
import functools


def cors_preflight(methods: str = 'GET'):
    """Render an option method on the class."""
    def wrapper(func):
        def options(self, *args, **kwargs):  # pylint: disable=unused-argument
            return {'Allow': 'GET'}, 200, \
                   {'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': methods,
                    'Access-Control-Allow-Headers': 'Authorization, Content-Type'}

        setattr(func, 'options', options)
        return func
    return wrapper


def build_schema_error_response(errors):
    """Provide a formatted error response for schema errors."""
    formatted_errors = []
    for error in errors:
        validation_errors = []
        for context in error.context:
            validation_errors.append({
                'message': context.message,
                'jsonPath': context.json_path,
                'validator': context.validator,
                'validatorValue': context.validator_value
            })
        formatted_errors.append({'path': '/'.join(error.path), 'error': error.message, 'context': validation_errors})
    return formatted_errors


def print_execution_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = (end_time - start_time) 
        print(f"Function '{func.__name__}' took {elapsed_time:.6f} s to execute")
        return result
    return wrapper