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
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from horizon.utils.memoized import memoized  # noqa
from openstack_dashboard.api import base

LOG = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    LOG.error("import boto3 failed. please pip install boto3")
    pass


class Ec2Instance(base.APIDictWrapper):
    _attrs = ['id', 'name', 'status',
              'InstanceId', 'PublicDnsName', 'PrivateDnsName', 'State',
              'Monitoring', 'EbsOptimized', 'PublicIpAddress', 'PrivateIpAddress',
              'ProductCodes', 'VpcId', 'KeyName', 'SecurityGroups', 'ClientToken',
              'SubnetId', 'InstanceType', 'NetworkInterfaces', 'Placement',
              'Hypervisor', 'BlockDeviceMappings', 'RootDeviceName'
              'StateTransitionReason', 'ImageId', 'Tags']

    def __init__(self, apidict):
        super(Ec2Instance, self).__init__(apidict)
        self.id = self.InstanceId
        for tag in self.Tags:
            if tag["Key"] == "Name":
                self.name = tag["Value"]
        if self.name is None:
            self.name = "No Name"
        self.status = self.InstanceId
        self.tenant_id = "tenant_id"


@memoized
def ec2_client(request):
    project_id = request.user.tenant_id

    keys_dict = getattr(settings, 'AWS_API_KEY_DICT', {})
    key_set = keys_dict.get(project_id)
    if key_set is None:
        LOG.error("Not Found project_id : %s in AWS_API_KEY_DICT." % project_id)
        raise ImproperlyConfigured("AWS API Key Not Found. Please Check in "
                                   "local_settings.d/_30000_aws_dashboard.py")

    aws_access_key_id = key_set.get('AWS_ACCESS_KEY_ID', '')
    aws_secret_access_key = key_set.get('AWS_SECRET_ACCESS_KEY', '')
    region_name = key_set.get('AWS_REGION_NAME', '')
    if aws_access_key_id == "" or aws_secret_access_key == "" or region_name == "":
        LOG.error("aws_access_key_id : %(aws_access_key_id)s "
                  "aws_secret_access_key : %(aws_secret_access_key)s "
                  "region_name: %(region_name)s" %
                  dict(aws_access_key_id=aws_access_key_id,
                       aws_secret_access_key=aws_secret_access_key,
                       region_name=region_name))
        raise ImproperlyConfigured("AWS API Key Not Found. Please Check in "
                                   "local_settings.d/_30000_aws_dashboard.py")

    c = boto3.client(
        'ec2',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name)
    return c


def list_instance(request):
    reservations = ec2_client(request).describe_instances().get('Reservations')
    instances = to_instances(reservations)
    return instances


def get_instance(request, instance_id):
    reservations = None
    try:
        reservations = ec2_client(request).describe_instances(
            InstanceIds=[instance_id, ]
        ).get('Reservations')
    except ClientError as e:
        LOG.error("Received error: %s", e, exc_info=True)
    instances = to_instances(reservations)
    if len(instances) > 0:
        return instances[0]
    else:
        return Ec2Instance()


def to_instances(reservations):
    instances = []
    for reservation in reservations:
        for ec2_instance in reservation.get('Instances'):
            instances.append(Ec2Instance(ec2_instance))
    return instances
