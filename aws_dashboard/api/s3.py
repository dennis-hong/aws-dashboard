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

from horizon.utils.memoized import memoized  # noqa

from boto3.s3.transfer import S3Transfer
from aws_dashboard.api import utils

LOG = logging.getLogger(__name__)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)

try:
    import boto3
except ImportError:
    LOG.error("import boto3 failed. please pip install boto3")


@memoized
def s3_client(request):
    project_id = request.user.tenant_id
    aws_access_key_id, aws_secret_access_key, region_name = utils.get_api_keys(project_id)
    session = boto3.session.Session(aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key,
                                    region_name=region_name)
    return session.client('s3')


def list_buckets(request):
    response = s3_client(request).list_buckets()
    return [bucket['Name'] for bucket in response['Buckets']]


def upload_object(request, file_path, object_name=None):
    if not object_name:
        object_name = file_path
    project_id = request.user.tenant_id
    config = boto3.s3.transfer.TransferConfig(
        multipart_threshold=64 * 1024 * 1024,
        max_concurrency=10,
        num_download_attempts=10,
        multipart_chunksize=16 * 1024 * 1024,
        max_io_queue=10000
    )

    transfer = S3Transfer(s3_client(request), config)
    transfer.upload_file(file_path, project_id, object_name, callback=ProgressPercentage(file_path))
    LOG.debug('Upload Complete : %s' % file_path)


def create_bucket(request, bucket_name, region):
    return s3_client(request).create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': region}
    )


def delete_object(request, bucket_name, object_name):
    return s3_client(request).delete_object(
        Bucket=bucket_name,
        Key=object_name
    )


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            if round(percentage) % 5 == 0:
                LOG.debug(("%s  %s / %s  (%.2f%%)"
                           % (self._filename, self._seen_so_far, self._size, percentage)))
