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
import datetime
import json
import logging
from os import path

import boto3
from botocore.exceptions import ClientError

from horizon.utils.memoized import memoized  # noqa
from openstack_dashboard.api import base

from aws_dashboard.api.hybrid.utils import get_api_keys
from aws_dashboard.api.hybrid.utils import to_wrapping_list

LOG = logging.getLogger(__name__)

logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)


class Ec2Instance(base.APIDictWrapper):
    _attrs = ["id", "name", "instance_type", "image_id", "status", "tenant_id",
              "InstanceId", "PublicDnsName", "PrivateDnsName", "State",
              "Monitoring", "EbsOptimized", "PublicIpAddress", "PrivateIpAddress",
              "ProductCodes", "VpcId", "KeyName", "SecurityGroups", "ClientToken",
              "SubnetId", "InstanceType", "NetworkInterfaces", "Placement",
              "Hypervisor", "BlockDeviceMappings", "RootDeviceName"
              "StateTransitionReason", "ImageId", "Tags"]

    def __init__(self, apidict):
        apidict["id"] = apidict["InstanceId"]
        apidict["instance_type"] = apidict["InstanceType"]
        apidict["image_id"] = apidict["ImageId"]
        apidict["status"] = apidict["State"]["Name"]
        for tag in apidict.get("Tags"):
            if tag.get("Key") == "Name":
                apidict["name"] = tag.get("Value")
        if apidict.get("name") == "" or apidict.get("name") is None:
            apidict["name"] = apidict["InstanceId"]
        apidict["tenant_id"] = "aws_ec2"
        super(Ec2Instance, self).__init__(apidict)


class Image(base.APIDictWrapper):
    _attrs = ["id", "Name", "State", "Public",
              "VirtualizationType", "Hypervisor", "ImageOwnerAlias", "EnaSupport",
              "SriovNetSupport", "ImageId", "BlockDeviceMappings", "Architecture",
              "ImageLocation", "RootDeviceType", "OwnerId", "RootDeviceName",
              "CreationDate", "ImageType", "Description"]

    def __init__(self, apidict):
        apidict["id"] = apidict["ImageId"]
        super(Image, self).__init__(apidict)


class InstanceType(base.APIDictWrapper):
    _attrs = ["id", "InstanceType", "vCPU", "Memory", "Storage", "PhysicalProcessor",
              "ClockSpeed", "EBS_OPT", "EnhancedNetworking",
              "IntelAVX2", "IntelAVX", "IntelTurbo", "NetworkingPerformance"]

    def __init__(self, apidict):
        apidict["id"] = apidict["InstanceType"]
        super(InstanceType, self).__init__(apidict)


class SecurityGroup(base.APIDictWrapper):
    _attrs = ["id", "GroupName", "Description", "IpPermissions", "IpRanges",
              "IpPermissionsEgress", "Ipv6Ranges", "EnhancedNetworking",
              "UserIdGroupPairs", "VpcId", "OwnerId", "GroupId"]

    def __init__(self, apidict):
        apidict["id"] = apidict["GroupId"]
        apidict["security_group_rules"] = apidict["IpPermissions"]
        super(SecurityGroup, self).__init__(apidict)


class KeyPair(base.APIDictWrapper):
    _attrs = ["name", "fingerprint"]

    def __init__(self, apidict):
        apidict["name"] = apidict["KeyName"]
        apidict["fingerprint"] = apidict["KeyFingerprint"]
        apidict["key_material"] = apidict.get("KeyMaterial", "")
        super(KeyPair, self).__init__(apidict)


class Region(base.APIDictWrapper):
    _attrs = ["RegionName", "Endpoint"]

    def __init__(self, apidict):
        apidict["name"] = apidict["RegionName"]
        apidict["endpoint"] = apidict["Endpoint"]
        super(Region, self).__init__(apidict)


class AvailabilityZone(base.APIDictWrapper):
    _attrs = ["RegionName", "ZoneName", "State", "Messages"]

    def __init__(self, apidict):
        apidict["region_name"] = apidict["RegionName"]
        apidict["zone_name"] = apidict["ZoneName"]
        apidict["state"] = apidict["State"]
        apidict["messages"] = apidict["Messages"]
        super(AvailabilityZone, self).__init__(apidict)


def _to_instances(reservations):
    instances = []
    for reservation in reservations:
        for ec2_instance in reservation.get("Instances"):
            instances.append(Ec2Instance(ec2_instance))
    return instances


def _to_instance_types(aws_instance_types):
    instance_types = []
    for k in aws_instance_types.keys():
        instance_types.append(InstanceType(aws_instance_types.get(k)))
    return instance_types


@memoized
def ec2_client(request):
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = get_api_keys(project_id)
    session = boto3.session.Session(aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key,
                                    region_name=region_name)
    return session.client("ec2")


@memoized
def ec2_resource(request):
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = get_api_keys(project_id)
    session = boto3.session.Session(aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key,
                                    region_name=region_name)
    return session.resource("ec2")


def list_instance(request):
    reservations = ec2_client(request).describe_instances().get("Reservations")
    return _to_instances(reservations)


def get_instance(request, instance_id):
    # TODO: change to use ec2_resource(request)
    reservations = ec2_client(request).describe_instances(
        InstanceIds=[instance_id]
    ).get("Reservations")
    instances = _to_instances(reservations)
    return instances[0]


def delete_instance(request, instance_id):
    LOG.debug('Delete EC2 Instance : %s' % instance_id)
    return ec2_client(request).terminate_instances(InstanceIds=[instance_id])


def create_instance(request, name, image_id, flavor, key_name,
                    security_groups, availability_zone, instance_count=1):
    instance = ec2_resource(request).create_instances(
        ImageId=image_id,
        MinCount=instance_count,
        MaxCount=instance_count,
        KeyName=key_name,
        SecurityGroupIds=security_groups,
        InstanceType=flavor,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": name
                    },
                ]
            },
        ],
        Placement={
            "AvailabilityZone": availability_zone,
        }
    )
    return instance[0].id


def get_images(request):
    response = None
    try:
        response = ec2_client(request).describe_images(
            Filters=[
                {
                    "Name": "name",
                    "Values": [
                        "RHEL-7.2*",
                        "suse-sles-12-*",
                        "ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-*",
                        "amzn-ami-hvm-*",
                        "import*",
                        "export*",
                    ]
                },
                {
                    "Name": "state",
                    "Values": [
                        "available",
                    ]
                },
            ]
        )
    except ClientError as e:
        LOG.error("Image List Received error: %s", e, exc_info=True)
    return to_wrapping_list(response, "Images", Image)


def list_flavor(request):
    """Get the list of available instance type (flavors)."""
    # TODO(Dennis) : Instance type API is too heavy to call directly.(per region 7MB..) Needs Improvement. T.T
    # DOC : https://aws.amazon.com/blogs/aws/new-aws-price-list-api/
    # API : https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20170605233259/ap-northeast-2/index.json
    with open(path.join(path.dirname(path.realpath(__file__)), "instanceType.json"), "r") as r:
        rd = json.load(r)
        instance_types = rd
        r.close()
    return _to_instance_types(instance_types)


def list_security_groups(request):
    """Get the list of available security groups."""
    response = ec2_client(request).describe_security_groups()
    return to_wrapping_list(response, "SecurityGroups", SecurityGroup)


def list_keypairs(request):
    """Get the list of ssh key."""
    response = ec2_client(request).describe_key_pairs()
    return to_wrapping_list(response, "KeyPairs", KeyPair)


def create_keypair(request, key_name):
    """create ssh key."""
    response = ec2_client(request).create_key_pair(KeyName=key_name)
    return KeyPair(response)


def import_keypair(request, key_name, public_key):
    """create ssh key."""
    response = ec2_client(request).import_key_pair(
        KeyName=key_name,
        PublicKeyMaterial=public_key
    )
    return KeyPair(response)


def start_instance(request, instance_id):
    ec2_client(request).start_instances(InstanceIds=[instance_id, ])


def stop_instance(request, instance_id):
    ec2_client(request).stop_instances(InstanceIds=[instance_id, ])


def reboot_instance(request, instance_id):
    ec2_client(request).reboot_instances(InstanceIds=[instance_id, ])


def list_regions(request):
    """Get the list of region."""
    response = ec2_client(request).describe_regions()
    return to_wrapping_list(response, "Regions", Region)


def list_availability_zones(request):
    """Get the list of availability zone."""
    response = ec2_client(request).describe_availability_zones()
    return to_wrapping_list(response, "AvailabilityZones", AvailabilityZone)


def import_image_from_s3(request, image_format, bucket_name, object_name, upload_size):
    """Import Instance Image"""
    now = datetime.datetime.now()
    response = ec2_client(request).import_image(
        Description=object_name,
        DiskContainers=[
            {
                "Description": object_name,
                "Format": image_format,
                "UserBucket": {
                    "S3Bucket": bucket_name,
                    "S3Key": object_name
                },
                "DeviceName": "/dev/sda"
            },
        ],
        LicenseType="BYOL",
        Hypervisor="xen",
        Architecture="x86_64",
        Platform="Linux",
        ClientData={
            "UploadStart": now,
            "UploadEnd": now + datetime.timedelta(days=1),
            "UploadSize": upload_size,
            "Comment": "from_openstack"
        }
    )
    LOG.debug("Import Image_Task : {}".format(response))
    return response.get("ImportTaskId")


def export_instance_to_s3(request, instance_id, bucket_name, instance_name=""):
    """Export Instance To OpenStack"""
    task = ec2_client(request).create_instance_export_task(
        Description=instance_name,
        ExportToS3Task={
            "DiskImageFormat": "vmdk",
            "S3Bucket": bucket_name
        },
        InstanceId=instance_id,
        TargetEnvironment="vmware"
    )
    return task.get("ExportTask").get("ExportTaskId")
