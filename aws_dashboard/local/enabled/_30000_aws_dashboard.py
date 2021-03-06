# Copyright 2017, dennis.hong.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The slug of the dashboard to be added to HORIZON['dashboards']. Required.
DASHBOARD = 'aws'

# A list of applications to be added to INSTALLED_APPS.
ADD_INSTALLED_APPS = ['aws_dashboard', ]

ADD_ANGULAR_MODULES = [
    'horizon.dashboard.aws',
]

AUTO_DISCOVER_STATIC_FILES = True
# A list of js files to be included in the compressed set of files
ADD_JS_FILES = []
# A list of scss files to be included in the compressed set of files
ADD_SCSS_FILES = ['dashboard/aws/aws.scss']