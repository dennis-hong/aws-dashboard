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
import json
from os import path

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
        self.tenant_id = "aws_ec2"


class Image(base.APIDictWrapper):
    _attrs = ['id', 'Name', 'State', 'Public',
              'VirtualizationType', 'Hypervisor', 'ImageOwnerAlias', 'EnaSupport',
              'SriovNetSupport', 'ImageId', 'BlockDeviceMappings', 'Architecture',
              'ImageLocation', 'RootDeviceType', 'OwnerId', 'RootDeviceName',
              'CreationDate', 'ImageType', 'Description']

    def __init__(self, apidict):
        apidict['id'] = apidict['ImageId']
        super(Image, self).__init__(apidict)


class InstanceType(base.APIDictWrapper):
    _attrs = ['id', 'InstanceType', 'vCPU', 'Memory', 'Storage', 'PhysicalProcessor',
              'ClockSpeed', 'EBS_OPT', 'EnhancedNetworking',
              'IntelAVX2', 'IntelAVX', 'IntelTurbo', 'NetworkingPerformance']

    def __init__(self, apidict):
        apidict['id'] = apidict['InstanceType']
        super(InstanceType, self).__init__(apidict)


class SecurityGroup(base.APIDictWrapper):
    _attrs = ['id', 'GroupName', 'Description', 'IpPermissions', 'IpRanges',
              'IpPermissionsEgress', 'Ipv6Ranges', 'EnhancedNetworking',
              'UserIdGroupPairs', 'VpcId', 'OwnerId', 'GroupId']

    def __init__(self, apidict):
        apidict['id'] = apidict['GroupId']
        apidict['security_group_rules'] = apidict['IpPermissions']
        super(SecurityGroup, self).__init__(apidict)


class KeyFair(base.APIDictWrapper):
    _attrs = ['name', 'key']

    def __init__(self, apidict):
        apidict['name'] = apidict['KeyName']
        apidict['fingerprint'] = apidict['KeyFingerprint']
        super(KeyFair, self).__init__(apidict)


def _to_instances(reservations):
    instances = []
    for reservation in reservations:
        for ec2_instance in reservation.get('Instances'):
            instances.append(Ec2Instance(ec2_instance))
    return instances


def _to_images(aws_images):
    images = []
    for aws_image in aws_images.get('Images'):
            images.append(Image(aws_image))
    return images


def _to_instance_types(aws_instance_types):
    instance_types = []
    for k in aws_instance_types.keys():
        instance_types.append(InstanceType(aws_instance_types.get(k)))
    return instance_types


def _to_security_groups(aws_sg_list):
    sg_list = []
    for aws_sg in aws_sg_list.get('SecurityGroups'):
        sg_list.append(SecurityGroup(aws_sg))
    return sg_list


def _to_keyfairs(aws_key_list):
    key_list = []
    for aws_key in aws_key_list.get('KeyPairs'):
        key_list.append(KeyFair(aws_key))
    return key_list


def _get_api_keys(project_id):
    keys_dict = getattr(settings, 'AWS_API_KEY_DICT', {})
    key_set = keys_dict.get(project_id)
    _validate_key_set(key_set)
    return key_set.get('AWS_ACCESS_KEY_ID'), key_set.get('AWS_SECRET_ACCESS_KEY'), key_set.get('AWS_REGION_NAME')


def _validate_key_set(key_set):
    if key_set is None:
        LOG.error("Not Found AWS API key set.")
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


@memoized
def ec2_client(request):
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = _get_api_keys(project_id)

    c = boto3.client(
        'ec2',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name)
    return c


@memoized
def ec2_resource(request):
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = _get_api_keys(project_id)

    r = boto3.resource(
        'ec2',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name)
    return r


def list_instance(request):
    reservations = ec2_client(request).describe_instances().get('Reservations')
    instances = _to_instances(reservations)
    return instances


def get_instance(request, instance_id):
    reservations = None
    try:
        # TODO: change to use ec2_resource(request)
        reservations = ec2_client(request).describe_instances(
            InstanceIds=[instance_id, ]
        ).get('Reservations')
    except ClientError as e:
        LOG.error("Received error: %s", e, exc_info=True)
    instances = _to_instances(reservations)
    if len(instances) > 0:
        return instances[0]
    else:
        return Ec2Instance()


def delete_instance(request, instance_id):
    response = ec2_client(request).terminate_instances(
        InstanceIds=[
            instance_id,
        ]
    )
    return response


def create_instance(request, name, image, flavor, key_name, security_groups, instance_count):
    instance = ec2_resource(request).create_instances(
        ImageId=image,
        MinCount=instance_count,
        MaxCount=instance_count,
        KeyName=key_name,
        SecurityGroupIds=security_groups,
        InstanceType=flavor,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ]
    )
    return instance[0].id


def get_images(request):
    response = None
    try:
        response = ec2_client(request).describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': [
                        'RHEL-7.2*',
                        'suse-sles-12-*',
                        'ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-*',
                        'amzn-ami-hvm-*',
                    ]
                },
                {
                    'Name': 'state',
                    'Values': [
                        'available',
                    ]
                },
            ]
        )
    except ClientError as e:
        LOG.error("Image List Received error: %s", e, exc_info=True)
    return _to_images(response)


def list_flavor():
    """Get the list of available instance type (flavors)."""
    with open(path.join(path.dirname(path.realpath(__file__)), 'instanceType.json'), 'r') as r:
        rd = json.load(r)
        instance_types = rd
        r.close()
    return _to_instance_types(instance_types)


def list_security_groups(request):
    """Get the list of available security groups."""
    aws_sg_list = ec2_client(request).describe_security_groups()
    return _to_security_groups(aws_sg_list)


def list_keypairs(request):
    """Get the list of ssh key."""
    response = ec2_client(request).describe_key_pairs()
    return _to_keyfairs(response)
