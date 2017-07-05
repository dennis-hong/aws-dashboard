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
import threading

import boto3
from boto3.s3.transfer import S3Transfer
from horizon.utils.memoized import memoized  # noqa

from aws_dashboard.api.hybrid import utils

LOG = logging.getLogger(__name__)
logging.getLogger("s3transfer").setLevel(logging.CRITICAL)
s3_config = boto3.s3.transfer.TransferConfig(
    multipart_threshold=64 * 1024 * 1024,
    max_concurrency=10,
    num_download_attempts=10,
    multipart_chunksize=16 * 1024 * 1024,
    max_io_queue=10000
)


@memoized
def s3_client(request):
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = utils.get_api_keys(project_id)
    session = boto3.session.Session(aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key,
                                    region_name=region_name)
    return session.client("s3")


def list_buckets(request):
    response = s3_client(request).list_buckets()
    return [bucket["Name"] for bucket in response["Buckets"]]


def upload_object(request, file_path, object_name=None):
    LOG.debug("Start Upload To S3 Image File  : %s" % file_path)
    if not object_name:
        object_name = file_path
    project_id = request.user.tenant_id
    transfer = S3Transfer(s3_client(request), s3_config)
    transfer.upload_file(file_path, project_id, object_name, callback=UploadProgress(file_path))
    LOG.debug("Upload Complete : %s" % file_path)


def download_object(request, object_name, download_dir):
    bucket_name = request.user.tenant_id
    download_path = "%s/%s" % (download_dir, object_name)
    LOG.debug('Start Download S3 Object : %s/%s"' % (bucket_name, object_name))
    file_size = s3_client(request).head_object(Bucket=bucket_name, Key=object_name).get("ContentLength")
    transfer = S3Transfer(s3_client(request), s3_config)
    transfer.download_file(bucket_name, object_name, download_path,
                           callback=DownloadProgress(download_path, file_size))
    LOG.debug('Download S3 Object Complete : %s (%d MB)' % (download_path, round(file_size / 1024 / 1024)))
    return download_path


def create_bucket(request, bucket_name, region):
    LOG.debug("Create Bucket : %s (%s)" % (bucket_name, region))
    return s3_client(request).create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": region}
    )


def get_bucket_acl(request, bucket_name):
    return s3_client(request).get_bucket_acl(Bucket=bucket_name)


def get_bucket_owner_id(request, bucket_name):
    return get_bucket_acl(request, bucket_name).get("Owner", {}).get("ID")


def grant_bucket_acl(request, bucket_name):
    """Sets the permissions on a bucket using access control lists (ACL)."""
    owner_id = get_bucket_owner_id(request, bucket_name)
    LOG.debug("Grant Bucket ACL To Owner Id : %s Bucket : %s" % (owner_id, bucket_name))
    # AWS official account for export instance permission
    # http://docs.aws.amazon.com/vm-import/latest/userguide/vmexport.html
    aws_export_account = "c4d8eabf8db69dbe46bfe0e517100c554f01200b104d59cd408e777ba442a322"
    china_export_account = "834bafd86b15b6ca71074df0fd1f93d234b9d5e848a2cb31f880c149003ce36f"
    return s3_client(request).put_bucket_acl(
        AccessControlPolicy={
            "Grants": [
                {
                    "Grantee": {
                        "DisplayName": "aws_export_account",
                        "ID": aws_export_account,
                        "Type": "CanonicalUser"
                    },
                    "Permission": "FULL_CONTROL"
                },
                {
                    "Grantee": {
                        "DisplayName": "aws_china_export_account",
                        "ID": china_export_account,
                        "Type": "CanonicalUser"
                    },
                    "Permission": "FULL_CONTROL"
                },
                {
                    "Grantee": {
                        "DisplayName": "container_owner",
                        "ID": owner_id,
                        "Type": "CanonicalUser"
                    },
                    "Permission": "FULL_CONTROL"
                },
            ],
            "Owner": {
                "DisplayName": "container_owner",
                "ID": owner_id
            }
        },
        Bucket=bucket_name,
    )


def delete_object(request, bucket_name, object_name):
    LOG.debug("Delete S3 Object : %s/%s" % (bucket_name, object_name))
    return s3_client(request).delete_object(
        Bucket=bucket_name,
        Key=object_name
    )


class UploadProgress(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self.pre_percentage = -1

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = round(self._seen_so_far / self._size * 100)
            if percentage % 2 == 0 and not percentage == self.pre_percentage:
                self.pre_percentage = percentage
                LOG.debug(("Uploading : %s  %s / %s  (%d %%)"
                           % (self._filename, self._seen_so_far, self._size, percentage)))


class DownloadProgress(object):
    def __init__(self, file_name, file_size):
        self._filename = file_name
        self._size = float(file_size)
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self.pre_percentage = -1

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = round(self._seen_so_far / self._size * 100)
            if percentage % 2 == 0 and not percentage == self.pre_percentage:
                self.pre_percentage = percentage
                LOG.debug(("Downloading : %s  %s / %s  (%d %%)"
                          % (self._filename, self._seen_so_far, self._size, percentage)))
