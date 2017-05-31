# Copyright 2017 dennis.hong.
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
from django.views import generic
from django.utils import http as utils_http

from aws_dashboard.api import ec2

from openstack_dashboard.api.rest import urls

from openstack_dashboard.api.rest import utils as rest_utils


LOGICAL_NAME_PATTERN = '[a-zA-Z0-9-._~]+'


@urls.register
class Instances(generic.View):

    url_regex = r'aws/ec2/instances/$'

    @rest_utils.ajax()
    def get(self, request, instance_id):
        """Get a specific EC2 instance
        :param request: HTTP request
        :param instance_id: EC2 Instance ID

        """
        return ec2.get_instance(request, instance_id).to_dict()

    @rest_utils.ajax(data_required=True)
    def post(self, request):
        """Create an EC2 instance
        :param request: HTTP request
        """
        instance_id = ec2.create_instance(
            request,
            name=request.DATA['name'],
            image='ami-66e33108',
            flavor='t2.micro',
            key_name='dennis',
            security_groups=['sg-873597ef', ],
            instance_count=1
        )
        instance = ec2.get_instance(request, instance_id)
        return rest_utils.CreatedResponse(
            'aws/ec2/instances/%s' % utils_http.urlquote(instance_id),
            instance.to_dict()
        )

    @rest_utils.ajax()
    def delete(self, request, server_id):
        ec2.delete_instance(request, server_id)

