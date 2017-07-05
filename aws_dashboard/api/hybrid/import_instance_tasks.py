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

from openstack_dashboard.api import glance
from openstack_dashboard.api import nova
from openstack_dashboard.api.glance import glanceclient

from aws_dashboard.api import ec2
from aws_dashboard.api import s3
from aws_dashboard.api import transport
from aws_dashboard.api.hybrid import utils

LOG = logging.getLogger(__name__)


# TODO : https://wiki.openstack.org/wiki/TaskFlow should be applied
def create_snapshot(request, instance_id, status_check_interval):
    """Create Snapshot"""
    instance = nova.server_get(request, instance_id)
    snapshot_id = nova.snapshot_create(request, instance.id, instance.name)
    LOG.debug("Target instance name : {} ({})".format(instance.name, instance.id))
    LOG.debug("Snapshot id : {}".format(snapshot_id))
    image = glance.image_get(request, snapshot_id)
    LOG.debug("Snapshot Image : {}".format(image))
    # TODO : from oslo_service.loopingcall import FixedIntervalLoopingCall should be applied
    while True:
        image = glance.image_get(request, snapshot_id)
        if (image or image.status) is None:
            LOG.error("Instance Snapshot Fail")
            break
        LOG.debug("Instance Snapshot Status : {}".format(image.status))
        sleep(status_check_interval)
        if image.status == "active":
            LOG.debug("Instance Snapshot Complete : {}".format(image))
            break
    return image


def download_image(request, image, download_path):
    """ download_image """
    file_path = "%s/%s.%s" % (download_path, image.name, image.disk_format)
    utils.validate_image_format(file_path)
    LOG.debug("download image file path : {}".format(file_path))

    image_file = open(file_path, "w+")
    image_data_iterable = glanceclient(request).images.data(image.id)
    try:
        LOG.debug("Start Image Download")
        for chunk in image_data_iterable:
            image_file.write(chunk)
        LOG.debug("Complete Image Download")
    finally:
        image_file.close()

    return file_path


def convert_image_format(target_file_path, convert_format, delete_origin=True):
    """ convert_image_format """
    return utils.convert_image_format(target_file_path, convert_format, delete_origin)


def upload_to_s3(request, target_file, object_name):
    """ Upload to s3. Create the container if it does not exist."""
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = utils.get_api_keys(project_id)

    buckets = s3.list_buckets(request)
    if project_id not in buckets:
        s3.create_bucket(request, project_id, region_name)
        s3.grant_bucket_acl(request, project_id)

    return s3.upload_object(request, target_file, object_name)


def import_image(request, object_name, object_size_gb, image_format, status_check_interval):
    """Import the image and wait for finish."""
    bucket_name = request.user.tenant_id
    task_id = ec2.import_image_from_s3(request, image_format, bucket_name, object_name, object_size_gb)

    while True:
        import_image_task = transport.get_import_image_task(request, task_id)
        if import_image_task == {} or None:
            LOG.debug("Import ImageTask Fail")
            break
        LOG.debug("Import ImageTask Status : %s (%s)"
                  % (import_image_task.get("StatusMessage"), import_image_task.get("Progress")))
        sleep(status_check_interval)
        if import_image_task.get("Progress") is None:
            LOG.debug("Complete Import Image Tasks : %s" % import_image_task)
            break
    return import_image_task


def create_instance(request, name, image_id, flavor, key_name,
                    security_groups, availability_zone, instance_count):
    """Create EC2 Instance using imported image"""
    LOG.debug("Create Instance : {} From Imported EC2 Image : {}".format(name, image_id))
    return ec2.create_instance(request, name, image_id, flavor, key_name,
                               security_groups, availability_zone, instance_count)


def delete_s3_object(request, object_name):
    """delete s3 image"""
    bucket_name = request.user.tenant_id
    s3.delete_object(request, bucket_name, object_name)


def delete_file(file_path):
    """delete s3 image"""
    LOG.debug("Delete File  : %s" % file_path)
    os.remove(file_path)


def delete_original_instance(request, instance_id):
    """delete original instance"""
    LOG.debug("Delete Original Instance : %s" % instance_id)
    nova.server_delete(request, instance_id)


def delete_original_snapshot(request, image):
    """delete original snapshot"""
    LOG.debug("Delete Original Instance Snapshot : {} ({})"
              .format(image.name, image.id))
    glance.image_delete(request, image.id)
