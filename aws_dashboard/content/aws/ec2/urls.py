# Copyright (c) 2017 dennis hong.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.conf.urls import url

import aws_dashboard.api.ec2_rest_api  # noqa
from aws_dashboard.content.aws.ec2 import views


INSTANCES = r'^(?P<instance_id>[^/]+)/%s$'
INSTANCES_KEYPAIR = r'^(?P<instance_id>[^/]+)/(?P<keypair_name>[^/]+)/%s$'

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^launch$', views.LaunchInstanceView.as_view(), name='launch'),
]
