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
import os
import logging
import subprocess

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from horizon.utils.memoized import memoized  # noqa

LOG = logging.getLogger(__name__)
SUPPORT_IMAGE_FORMATS = ["qcow2", "vmdk", "raw"]


@memoized
def get_api_keys(project_id):
    keys_dict = getattr(settings, "AWS_API_KEY_DICT", {})
    key_set = keys_dict.get(project_id)
    _validate_key_set(key_set)
    return key_set.get("AWS_ACCESS_KEY_ID"), key_set.get("AWS_SECRET_ACCESS_KEY"), key_set.get("AWS_REGION_NAME")


def _validate_key_set(key_set):
    error_msg = """AWS API Key Not Found. Please Check in
                   local/local_settings.d/_30000_aws_dashboard.py"""

    if key_set is None:
        LOG.error("Not Found AWS API key set.")
        raise ImproperlyConfigured(error_msg)
    aws_access_key_id = key_set.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key = key_set.get("AWS_SECRET_ACCESS_KEY", "")
    region_name = key_set.get("AWS_REGION_NAME", "")
    if aws_access_key_id == "" or aws_secret_access_key == "" or region_name == "":
        LOG.error("""aws_access_key_id : %s
                  aws_secret_access_key : %s
                  region_name: %s""" %
                  (aws_access_key_id, aws_secret_access_key, region_name))
        raise ImproperlyConfigured(error_msg)


def validate_image_format(file_path):
    file_extension = os.path.splitext(file_path)[1][1:]
    if file_extension not in SUPPORT_IMAGE_FORMATS:
        raise BaseException("{} file not support format({})"
                            .format(file_path, file_extension))


def get_file_size_gb(file_path):
    """Get File Size by GB"""
    if os.path.exists(file_path):
        size = round((os.path.getsize(file_path) / 1024 / 1024 / 1024), 1)
        LOG.debug("Target File Size : {} ({} GB)".format(file_path, size))
        return size
    else:
        return 0


def to_wrapping_list(aws_list, key, wrapper_cls):
    """Wrapping List To OpenStack Horizon Format"""
    openstack_list = []
    for value in aws_list.get(key):
        openstack_list.append(wrapper_cls(value))
    return openstack_list


def convert_image_format(target_file_path, convert_format, delete_origin=True):
    """ Convert Image Format """
    validate_image_format(target_file_path)
    file_name, file_extension = os.path.splitext(target_file_path)
    new_file_path = file_name + "." + convert_format
    LOG.debug("Start Convert Image : %s" % target_file_path)
    cmd = ["qemu-img", "convert", "-O", convert_format, target_file_path, new_file_path]

    if convert_format == "qcow2":
        cmd = ["qemu-img", "convert", "-O", convert_format, "-c", target_file_path, new_file_path]

    subprocess.call(cmd)
    LOG.debug("Finish Convert Image : %s" % new_file_path)

    if delete_origin:
        os.remove(target_file_path)
        LOG.debug("Remove original image file : {}".format(target_file_path))

    return new_file_path
