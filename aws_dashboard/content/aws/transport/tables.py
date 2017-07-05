# Copyright 2017 dennis.hong.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import logging

from horizon import tables
from django.template.defaultfilters import title  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.utils.translation import ungettext_lazy

from aws_dashboard.api import transport

LOG = logging.getLogger(__name__)
TASK_DISPLAY_NONE = pgettext_lazy("Task status of an Instance", u"None")
STATUS_CHOICES = (
    ("completed", True),
    ("stopped", False),
    ("error", False),
    ("cancelled", False),
)


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, task_id):
        if task_id.startswith("import"):
            task = transport.get_import_image_task(request, task_id)
        elif task_id.startswith("export"):
            task = transport.get_export_task(request, task_id)
        else:
            task = None
        return task


class CancelTask(tables.DeleteAction):
    help_text = _("Canceld instances are not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Cancel Task",
            u"Cancel Tasks",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled Cancel of Task",
            u"Scheduled Cancel of Tasks",
            count
        )

    def action(self, request, obj_id):
        if obj_id.startswith("import"):
            transport.cancel_import_task(request, obj_id)
        elif obj_id.startswith("export"):
            transport.cancel_export_task(request, obj_id)
        else:
            pass


class InstancesFilterAction(tables.FilterAction):
    filter_type = "query"
    filter_choices = (('type', _("Task Type ="), True),
                      ('id', _("Task ID ="), True),
                      ('instance_id', _("Instance ID ="), True),
                      ('instance_name', _("Instance Name ="), True),
                      ('status_message', _("Status Message ="), True),
                      ('state', _("State ="), True))


class TransportTaskTable(tables.DataTable):
    type = tables.WrappingColumn("type",
                                 verbose_name=_("Task Type"))
    id = tables.WrappingColumn("id",
                               verbose_name=_("Task ID"))
    instance_id = tables.Column("instance_id",
                                verbose_name=_("Instance ID"))
    instance_name = tables.Column("instance_name",
                                  verbose_name=_("Instance Name"))
    status_message = tables.Column("status_message", verbose_name=_("Status Message"))
    state = tables.Column("state",
                          verbose_name=_("State"),
                          empty_value=TASK_DISPLAY_NONE,
                          filters=(title,),
                          status=True,
                          status_choices=STATUS_CHOICES)
    progress = tables.Column("progress",
                             verbose_name=_("Progress"))

    class Meta(object):
        name = "EC2"
        verbose_name = _("EC2 Instances")
        status_columns = ["state", ]
        row_class = UpdateRow
        table_actions = (InstancesFilterAction, CancelTask)
        row_actions = (CancelTask,)
