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

from openstack_dashboard.api import base

from aws_dashboard.api.ec2 import ec2_client
from aws_dashboard.api.hybrid.utils import to_wrapping_list

LOG = logging.getLogger(__name__)


class ExportTask(base.APIDictWrapper):
    _attrs = ["id", "name", "status", "status_message", "instance_id", "object_name", "bucket_name", "progress"]

    def __init__(self, apidict):
        apidict["id"] = apidict.get("ExportTaskId")
        apidict["type"] = "Export"
        apidict["state"] = apidict.get("State", "None")
        apidict["status_message"] = apidict.get("StatusMessage")
        apidict["progress"] = "-"
        apidict["instance_id"] = apidict.get("InstanceExportDetails", {}).get("InstanceId")
        apidict["instance_name"] = apidict.get("Description", {})
        apidict["object_name"] = apidict.get("ExportToS3Task", {}).get("S3Key")
        apidict["bucket_name"] = apidict.get("ExportToS3Task", {}).get("S3Bucket")
        super(ExportTask, self).__init__(apidict)


class ImportTask(base.APIDictWrapper):
    _attrs = ["id", "name", "status", "status_message", "instance_id", "object_name", "bucket_name", "progress"]

    def __init__(self, apidict):
        apidict["id"] = apidict.get("ImportTaskId")
        apidict["type"] = "Import"
        apidict["state"] = apidict.get("Status", "None")
        apidict["status_message"] = apidict.get("StatusMessage")
        apidict["progress"] = apidict.get("Progress")
        apidict["instance_id"] = "-"
        apidict["instance_name"] = apidict.get("Description", {})
        apidict["object_name"] = apidict.get("SnapshotDetails")[0].get("UserBucket", {}).get("S3Key")
        apidict["bucket_name"] = apidict.get("SnapshotDetails")[0].get("UserBucket", {}).get("S3Bucket")
        super(ImportTask, self).__init__(apidict)


def list_export_task(request):
    response = ec2_client(request).describe_export_tasks()
    return to_wrapping_list(response, "ExportTasks", ExportTask)


def list_import_image_task(request):
    response = ec2_client(request).describe_import_image_tasks()
    return to_wrapping_list(response, "ImportImageTasks", ImportTask)


def get_export_task(request, task_id):
    response = ec2_client(request).describe_export_tasks(ExportTaskIds=[task_id])
    return ExportTask(response.get("ExportTasks")[0])


def get_import_image_task(request, task_id):
    response = ec2_client(request).describe_import_image_tasks(ImportTaskIds=[task_id])
    return ImportTask(response.get('ImportImageTasks')[0])


def cancel_export_task(request, task_id):
    ec2_client(request).cancel_export_task(ExportTaskIds=[task_id])


def cancel_import_task(request, task_id):
    ec2_client(request).cancel_import_task(ImportTaskIds=[task_id])

