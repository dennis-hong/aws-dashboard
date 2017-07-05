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
import logging
import os
from time import sleep

from openstack_dashboard.api import nova
from openstack_dashboard.api import glance

from aws_dashboard.api import ec2
from aws_dashboard.api import s3
from aws_dashboard.api import transport
from aws_dashboard.api.hybrid import utils

LOG = logging.getLogger(__name__)


# TODO : https://wiki.openstack.org/wiki/TaskFlow should be applied
def export_instance(request, instance_id, instance_name, status_check_interval):
    """Export instance image to S3"""
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = utils.get_api_keys(project_id)

    buckets = s3.list_buckets(request)
    if project_id not in buckets:
        s3.create_bucket(request, project_id, region_name)
        s3.grant_bucket_acl(request, project_id)

    task_id = ec2.export_instance_to_s3(request, instance_id, project_id, instance_name)
    # TODO : from oslo_service.loopingcall import FixedIntervalLoopingCall should be applied
    while True:
        task = transport.get_export_task(request, task_id)
        task_state = task.get("State")
        if task_state is None:
            raise KeyError("export instance task state is None")
        LOG.debug("Export Task State : {}".format(task_state))
        sleep(status_check_interval)
        if task_state == "completed":
            LOG.debug("VM export ready!!")
            break
    return task


def download_image_from_s3(request, target_obj, download_path):
    """Download instance image file from s3"""
    return s3.download_object(request, target_obj, download_path)


def convert_image_format(target_file_path, convert_format, delete_origin=True):
    """Convert Image Format"""
    return utils.convert_image_format(target_file_path, convert_format, delete_origin)


def upload_image_to_glance(request, image_name, image_file_path, image_format, interval):
    image = glance.image_create(request,
                                name=image_name,
                                is_public="False",
                                disk_format=image_format,
                                data=open(image_file_path, 'rb'),
                                container_format="bare")
    while True:
        image = glance.image_get(request, image.id)
        LOG.debug("Image Upload Status : {}".format(image.status))
        if image.status == "active":
            break
        sleep(interval)
    LOG.debug("Image Upload Complete")
    return image


def create_instance(request, name, image, flavor, key_name, user_data,
                    security_groups, block_device_mapping=None,
                    block_device_mapping_v2=None, nics=None,
                    availability_zone=None, instance_count=1, admin_pass=None,
                    disk_config=None, config_drive=None, meta=None,
                    scheduler_hints=None):
    """Create OpenStack Instance Using Exported Image"""
    LOG.debug('Create OpenStack Instance : %s (%s)' % (name, image.name))
    return nova.server_create(request, name, image, flavor, key_name, user_data,
                              security_groups, block_device_mapping=block_device_mapping,
                              block_device_mapping_v2=block_device_mapping_v2, nics=nics,
                              availability_zone=availability_zone, instance_count=instance_count,
                              admin_pass=admin_pass, disk_config=disk_config, config_drive=config_drive,
                              scheduler_hints=scheduler_hints, meta=meta)


def delete_s3_object(request, object_name):
    """Delete s3 image"""
    bucket_name = request.user.tenant_id
    s3.delete_object(request, bucket_name, object_name)


def delete_file(file_path):
    """Delete Local File"""
    os.remove(file_path)


def delete_instance(request, instance_id):
    """Delete EC2 Instance"""
    return ec2.delete_instance(request, instance_id)


def delete_glance_image(request, image_id):
    """Delete Glance Image"""
    LOG.debug('Delete Glance Image : %s' % image_id)
    return glance.image_delete(request, image_id)
