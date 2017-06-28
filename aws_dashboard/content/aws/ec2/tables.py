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

from django.core import urlresolvers
from django.http import HttpResponse  # noqa
from django import template
from django.template.defaultfilters import title  # noqa
from django.utils.translation import npgettext_lazy
from django.utils.translation import pgettext_lazy
from django.utils.translation import string_concat  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon.utils import filters

from openstack_dashboard import api

from aws_dashboard.api import ec2


LOG = logging.getLogger(__name__)

ACTIVE_STATES = ("running",)
VOLUME_ATTACH_READY_STATES = ("running",)
SNAPSHOT_READY_STATES = ("running",)


def is_deleting(instance):
    return get_state(instance) == "shutting-down"


class DeleteInstance(tables.DeleteAction):
    help_text = _("Deleted instances are not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Instance",
            u"Delete Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Instance",
            u"Scheduled deletion of Instances",
            count
        )

    def allowed(self, request, instance=None):
        """Allow delete action if instance is in error state or not currently
        being deleted.
        """
        error_state = False
        if instance:
            error_state = (instance.status == 'ERROR')
        return error_state or not is_deleting(instance)

    def action(self, request, obj_id):
        ec2.delete_instance(request, obj_id)


class RebootInstance(tables.BatchAction):
    name = "reboot"
    classes = ('btn-reboot',)
    help_text = _("Restarted instances will lose any data"
                  " not saved in persistent storage.")
    action_type = "danger"

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Hard Reboot Instance",
            u"Hard Reboot Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Hard Rebooted Instance",
            u"Hard Rebooted Instances",
            count
        )

    def allowed(self, request, instance=None):
        if instance is not None:
            return ((get_state(instance) in ACTIVE_STATES)
                    and not is_deleting(instance))
        else:
            return True

    def action(self, request, obj_id):
        ec2.reboot_instance(request, obj_id)


class LaunchLink(tables.LinkAction):
    name = "launch"
    verbose_name = _("Launch Instance")
    url = "horizon:aws:ec2:launch"
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"
    ajax = True

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        super(LaunchLink, self).__init__(attrs, **kwargs)

    def allowed(self, request, datum):
        try:
            limits = api.nova.tenant_absolute_limits(request, reserved=True)

            instances_available = limits['maxTotalInstances'] \
                - limits['totalInstancesUsed']
            cores_available = limits['maxTotalCores'] \
                - limits['totalCoresUsed']
            ram_available = limits['maxTotalRAMSize'] - limits['totalRAMUsed']

            if instances_available <= 0 or cores_available <= 0 \
                    or ram_available <= 0:
                if "disabled" not in self.classes:
                    self.classes = [c for c in self.classes] + ['disabled']
                    self.verbose_name = string_concat(self.verbose_name, ' ',
                                                      _("(Quota exceeded)"))
            else:
                self.verbose_name = _("Launch Instance")
                classes = [c for c in self.classes if c != "disabled"]
                self.classes = classes
        except Exception:
            LOG.exception("Failed to retrieve quota information")
            # If we can't get the quota information, leave it to the
            # API to check when launching
        return True  # The action should always be displayed

    def single(self, table, request, object_id=None):
        self.allowed(request, None)
        return HttpResponse(self.render(is_table_action=True))


class LaunchLinkNG(LaunchLink):
    name = "launch-ng"
    url = "horizon:aws:ec2:index"
    ajax = False
    classes = ("btn-launch", )

    def get_default_attrs(self):
        url = urlresolvers.reverse(self.url)
        ngclick = "modal.openLaunchEC2InstanceWizard(" \
            "{ successUrl: '%s' })" % url
        self.attrs.update({
            'ng-controller': 'LaunchEC2InstanceModalController as modal',
            'ng-click': ngclick
        })
        return super(LaunchLinkNG, self).get_default_attrs()

    def get_link_url(self, datum=None):
        return "javascript:void(0);"


class ImportInstanceLink(tables.LinkAction):
    name = "import_instance"
    verbose_name = _("Import Instance")
    url = "horizon:aws:ec2:import_instance"
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-download"
    ajax = True

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        super(ImportInstanceLink, self).__init__(attrs, **kwargs)

    def single(self, table, request, object_id=None):
        self.allowed(request, None)
        return HttpResponse(self.render(is_table_action=True))


class ImportInstanceLinkNG(ImportInstanceLink):
    name = "import_instance-ng"
    url = "horizon:aws:ec2:index"
    ajax = False
    classes = ("btn-launch", )

    def get_default_attrs(self):
        url = urlresolvers.reverse(self.url)
        ngclick = "modal.openImportEC2InstanceWizard(" \
            "{ successUrl: '%s' })" % url
        self.attrs.update({
            'ng-controller': 'ImportEC2InstanceModalController as modal',
            'ng-click': ngclick
        })
        return super(ImportInstanceLinkNG, self).get_default_attrs()

    def get_link_url(self, datum=None):
        return "javascript:void(0);"


def instance_fault_to_friendly_message(instance):
    fault = getattr(instance, 'fault', {})
    message = fault.get('message', _("Unknown"))
    default_message = _("Please try again later [Error: %s].") % message
    fault_map = {
        'NoValidHost': _("There is not enough capacity for this "
                         "flavor in the selected availability zone. "
                         "Try again later or select a different availability "
                         "zone.")
    }
    return fault_map.get(message, default_message)


def get_instance_error(instance):
    if instance.status.lower() != 'error':
        return None
    message = instance_fault_to_friendly_message(instance)
    preamble = _('Failed to perform requested operation on instance "%s", the '
                 'instance has an error status') % instance.name or instance.id
    message = string_concat(preamble, ': ', message)
    return message


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, instance_id):
        instance = ec2.get_instance(request, instance_id)
        return instance


class StartInstance(tables.BatchAction):
    name = "start"
    classes = ('btn-confirm',)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Start Instance",
            u"Start Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Started Instance",
            u"Started Instances",
            count
        )

    def allowed(self, request, instance=None):
        return ((instance is not None) and
                (get_state(instance) in ("stopped", )))

    def action(self, request, obj_id):
        ec2.start_instance(request, obj_id)


class StopInstance(tables.BatchAction):
    name = "stop"
    help_text = _("The instance(s) will be shut off.")
    action_type = "danger"

    @staticmethod
    def action_present(count):
        return npgettext_lazy(
            "Action to perform (the instance is currently running)",
            u"Shut Off Instance",
            u"Shut Off Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return npgettext_lazy(
            "Past action (the instance is currently already Shut Off)",
            u"Shut Off Instance",
            u"Shut Off Instances",
            count
        )

    def allowed(self, request, instance=None):
        return ((instance is not None)
                and ((get_state(instance) in ("running", ))
                and not is_deleting(instance)))

    def action(self, request, obj_id):
        ec2.stop_instance(request, obj_id)


def get_ips(instance):
    template_name = 'aws/ec2/_instance_ips.html'
    context = {
        "publicDnsName": getattr(instance, "PublicDnsName", ""),
        "publicIpAddress": getattr(instance, "PublicIpAddress", "")
    }
    return template.loader.render_to_string(template_name, context)


def get_state(instance):
    return getattr(instance, "State", {}).get("Name")


def get_az(instance):
    return getattr(instance, "Placement", {}).get("AvailabilityZone")


def get_launch_time(instance):
    datetime = getattr(instance, "LaunchTime", {})
    return datetime.isoformat()


TASK_DISPLAY_NONE = pgettext_lazy("Task status of an Instance", u"None")


STATUS_CHOICES = (
    ("running", True),
    ("stopped", False),
    ("error", False),
    ("terminated", False),
)


class InstancesFilterAction(tables.FilterAction):
    filter_type = "server"
    filter_choices = (('name', _("Instance Name ="), True),
                      ('status', _("Status ="), True),
                      ('image', _("Image ID ="), True),
                      ('flavor', _("Flavor ID ="), True))


class Ec2InstanceTable(tables.DataTable):
    name = tables.WrappingColumn("name",
                                 link="aws:ec2:instances:detail",
                                 verbose_name=_("Instance Name"))
    image_name = tables.Column("ImageId",
                               verbose_name=_("Image ID"))
    ip = tables.Column(get_ips,
                       verbose_name=_("Public Address"),
                       attrs={'data-type': "ip"})
    size = tables.Column("InstanceType", sortable=False, verbose_name=_("Size"))
    keypair = tables.Column("KeyName", verbose_name=_("Key Pair"))
    az = tables.Column(get_az,
                       verbose_name=_("Availability Zone"))
    status = tables.Column(get_state,
                           verbose_name=_("Status"),
                           empty_value=TASK_DISPLAY_NONE,
                           filters=(title, ),
                           status=True,
                           status_choices=STATUS_CHOICES)
    created = tables.Column(get_launch_time,
                            verbose_name=_("Time since created"),
                            filters=(filters.parse_isotime,
                                     filters.timesince_sortable),
                            attrs={'data-type': 'timesince'})

    class Meta(object):
        name = "EC2"
        verbose_name = _("EC2 Instances")
        status_columns = ["status", ]
        row_class = UpdateRow
        table_actions_menu = (StartInstance, StopInstance)
        table_actions = (LaunchLinkNG, ImportInstanceLinkNG, DeleteInstance, InstancesFilterAction)
        row_actions = (StartInstance, StopInstance, RebootInstance, DeleteInstance)
