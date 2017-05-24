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

import tables as aws_tables
from aws_dashboard.api.ec2 import list_instance


LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = aws_tables.Ec2InstanceTable
    template_name = 'aws/ec2/index.html'
    page_title = _("EC2 Instances")

    def get_data(self):
        instances = []
        try:
            instances = list_instance(self.request)
        except ImproperlyConfigured:
            exceptions.handle(self.request, _("Not Found AWS API KEY in this project."))
        except Exception:
            exceptions.handle(self.request, _("Unable to retrieve instances."))
        return instances


