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
from openstack_dashboard.api import nova
from openstack_dashboard.api import network

from aws_dashboard.api.hybrid.utils import get_api_keys
from aws_dashboard.api.hybrid.utils import to_wrapping_list

LOG = logging.getLogger(__name__)

logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)
#logging.getLogger("keystoneauth").setLevel(logging.CRITICAL)
#logging.getLogger("oslo_policy").setLevel(logging.CRITICAL)


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
    _attrs = ["id", "name", "state", "isPublic", "Name", "State", "Public",
              "VirtualizationType", "Hypervisor", "ImageOwnerAlias", "EnaSupport",
              "SriovNetSupport", "ImageId", "BlockDeviceMappings", "Architecture",
              "ImageLocation", "RootDeviceType", "OwnerId", "RootDeviceName",
              "CreationDate", "ImageType", "Description"]

    def __init__(self, apidict):
        apidict["id"] = apidict["ImageId"]
        apidict["name"] = apidict["Name"]
        apidict["description"] = apidict.get("Description")
        apidict["owner"] = apidict.get("OwnerId")
        apidict["type"] = apidict["ImageType"]
        apidict["status"] = apidict["State"]
        apidict["location"] = apidict["ImageLocation"]
        apidict["state_reason"] = apidict.get("StateReason", {}).get("Message")
        apidict["is_public"] = apidict["Public"]
        apidict["create_at"] = apidict["CreationDate"]
        apidict["platform"] = apidict.get("Platform")
        apidict["architecture"] = apidict.get("Architecture")
        super(Image, self).__init__(apidict)


class InstanceType(base.APIDictWrapper):
    _attrs = ["id", "InstanceType", "vCPU", "Memory", "Storage", "PhysicalProcessor",
              "ClockSpeed", "EBS_OPT", "EnhancedNetworking",
              "IntelAVX2", "IntelAVX", "IntelTurbo", "NetworkingPerformance"]

    def __init__(self, apidict):
        apidict["id"] = apidict["InstanceType"]
        apidict["name"] = apidict["InstanceType"]
        apidict["vcpus"] = apidict["vCPU"]
        apidict["ram"] = apidict["Memory"]
        apidict["storage"] = apidict["Storage"]
        apidict["clock_speed"] = apidict["ClockSpeed"]
        apidict["network_performance"] = apidict["NetworkingPerformance"]
        super(InstanceType, self).__init__(apidict)


class SecurityGroup(base.APIDictWrapper):
    _attrs = ["id", "name", "description", "ip_ranges",
              "security_group_rules", "ip_permissions_egress",
              "GroupName", "Description", "IpPermissions", "IpRanges",
              "IpPermissionsEgress", "Ipv6Ranges", "EnhancedNetworking",
              "UserIdGroupPairs", "VpcId", "OwnerId", "GroupId", "Tags"]

    def __init__(self, apidict):
        apidict["id"] = apidict["GroupId"]
        apidict["name"] = apidict["GroupName"]
        apidict["description"] = apidict["Description"]
        apidict["ip_ranges"] = apidict.get("IpRanges")
        apidict["security_group_rules"] = apidict["IpPermissions"]
        apidict["ip_permissions_egress"] = apidict["IpPermissionsEgress"]
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
    reservations = ec2_client(request).describe_instances(
        InstanceIds=[instance_id]
    ).get("Reservations")
    return _to_instances(reservations)[0]


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


def list_image(request, params=[]):
    # TODO Need a more detailed implementation of list lookup
    if len(params):
        filters = params
    else:
        filters = [
            {
                "Name": "name",
                "Values": [
                    "RHEL-7*",
                    "suse-sles-12-*",
                    "ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-*",
                    "amzn-ami-hvm-*",
                    "Windows_Server-2016*",
                    "import*",
                    "export*",
                ]
            },
        ]
    response = ec2_client(request).describe_images(Filters=filters)
    return to_wrapping_list(response, "Images", Image)


def get_image(request, image_id):
    try:
        response = ec2_client(request).describe_images(ImageIds=[image_id])
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidImage.NotFound':
            return None
        else:
            return None
    return to_wrapping_list(response, "Images", Image)[0]


def delete_image(request, image_id):
    ec2_client(request).deregister_image(ImageId=image_id)


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


def import_openstack_sg(request, openstack_sg_id):
    """Import security group from OpenStack."""
    openstack_sg = network.security_group_get(request, openstack_sg_id)
    if openstack_sg.description == "":
        openstack_sg.description = "No Description"

    # If a security group with the same name exists, delete it and create a new one.
    old_sg = get_security_group(request, openstack_sg.name)
    if old_sg:
        delete_security_group(request, old_sg.get("id"))

    ec2_sg = ec2_resource(request).create_security_group(
        GroupName=openstack_sg.name,
        Description=openstack_sg.description)

    for rule in openstack_sg.rules:
        try:
            LOG.debug("start rule : {}".format(rule))
            kwargs = {
                "IpProtocol": rule.get("ip_protocol") if rule.get("ip_protocol") else "tcp",
                "FromPort": rule.get("from_port") if rule.get("from_port") else -1,
                "ToPort": rule.get("to_port") if rule.get("to_port") else -1
            }
            if rule.get("ethertype") == "IPv4":
                kwargs["CidrIp"] = str(rule.get("ip_range", {}).get("cidr", "0.0.0.0/0"))

                if rule.get("direction") == "ingress":
                    LOG.debug("Add ingress rule : {}".format(kwargs))
                    ec2_sg.authorize_ingress(**kwargs)
                elif rule.get("direction") == "egress":
                    LOG.debug("Add egress rule : {}".format(kwargs))
                    ec2_sg.authorize_egress(**kwargs)

            elif rule.get("ethertype") == "IPv6":
                # EC2 IPv6 format support
                LOG.debug("IPv6 format not support : {}".format(rule))

        except BaseException as e:
            LOG.error("Import Fail. Cause : {} Rule format something wrong : {}"
                      .format(e, rule))


def list_security_groups(request):
    """Get the list of available security groups."""
    response = ec2_client(request).describe_security_groups()
    return to_wrapping_list(response, "SecurityGroups", SecurityGroup)


def get_security_group(request, sg_name):
    """Get security groups."""
    try:
        response = ec2_client(request).describe_security_groups(GroupNames=[sg_name])
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
            return None
        else:
            return None
    return to_wrapping_list(response, "SecurityGroups", SecurityGroup)[0]


def create_security_group(request, name, desc):
    """Create security group."""
    response = ec2_client(request).create_security_group(GroupName=name, Description=desc)
    return SecurityGroup(response)


def delete_security_group(request, sg_id):
    """Delete Security Group."""
    ec2_client(request).delete_security_group(GroupId=sg_id)


def create_security_group_rule(request, *arg, **kwargs):
    """Create security group rule."""
    response = ec2_client(request).create_security_group_rule(*arg, **kwargs)
    return SecurityGroup(response)


def update_security_group(request, group_id, name, desc):
    """Update security group."""
    response = ec2_client(request).update_security_group(
        GroupId=group_id,
        GroupName=name,
        Description=desc
    )
    return SecurityGroup(response)


def list_keypairs(request):
    """Get the list of ssh key."""
    response = ec2_client(request).describe_key_pairs()
    return to_wrapping_list(response, "KeyPairs", KeyPair)


def get_keypair(request, key_name):
    """Get ssh key."""
    response = ec2_client(request).describe_key_pairs(KeyNames=[key_name])
    return to_wrapping_list(response, "KeyPairs", KeyPair)[0]


def create_keypair(request, key_name):
    """create ssh key."""
    response = ec2_client(request).create_key_pair(KeyName=key_name)
    return KeyPair(response)


def delete_keypair(request, key_name):
    """delete ssh key."""
    response = ec2_client(request).delete_key_pair(KeyName=key_name)
    return response


def import_keypair(request, key_name, public_key):
    """import ssh key."""
    response = ec2_client(request).import_key_pair(
        KeyName=key_name,
        PublicKeyMaterial=public_key
    )
    return KeyPair(response)


def import_openstack_keypair(request, os_key_name):
    """import openstack keypair."""
    os_keypair = nova.keypair_get(request, os_key_name)
    return import_keypair(
        request,
        os_keypair.name,
        os_keypair.public_key
    )


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
