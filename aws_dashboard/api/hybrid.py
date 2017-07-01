import os
import logging
import subprocess
from eventlet import sleep

from openstack_dashboard.api import nova
from openstack_dashboard.api import glance
from openstack_dashboard.api.glance import glanceclient

from aws_dashboard.api import ec2
from aws_dashboard.api import s3
from aws_dashboard.api import utils

LOG = logging.getLogger(__name__)
IMAGE_TASK_WORKING_PATH = "/tmp"
CONVERT_IMAGE_FORMAT = "raw"
STATUS_CHECK_INTERVAL = 10


def run_import_instance(request, source_type, source_id,
                        leave_original_instance, leave_instance_snapshot):
    """import instance task flow"""
    LOG.debug("Import Instance Receive Data : {}".format(request.DATA))
    try:
        if source_type == 'instance':
            image = create_snapshot(request, source_id)
        else:
            image = glance.image_get(request, source_id)
        file_path = download_image(request, image)
        new_file_path = convert_image_format(file_path, CONVERT_IMAGE_FORMAT)

        LOG.debug('Start Upload To S3 Image File  : %s' % new_file_path)
        upload_to_s3(request, new_file_path, image.name)
        size = utils.get_file_size_gb(new_file_path)
        os.remove(new_file_path)
        LOG.debug('Delete Converted Image File  : %s' % new_file_path)

        if source_type == 'instance' and not leave_instance_snapshot:
            glance.image_delete(request, image.id)
            LOG.debug('Origin Images Deleted : {}'.format(image.id))

        image_id = import_image(request, image.name, size)
        ec2.create_instance(request,
                            name=image.name,
                            image_id=image_id,
                            flavor=request.DATA.get("flavor_id"),
                            key_name=request.DATA.get("key_name"),
                            security_groups=request.DATA.get("security_groups"),
                            availability_zone=request.DATA.get("availability_zone"),
                            instance_count=request.DATA.get("instance_count"))
        delete_s3_object(request, image.name)

        if source_type == 'instance' and not leave_original_instance:
            nova.server_delete(request, source_id)
            LOG.debug('Origin Instance Deleted : {}'.format(source_id))

    except Exception as exc:
        LOG.error("Unexpected Error : {}".format(exc.message))


def create_snapshot(request, instance_id):
    """Create Snapshot"""
    instance = nova.server_get(request, instance_id)
    snapshot_id = nova.snapshot_create(request, instance.id, instance.name)
    LOG.debug('Target instance name : {} ({})'.format(instance.name, instance.id))
    LOG.debug('Snapshot id : {}'.format(snapshot_id))
    image = glance.image_get(request, snapshot_id)
    LOG.debug('Snapshot Image : {}'.format(image))

    while True:
        image = glance.image_get(request, snapshot_id)
        if (image or image.status) is None:
            LOG.error("Instance Snapshot Fail")
            break
        LOG.debug("Instance Snapshot Status : {}".format(image.status))
        sleep(STATUS_CHECK_INTERVAL)
        if image.status == "active":
            LOG.debug("Instance Snapshot Complete : {}".format(image))
            break
    return image


def download_image(request, image):
    """ download_image """
    file_path = "%s/%s.%s" % (IMAGE_TASK_WORKING_PATH, image.name, image.disk_format)
    utils.validate_image_format(file_path)
    LOG.debug('download image file path : {}'.format(file_path))

    image_file = open(file_path, 'w+')
    image_data_iterable = glanceclient(request).images.data(image.id)
    try:
        LOG.debug('Start Image Download')
        for chunk in image_data_iterable:
            image_file.write(chunk)
        LOG.debug('Complete Image Download')
    finally:
        image_file.close()

    return file_path


def convert_image_format(target_file_path, convert_format, delete_origin=True):
    """ convert_image_format """
    utils.validate_image_format(target_file_path)
    file_name, file_extension = os.path.splitext(target_file_path)
    new_file_path = file_name + '.' + convert_format
    LOG.debug('origin image path : %s' % target_file_path)
    LOG.debug('convert image path : %s' % new_file_path)
    cmd = ['qemu-img', 'convert', '-O', convert_format, target_file_path, new_file_path]
    subprocess.call(cmd)

    if delete_origin:
        os.remove(target_file_path)
        LOG.debug('remove original image file : {}'.format(target_file_path))

    return new_file_path


def upload_to_s3(request, target_file, image_name):
    """ Upload to s3 """
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = utils.get_api_keys(project_id)

    buckets = s3.list_buckets(request)
    if project_id not in buckets:
        s3.create_bucket(request, project_id, region_name)
        LOG.debug('buckets create : {} (region_name)'.format(project_id, region_name))

    return s3.upload_object(request, target_file, image_name)


def import_image(request, object_name, object_size_gb):
    """import image and wait complete"""
    bucket_name = request.user.tenant_id
    task_id = ec2.import_image_from_s3(request, CONVERT_IMAGE_FORMAT, bucket_name, object_name, object_size_gb)

    while True:
        import_image_task = ec2.get_import_image_tasks(request, task_id)
        if import_image_task == {} or None:
            LOG.debug("Import ImageTask Fail")
            break
        LOG.debug('Import ImageTask Status : %s (%s)'
                  % (import_image_task.get('StatusMessage'), import_image_task.get('Progress')))
        sleep(STATUS_CHECK_INTERVAL)
        if import_image_task.get('Progress') is None:
            LOG.debug('Complete Import Image Tasks : %s' % import_image_task)
            break
    return import_image_task.get('ImageId')


def delete_s3_object(request, object_name):
    bucket_name = request.user.tenant_id
    s3.delete_object(request, bucket_name, object_name)
