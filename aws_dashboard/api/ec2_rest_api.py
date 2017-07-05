# Copyright 2017 Dennis Hong.
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
from django.utils import http as utils_http
from django.views import generic
from openstack_dashboard.api.rest import urls
from openstack_dashboard.api.rest import utils as rest_utils

from aws_dashboard.api import ec2
from aws_dashboard.api.hybrid import taskflow

LOGICAL_NAME_PATTERN = "[a-zA-Z0-9-._~]+"


@urls.register
class Instances(generic.View):
    """API for EC2 Instances."""
    url_regex = r"aws/ec2/instances/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get a specific EC2 instance
        :param request: HTTP request

        """
        instances = ec2.list_instance(request)
        return {"items": [i.to_dict() for i in instances]}

    @rest_utils.ajax(data_required=True)
    def post(self, request):
        """Create an EC2 instance
        :param request: HTTP request
        """
        try:
            instance_id = ec2.create_instance(
                request,
                name=request.DATA["name"],
                image_id=request.DATA["source_id"],
                flavor=request.DATA["flavor_id"],
                key_name=request.DATA["key_name"],
                security_groups=request.DATA.get("security_groups"),
                availability_zone=request.DATA.get("availability_zone", None),
                instance_count=request.DATA["instance_count"]
            )
        except KeyError as e:
            raise rest_utils.AjaxError(400, "missing required parameter "
                                            "'%s'" % e.args[0])

        instance = ec2.get_instance(request, instance_id)
        return rest_utils.CreatedResponse(
            "aws/ec2/instances/%s" % utils_http.urlquote(instance_id),
            instance.to_dict()
        )

    @rest_utils.ajax()
    def delete(self, request, server_id):
        ec2.delete_instance(request, server_id)


@urls.register
class Instance(generic.View):
    """API for EC2 Instance."""
    url_regex = r"aws/ec2/instance/$"

    @rest_utils.ajax()
    def get(self, request, instance_id):
        """Get a specific EC2 instance
        :param request: HTTP request
        :param instance_id: EC2 Instance ID

        """
        return ec2.get_instance(request, instance_id).to_dict()


@urls.register
class ImportInstances(generic.View):
    """API for Import EC2 Instances."""
    url_regex = r"aws/ec2/import-instances/$"

    @rest_utils.ajax(data_required=True)
    def post(self, request):
        """Import an EC2 instance from OpenStack
        :param request: HTTP request
        """
        try:
            taskflow.run_import_instance_tasks(
                request,
                source_type=request.DATA.get("source_type", {}).get("type"),
                source_id=request.DATA.get("source_id"),
                flavor=request.DATA.get("flavor_id"),
                key_name=request.DATA.get("key_name"),
                security_groups=request.DATA.get("security_groups"),
                availability_zone=request.DATA.get("availability_zone"),
                instance_count=request.DATA.get("instance_count"),
                leave_original_instance=request.DATA.get("leave_original_instance"),
                leave_instance_snapshot=request.DATA.get("leave_instance_snapshot")
            )
        except KeyError as e:
            raise rest_utils.AjaxError(400, "missing required parameter "
                                            "'%s'" % e.args[0])
        return rest_utils.CreatedResponse("aws/ec2/instances", {})


@urls.register
class ExportInstances(generic.View):
    """API for Export EC2 Instances."""
    url_regex = r"aws/ec2/export-instances/$"

    _optional_create = [
        'block_device_mapping', 'block_device_mapping_v2', 'nics', 'meta',
        'availability_zone', 'instance_count', 'admin_pass', 'disk_config',
        'config_drive', 'scheduler_hints'
    ]

    @rest_utils.ajax(data_required=True)
    def post(self, request):
        """Export an EC2 instance to OpenStack
        :param request: HTTP request
        """
        try:
            args = (
                request,
                request.DATA['name'],
                request.DATA['source_id'],
                request.DATA['flavor_id'],
                request.DATA['key_name'],
                request.DATA['user_data'],
                request.DATA['security_groups'],
                request.DATA.get('leave_original_instance'),
                request.DATA.get('leave_instance_snapshot')
            )
        except KeyError as e:
            raise rest_utils.AjaxError(400, 'missing required parameter '
                                            "'%s'" % e.args[0])
        kw = {}
        for name in self._optional_create:
            if name in request.DATA:
                kw[name] = request.DATA[name]

        new = taskflow.run_export_instance_tasks(*args, **kw)
        return rest_utils.CreatedResponse(
            '/api/nova/servers/%s' % utils_http.urlquote(new.id),
            new.to_dict()
        )


@urls.register
class Images(generic.View):
    """API for EC2 Images."""
    url_regex = r"aws/ec2/images/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get EC2 image list"""
        images = ec2.get_images(request)
        return {
            "items": [i.to_dict() for i in images],
            "has_more_data": False,
            "has_prev_data": False,
        }


@urls.register
class Flavors(generic.View):
    """API for EC2 flavors."""
    url_regex = r"aws/ec2/flavors/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of flavors."""
        flavors = ec2.list_flavor(request)
        return {"items": [f.to_dict() for f in flavors]}


@urls.register
class SecurityGroups(generic.View):
    """API over all server security groups.
    """
    url_regex = r"aws/ec2/security-groups/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of security groups.

        The listing result is an object with property "items". Each item is
        security group associated with this server.
        """
        groups = ec2.list_security_groups(request)
        return {"items": [s.to_dict() for s in groups]}


@urls.register
class Keypairs(generic.View):
    """API for EC2 keypairs.
    """
    url_regex = r"aws/ec2/keypairs/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of keypairs associated with the current logged-in
        account.

        The listing result is an object with property "items".
        """
        result = ec2.list_keypairs(request)
        return dict(items=[u.to_dict() for u in result])

    @rest_utils.ajax(data_required=True)
    def post(self, request):
        """Create a keypair.

        Create a keypair using the parameters supplied in the POST
        application/json object. The parameters are:

        :param name: the name to give the keypair
        :param public_key: (optional) a key to import

        This returns the new keypair object on success.
        """
        if "public_key" in request.DATA:
            new = ec2.import_keypair(request, request.DATA["name"],
                                     request.DATA["public_key"])
        else:
            new = ec2.create_keypair(request, request.DATA["name"])
        return rest_utils.CreatedResponse(
            "/api/aws/ec2/keypairs/%s" % utils_http.urlquote(new.name),
            new.to_dict()
        )



@urls.register
class Regions(generic.View):
    """API for EC2 Region.
    """
    url_regex = r"aws/ec2/regions/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of region.

        The listing result is an object with property "items".
        """
        result = ec2.list_regions(request)
        return {"items": [u.to_dict() for u in result]}


@urls.register
class AvailabilityZones(generic.View):
    """API for EC2 AvailabilityZones.
    """
    url_regex = r"aws/ec2/availability-zones/$"

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of AvailabilityZones.

        The listing result is an object with property "items".
        """
        result = ec2.list_availability_zones(request)
        return {"items": [u.to_dict() for u in result]}
