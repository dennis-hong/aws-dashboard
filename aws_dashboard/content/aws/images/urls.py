# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
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

from django.conf.urls import include
from django.conf.urls import url

from aws_dashboard.content.aws.images.images \
    import urls as image_urls
from aws_dashboard.content.aws.images.snapshots \
    import urls as snapshot_urls
from aws_dashboard.content.aws.images import views


urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'', include(image_urls, namespace='images')),
    url(r'', include(snapshot_urls, namespace='snapshots')),
]
