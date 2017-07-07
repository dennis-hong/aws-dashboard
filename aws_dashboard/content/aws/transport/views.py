# Copyright (c) 2017 dennis.hong.
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
"""
Views for managing EC2 instances.
"""
import logging

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured
from horizon import tables
from horizon import exceptions

from aws_dashboard.api.transport import list_export_task
from aws_dashboard.api.transport import list_import_image_task
from aws_dashboard.content.aws.transport.tables import TransportTaskTable


LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = TransportTaskTable
    template_name = 'aws/transport/index.html'
    page_title = _("Transport Task")

    def get_data(self):
        transport_tasks = []
        try:
            export_tasks = list_export_task(self.request)
            import_tasks = list_import_image_task(self.request)
            transport_tasks = export_tasks + import_tasks
        except ImproperlyConfigured:
            exceptions.handle(self.request, _("Not Found AWS API KEY in this project."))
        except Exception:
            exceptions.handle(self.request, _("Unable to retrieve transport list."))
        return transport_tasks
