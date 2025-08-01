#!/usr/bin/env bash

# Copyright © 2025 Province of British Columbia
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


COPYRIGHT="Copyright © 2025 Province of British Columbia"
RET=0

for file in $(find $@ -not \( -path */venv -prune \) -not \( -path */migrations -prune \) -not \( -path */tests -prune \) -not \( -path */.egg* -prune \) -name \*.py)
do
  grep "${COPYRIGHT}" ${file} >/dev/null
  if [[ $? != 0 ]]
  then
    echo "${file} missing copyright header"
    RET=1
  fi
done
exit ${RET}
