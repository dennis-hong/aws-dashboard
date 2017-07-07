# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
# Copyright 2012 OpenStack Foundation
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

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from aws_dashboard.content.aws.access_and_security.\
    floating_ips.tables import FloatingIPsTable
from aws_dashboard.content.aws.access_and_security.\
    keypairs.tables import KeypairsTable
from aws_dashboard.content.aws.access_and_security.\
    security_groups.tables import SecurityGroupsTable

from aws_dashboard.api import ec2


class SecurityGroupsTab(tabs.TableTab):
    table_classes = (SecurityGroupsTable,)
    name = _("Security Groups")
    slug = "security_groups_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_security_groups_data(self):
        try:
            security_groups = ec2.list_security_groups(self.request)
        except Exception:
            security_groups = []
            exceptions.handle(self.request,
                              _('Unable to retrieve security groups.'))
        return sorted(security_groups, key=lambda group: group.name)


class KeypairsTab(tabs.TableTab):
    table_classes = (KeypairsTable,)
    name = _("Key Pairs")
    slug = "keypairs_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_keypairs_data(self):
        try:
            keypairs = ec2.list_keypairs(self.request)
        except Exception:
            keypairs = []
            exceptions.handle(self.request,
                              _('Unable to retrieve key pair list.'))
        return keypairs


# TODO : TBD
class FloatingIPsTab(tabs.TableTab):
    table_classes = (FloatingIPsTable,)
    name = _("Floating IPs")
    slug = "floating_ips_tab"
    template_name = "horizon/common/_detail_table.html"

    def get_floating_ips_data(self):
        try:
            floating_ips = []
        except Exception:
            floating_ips = []
            exceptions.handle(self.request,
                              _('Unable to retrieve floating IP addresses.'))

        try:
            floating_ip_pools = []
        except Exception:
            floating_ip_pools = []
            exceptions.handle(self.request,
                              _('Unable to retrieve floating IP pools.'))
        pool_dict = dict([(obj.id, obj.name) for obj in floating_ip_pools])

        attached_instance_ids = [ip.instance_id for ip in floating_ips
                                 if ip.instance_id is not None]
        if attached_instance_ids:
            instances = []
            try:
                instances  = []
            except Exception:
                exceptions.handle(self.request,
                                  _('Unable to retrieve instance list.'))

            instances_dict = dict([(obj.id, obj.name) for obj in instances])

            for ip in floating_ips:
                ip.instance_name = instances_dict.get(ip.instance_id)
                ip.pool_name = pool_dict.get(ip.pool, ip.pool)

        return floating_ips


class AccessAndSecurityTabs(tabs.TabGroup):
    slug = "access_security_tabs"
    tabs = (SecurityGroupsTab, KeypairsTab)
    sticky = True
