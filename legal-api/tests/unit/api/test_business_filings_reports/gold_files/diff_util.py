#! /usr/bin/env python3
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
"""Hack to deeply compare 2 files."""
import json
import os
import sys

from deepdiff import DeepDiff


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

<<<<<<< HEAD
if len(sys.argv) == 2:
    print('usage: diff_util file1 file2')
    exit(0)
=======
if len(sys.argv) < 2:
    print('usage: diff_util file1 file2')
>>>>>>> 336972f82f32e8f09c0f53c05261a3dcafa2952f
else:
    file1 = sys.argv[1]
    file2 = sys.argv[2]

<<<<<<< HEAD
    try:

        with open(os.path.join(__location__, file1)) as json_file:
            json1 = json.load(json_file)

        with open(os.path.join(__location__, file2)) as json_file:
            json2 = json.load(json_file)

        print(DeepDiff(json1, json2))

    except FileNotFoundError as err:
        print(err)
        # exit(0)  # should return an error -1, but pytest chokes on this file
=======
    with open(os.path.join(__location__, file1)) as json_file:
        json1 = json.load(json_file)

    with open(os.path.join(__location__, file2)) as json_file:
        json2 = json.load(json_file)

    print(DeepDiff(json1, json2))
>>>>>>> 336972f82f32e8f09c0f53c05261a3dcafa2952f
