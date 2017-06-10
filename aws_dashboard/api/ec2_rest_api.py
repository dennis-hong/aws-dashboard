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
        try:
            instance_id = ec2.create_instance(
                request,
                name=request.DATA['name'],
                image=request.DATA['source_id'],
                flavor=request.DATA['flavor_id'],
                key_name='dennis',
                security_groups=['sg-873597ef', ],
                instance_count=request.DATA['instance_count']
            )
        except KeyError as e:
            raise rest_utils.AjaxError(400, 'missing required parameter '
                                            "'%s'" % e.args[0])

        instance = ec2.get_instance(request, instance_id)
        return rest_utils.CreatedResponse(
            'aws/ec2/instances/%s' % utils_http.urlquote(instance_id),
            instance.to_dict()
        )

    @rest_utils.ajax()
    def delete(self, request, server_id):
        ec2.delete_instance(request, server_id)


@urls.register
class Images(generic.View):

    url_regex = r'aws/ec2/images/$'

    @rest_utils.ajax()
    def get(self, request):
        """Get EC2 image list"""
        images = ec2.get_images(request)
        return {
            'items': [i.to_dict() for i in images],
            'has_more_data': False,
            'has_prev_data': False,
        }


@urls.register
class Flavors(generic.View):
    """API for EC2 flavors."""
    url_regex = r'aws/ec2/flavors/$'

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of flavors."""
        flavors = ec2.list_flavor()
        return {'items': [f.to_dict() for f in flavors]}


@urls.register
class SecurityGroups(generic.View):
    """API over all server security groups.
    """
    url_regex = r'aws/ec2/security-groups/$'

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of security groups.

        The listing result is an object with property "items". Each item is
        security group associated with this server.
        """
        groups = ec2.list_security_groups(request)
        return {'items': [s.to_dict() for s in groups]}


@urls.register
class Keypairs(generic.View):
    """API for nova keypairs.
    """
    url_regex = r'aws/ec2/keypairs/$'

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of keypairs associated with the current logged-in
        account.

        The listing result is an object with property "items".
        """
        result = ec2.list_keypairs(request)
        return {'items': [u.to_dict() for u in result]}
