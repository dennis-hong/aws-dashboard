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
import time

from django.conf import settings

from openstack_dashboard.api import glance
from aws_dashboard.api import ec2

from aws_dashboard.api.hybrid import utils
import aws_dashboard.api.hybrid.import_instance_tasks as import_task
import aws_dashboard.api.hybrid.export_instance_tasks as export_task

LOG = logging.getLogger(__name__)
OPENSTACK_IMAGE_FORMAT = getattr(settings, "OPENSTACK_IMAGE_FORMAT", "qcow2")
CONVERT_IMAGE_FORMAT = getattr(settings, "CONVERT_IMAGE_FORMAT", "raw")
IMAGE_TASK_WORKING_PATH = getattr(settings, "IMAGE_TASK_WORKING_PATH", "/tmp")
STATUS_CHECK_INTERVAL = getattr(settings, "STATUS_CHECK_INTERVAL", 10)


def run_import_instance_tasks(request, source_type, source_id, flavor, key_name,
                              security_groups, availability_zone, instance_count,
                              leave_original_instance, leave_instance_snapshot):
    """Import instance task flow"""
    start_time = time.time()
    LOG.debug("Start Import Instance. Receive Data : {}".format(request.DATA))
    if source_type == "instance":
        image = import_task.create_snapshot(request, source_id, STATUS_CHECK_INTERVAL)
    else:
        image = glance.image_get(request, source_id)

    file_path = import_task.download_image(request, image, IMAGE_TASK_WORKING_PATH)
    new_file_path = import_task.convert_image_format(file_path, CONVERT_IMAGE_FORMAT)
    import_task.upload_to_s3(request, new_file_path, image.name)
    size = utils.get_file_size_gb(new_file_path)
    import_task.delete_file(new_file_path)

    if source_type == "instance" and not leave_instance_snapshot:
        import_task.delete_original_snapshot(request, image)

    import_image = import_task.import_image(request, image.name, size,
                                            CONVERT_IMAGE_FORMAT, STATUS_CHECK_INTERVAL)
    new_instance = import_task.create_instance(request=request,
                                               name=import_image.get("Description"),
                                               image_id=import_image.get("ImageId"),
                                               flavor=flavor,
                                               key_name=key_name,
                                               security_groups=security_groups,
                                               availability_zone=availability_zone,
                                               instance_count=instance_count)
    import_task.delete_s3_object(request, image.name)

    if source_type == "instance" and not leave_original_instance:
        import_task.delete_original_instance(request, source_id)

    duration = round((time.time() - start_time) / 60, 1)
    LOG.debug("Complete Import Instance. Duration : {} min.".format(duration))

    return new_instance


def run_export_instance_tasks(request, name, source_id, flavor, key_name, user_data,
                              security_groups, leave_original_instance, leave_instance_snapshot,
                              block_device_mapping=None,
                              block_device_mapping_v2=None, nics=None,
                              availability_zone=None, instance_count=1, admin_pass=None,
                              disk_config=None, config_drive=None, meta=None,
                              scheduler_hints=None):
    """Export instance task flow"""
    start_time = time.time()
    LOG.debug("Start Export Instance. Receive Data : {}".format(request.DATA))
    task = export_task.export_instance(request, source_id, name, STATUS_CHECK_INTERVAL)
    obj_name = task.get("ExportToS3Task").get("S3Key")

    download_path = export_task.download_image_from_s3(request, obj_name, IMAGE_TASK_WORKING_PATH)
    new_file_path = export_task.convert_image_format(download_path, OPENSTACK_IMAGE_FORMAT)
    image = export_task.upload_image_to_glance(request, obj_name, new_file_path,
                                               OPENSTACK_IMAGE_FORMAT, STATUS_CHECK_INTERVAL)
    export_task.delete_file(new_file_path)

    new_instance = export_task.create_instance(
        request, name, image, flavor, key_name, user_data, security_groups,
        block_device_mapping=block_device_mapping,
        block_device_mapping_v2=block_device_mapping_v2, nics=nics,
        availability_zone=availability_zone,
        instance_count=instance_count,
        admin_pass=admin_pass, disk_config=disk_config,
        config_drive=config_drive, meta=meta,
        scheduler_hints=scheduler_hints
    )

    export_task.delete_s3_object(request, obj_name)
    if not leave_original_instance:
        export_task.delete_instance(request, source_id)
    if not leave_instance_snapshot:
        export_task.delete_glance_image(request, image.id)
    duration = round((time.time() - start_time) / 60, 1)
    LOG.debug("Complete Import Instance. Duration : {} min.".format(duration))

    return new_instance
