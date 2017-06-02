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
from dateutil import parser

from django.conf import settings
from django.core import urlresolvers
from django.http import HttpResponse  # noqa
from django import shortcuts
from django import template
from django.template.defaultfilters import title  # noqa
from django.utils.http import urlencode
from django.utils.translation import npgettext_lazy
from django.utils.translation import pgettext_lazy
from django.utils.translation import string_concat  # noqa
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon.utils import filters

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.access_and_security.floating_ips \
    import workflows
from openstack_dashboard.dashboards.project.instances import tabs
from openstack_dashboard.dashboards.project.instances.workflows \
    import resize_instance
from openstack_dashboard.dashboards.project.instances.workflows \
    import update_instance
from openstack_dashboard import policy

from aws_dashboard.api import ec2


LOG = logging.getLogger(__name__)

ACTIVE_STATES = ("Running",)
VOLUME_ATTACH_READY_STATES = ("Running", "SHUTOFF")
SNAPSHOT_READY_STATES = ("Running", "SHUTOFF", "PAUSED", "SUSPENDED")

POWER_STATES = {
    0: "NO STATE",
    1: "RUNNING",
    2: "BLOCKED",
    3: "PAUSED",
    4: "SHUTDOWN",
    5: "SHUTOFF",
    6: "CRASHED",
    7: "SUSPENDED",
    8: "FAILED",
    9: "BUILDING",
}

PAUSE = 0
UNPAUSE = 1
SUSPEND = 0
RESUME = 1
SHELVE = 0
UNSHELVE = 1


def is_deleting(instance):
    task_state = getattr(instance, "OS-EXT-STS:task_state", None)
    if not task_state:
        return False
    return task_state.lower() == "deleting"


class DeleteInstance(policy.PolicyTargetMixin, tables.DeleteAction):
    policy_rules = (("compute", "compute:delete"),)
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


class RebootInstance(policy.PolicyTargetMixin, tables.BatchAction):
    name = "reboot"
    classes = ('btn-reboot',)
    policy_rules = (("compute", "compute:reboot"),)
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
            return ((instance.status in ACTIVE_STATES
                     or instance.status == 'SHUTOFF')
                    and not is_deleting(instance))
        else:
            return True

    def action(self, request, obj_id):
        api.nova.server_reboot(request, obj_id, soft_reboot=False)


class SoftRebootInstance(RebootInstance):
    name = "soft_reboot"

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Soft Reboot Instance",
            u"Soft Reboot Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Soft Rebooted Instance",
            u"Soft Rebooted Instances",
            count
        )

    def action(self, request, obj_id):
        api.nova.server_reboot(request, obj_id, soft_reboot=True)


class TogglePause(tables.BatchAction):
    name = "pause"
    icon = "pause"

    @staticmethod
    def action_present(count):
        return (
            ungettext_lazy(
                u"Pause Instance",
                u"Pause Instances",
                count
            ),
            ungettext_lazy(
                u"Resume Instance",
                u"Resume Instances",
                count
            ),
        )

    @staticmethod
    def action_past(count):
        return (
            ungettext_lazy(
                u"Paused Instance",
                u"Paused Instances",
                count
            ),
            ungettext_lazy(
                u"Resumed Instance",
                u"Resumed Instances",
                count
            ),
        )

    def allowed(self, request, instance=None):
        if not api.nova.extension_supported('AdminActions',
                                            request):
            return False
        if not instance:
            return False
        self.paused = instance.status == "PAUSED"
        if self.paused:
            self.current_present_action = UNPAUSE
            policy_rules = (
                ("compute", "compute_extension:admin_actions:unpause"),)
        else:
            self.current_present_action = PAUSE
            policy_rules = (
                ("compute", "compute_extension:admin_actions:pause"),)

        has_permission = policy.check(
            policy_rules, request,
            target={'project_id': getattr(instance, 'tenant_id', None)})

        return (has_permission
                and (instance.status in ACTIVE_STATES or self.paused)
                and not is_deleting(instance))

    def action(self, request, obj_id):
        if self.paused:
            api.nova.server_unpause(request, obj_id)
            self.current_past_action = UNPAUSE
        else:
            api.nova.server_pause(request, obj_id)
            self.current_past_action = PAUSE


class ToggleSuspend(tables.BatchAction):
    name = "suspend"
    classes = ("btn-suspend",)

    @staticmethod
    def action_present(count):
        return (
            ungettext_lazy(
                u"Suspend Instance",
                u"Suspend Instances",
                count
            ),
            ungettext_lazy(
                u"Resume Instance",
                u"Resume Instances",
                count
            ),
        )

    @staticmethod
    def action_past(count):
        return (
            ungettext_lazy(
                u"Suspended Instance",
                u"Suspended Instances",
                count
            ),
            ungettext_lazy(
                u"Resumed Instance",
                u"Resumed Instances",
                count
            ),
        )

    def allowed(self, request, instance=None):
        if not api.nova.extension_supported('AdminActions',
                                            request):
            return False
        if not instance:
            return False
        self.suspended = instance.status == "SUSPENDED"
        if self.suspended:
            self.current_present_action = RESUME
            policy_rules = (
                ("compute", "compute_extension:admin_actions:resume"),)
        else:
            self.current_present_action = SUSPEND
            policy_rules = (
                ("compute", "compute_extension:admin_actions:suspend"),)

        has_permission = policy.check(
            policy_rules, request,
            target={'project_id': getattr(instance, 'tenant_id', None)})

        return (has_permission
                and (instance.status in ACTIVE_STATES or self.suspended)
                and not is_deleting(instance))

    def action(self, request, obj_id):
        if self.suspended:
            api.nova.server_resume(request, obj_id)
            self.current_past_action = RESUME
        else:
            api.nova.server_suspend(request, obj_id)
            self.current_past_action = SUSPEND


class ToggleShelve(tables.BatchAction):
    name = "shelve"
    icon = "shelve"

    @staticmethod
    def action_present(count):
        return (
            ungettext_lazy(
                u"Shelve Instance",
                u"Shelve Instances",
                count
            ),
            ungettext_lazy(
                u"Unshelve Instance",
                u"Unshelve Instances",
                count
            ),
        )

    @staticmethod
    def action_past(count):
        return (
            ungettext_lazy(
                u"Shelved Instance",
                u"Shelved Instances",
                count
            ),
            ungettext_lazy(
                u"Unshelved Instance",
                u"Unshelved Instances",
                count
            ),
        )

    def allowed(self, request, instance=None):
        if not api.nova.extension_supported('Shelve', request):
            return False
        if not instance:
            return False
        self.shelved = instance.status == "SHELVED_OFFLOADED"
        if self.shelved:
            self.current_present_action = UNSHELVE
            policy_rules = (("compute", "compute_extension:unshelve"),)
        else:
            self.current_present_action = SHELVE
            policy_rules = (("compute", "compute_extension:shelve"),)

        has_permission = policy.check(
            policy_rules, request,
            target={'project_id': getattr(instance, 'tenant_id', None)})

        return (has_permission
                and (instance.status in ACTIVE_STATES or self.shelved)
                and not is_deleting(instance))

    def action(self, request, obj_id):
        if self.shelved:
            api.nova.server_unshelve(request, obj_id)
            self.current_past_action = UNSHELVE
        else:
            api.nova.server_shelve(request, obj_id)
            self.current_past_action = SHELVE


class LaunchLink(tables.LinkAction):
    name = "launch"
    verbose_name = _("Launch Instance")
    url = "horizon:aws:ec2:launch"
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"
    policy_rules = (("compute", "compute:create"),)
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


class EditInstance(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Instance")
    url = "horizon:project:instances:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("compute", "compute:update"),)

    def get_link_url(self, project):
        return self._get_link_url(project, 'instance_info')

    def _get_link_url(self, project, step_slug):
        base_url = urlresolvers.reverse(self.url, args=[project.id])
        next_url = self.table.get_full_url()
        params = {"step": step_slug,
                  update_instance.UpdateInstance.redirect_param_name: next_url}
        param = urlencode(params)
        return "?".join([base_url, param])

    def allowed(self, request, instance):
        return not is_deleting(instance)


class EditInstanceSecurityGroups(EditInstance):
    name = "edit_secgroups"
    verbose_name = _("Edit Security Groups")

    def get_link_url(self, project):
        return self._get_link_url(project, 'update_security_groups')

    def allowed(self, request, instance=None):
        return (instance.status in ACTIVE_STATES and
                not is_deleting(instance) and
                request.user.tenant_id == instance.tenant_id)


class CreateSnapshot(policy.PolicyTargetMixin, tables.LinkAction):
    name = "snapshot"
    verbose_name = _("Create Snapshot")
    url = "horizon:project:images:snapshots:create"
    classes = ("ajax-modal",)
    icon = "camera"
    policy_rules = (("compute", "compute:snapshot"),)

    def allowed(self, request, instance=None):
        return instance.status in SNAPSHOT_READY_STATES \
            and not is_deleting(instance)


class ConsoleLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "console"
    verbose_name = _("Console")
    url = "horizon:project:instances:detail"
    classes = ("btn-console",)
    policy_rules = (("compute", "compute_extension:consoles"),)

    def allowed(self, request, instance=None):
        # We check if ConsoleLink is allowed only if settings.CONSOLE_TYPE is
        # not set at all, or if it's set to any value other than None or False.
        return bool(getattr(settings, 'CONSOLE_TYPE', True)) and \
            instance.status in ACTIVE_STATES and not is_deleting(instance)

    def get_link_url(self, datum):
        base_url = super(ConsoleLink, self).get_link_url(datum)
        tab_query_string = tabs.ConsoleTab(
            tabs.InstanceDetailTabs).get_query_string()
        return "?".join([base_url, tab_query_string])


class LogLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "log"
    verbose_name = _("View Log")
    url = "horizon:project:instances:detail"
    classes = ("btn-log",)
    policy_rules = (("compute", "compute_extension:console_output"),)

    def allowed(self, request, instance=None):
        return instance.status in ACTIVE_STATES and not is_deleting(instance)

    def get_link_url(self, datum):
        base_url = super(LogLink, self).get_link_url(datum)
        tab_query_string = tabs.LogTab(
            tabs.InstanceDetailTabs).get_query_string()
        return "?".join([base_url, tab_query_string])


class ResizeLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "resize"
    verbose_name = _("Resize Instance")
    url = "horizon:project:instances:resize"
    classes = ("ajax-modal", "btn-resize")
    policy_rules = (("compute", "compute:resize"),)

    def get_link_url(self, project):
        return self._get_link_url(project, 'flavor_choice')

    def _get_link_url(self, project, step_slug):
        base_url = urlresolvers.reverse(self.url, args=[project.id])
        next_url = self.table.get_full_url()
        params = {"step": step_slug,
                  resize_instance.ResizeInstance.redirect_param_name: next_url}
        param = urlencode(params)
        return "?".join([base_url, param])

    def allowed(self, request, instance):
        return ((instance.status in ACTIVE_STATES
                 or instance.status == 'SHUTOFF')
                and not is_deleting(instance))


class ConfirmResize(policy.PolicyTargetMixin, tables.Action):
    name = "confirm"
    verbose_name = _("Confirm Resize/Migrate")
    classes = ("btn-confirm", "btn-action-required")
    policy_rules = (("compute", "compute:confirm_resize"),)

    def allowed(self, request, instance):
        return instance.status == 'VERIFY_RESIZE'

    def single(self, table, request, instance):
        api.nova.server_confirm_resize(request, instance)


class RevertResize(policy.PolicyTargetMixin, tables.Action):
    name = "revert"
    verbose_name = _("Revert Resize/Migrate")
    classes = ("btn-revert", "btn-action-required")
    policy_rules = (("compute", "compute:revert_resize"),)

    def allowed(self, request, instance):
        return instance.status == 'VERIFY_RESIZE'

    def single(self, table, request, instance):
        api.nova.server_revert_resize(request, instance)


class RebuildInstance(policy.PolicyTargetMixin, tables.LinkAction):
    name = "rebuild"
    verbose_name = _("Rebuild Instance")
    classes = ("btn-rebuild", "ajax-modal")
    url = "horizon:project:instances:rebuild"
    policy_rules = (("compute", "compute:rebuild"),)

    def allowed(self, request, instance):
        return ((instance.status in ACTIVE_STATES
                 or instance.status == 'SHUTOFF')
                and not is_deleting(instance))

    def get_link_url(self, datum):
        instance_id = self.table.get_object_id(datum)
        return urlresolvers.reverse(self.url, args=[instance_id])


class AssociateIP(policy.PolicyTargetMixin, tables.LinkAction):
    name = "associate"
    verbose_name = _("Associate Floating IP")
    url = "horizon:project:access_and_security:floating_ips:associate"
    classes = ("ajax-modal",)
    icon = "link"
    policy_rules = (("compute", "network:associate_floating_ip"),)

    def allowed(self, request, instance):
        return True

    def get_link_url(self, datum):
        base_url = urlresolvers.reverse(self.url)
        next_url = self.table.get_full_url()
        params = {
            "instance_id": self.table.get_object_id(datum),
            workflows.IPAssociationWorkflow.redirect_param_name: next_url}
        params = urlencode(params)
        return "?".join([base_url, params])


class SimpleAssociateIP(policy.PolicyTargetMixin, tables.Action):
    name = "associate-simple"
    verbose_name = _("Associate Floating IP")
    icon = "link"
    policy_rules = (("compute", "network:associate_floating_ip"),)

    def allowed(self, request, instance):
        if not api.network.floating_ip_simple_associate_supported(request):
            return False
        if instance.status == "ERROR":
            return False
        return not is_deleting(instance)

    def single(self, table, request, instance_id):
        try:
            # target_id is port_id for Neutron and instance_id for Nova Network
            # (Neutron API wrapper returns a 'portid_fixedip' string)
            target_id = api.network.floating_ip_target_get_by_instance(
                request, instance_id).split('_')[0]

            fip = api.network.tenant_floating_ip_allocate(request)
            api.network.floating_ip_associate(request, fip.id, target_id)
            messages.success(request,
                             _("Successfully associated floating IP: %s")
                             % fip.ip)
        except Exception:
            exceptions.handle(request,
                              _("Unable to associate floating IP."))
        return shortcuts.redirect(request.get_full_path())


class SimpleDisassociateIP(policy.PolicyTargetMixin, tables.Action):
    name = "disassociate"
    verbose_name = _("Disassociate Floating IP")
    classes = ("btn-disassociate",)
    policy_rules = (("compute", "network:disassociate_floating_ip"),)
    action_type = "danger"

    def allowed(self, request, instance):
        return False

    def single(self, table, request, instance_id):
        try:
            # target_id is port_id for Neutron and instance_id for Nova Network
            # (Neutron API wrapper returns a 'portid_fixedip' string)
            targets = api.network.floating_ip_target_list_by_instance(
                request, instance_id)

            target_ids = [t.split('_')[0] for t in targets]

            fips = [fip for fip in api.network.tenant_floating_ip_list(request)
                    if fip.port_id in target_ids]
            # Removing multiple floating IPs at once doesn't work, so this pops
            # off the first one.
            if fips:
                fip = fips.pop()
                api.network.floating_ip_disassociate(request, fip.id)
                messages.success(request,
                                 _("Successfully disassociated "
                                   "floating IP: %s") % fip.ip)
            else:
                messages.info(request, _("No floating IPs to disassociate."))
        except Exception:
            exceptions.handle(request,
                              _("Unable to disassociate floating IP."))
        return shortcuts.redirect(request.get_full_path())


class UpdateMetadata(policy.PolicyTargetMixin, tables.LinkAction):
    name = "update_metadata"
    verbose_name = _("Update Metadata")
    ajax = False
    icon = "pencil"
    attrs = {"ng-controller": "MetadataModalHelperController as modal"}
    policy_rules = (("compute", "compute:update_instance_metadata"),)

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        super(UpdateMetadata, self).__init__(attrs, **kwargs)

    def get_link_url(self, datum):
        instance_id = self.table.get_object_id(datum)
        self.attrs['ng-click'] = (
            "modal.openMetadataModal('instance', '%s', true, 'metadata')"
            % instance_id)
        return "javascript:void(0);"

    def allowed(self, request, instance=None):
        return (instance and
                instance.status.lower() != 'error')


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


class StartInstance(policy.PolicyTargetMixin, tables.BatchAction):
    name = "start"
    classes = ('btn-confirm',)
    policy_rules = (("compute", "compute:start"),)

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

    def allowed(self, request, instance):
        return ((instance is None) or
                (instance.status in ("SHUTDOWN", "SHUTOFF", "CRASHED")))

    def action(self, request, obj_id):
        api.nova.server_start(request, obj_id)


class StopInstance(policy.PolicyTargetMixin, tables.BatchAction):
    name = "stop"
    policy_rules = (("compute", "compute:stop"),)
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

    def allowed(self, request, instance):
        return ((instance is None)
                or ((get_power_state(instance) in ("RUNNING", "SUSPENDED"))
                    and not is_deleting(instance)))

    def action(self, request, obj_id):
        api.nova.server_stop(request, obj_id)


class LockInstance(policy.PolicyTargetMixin, tables.BatchAction):
    name = "lock"
    policy_rules = (("compute", "compute_extension:admin_actions:lock"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Lock Instance",
            u"Lock Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Locked Instance",
            u"Locked Instances",
            count
        )

    # to only allow unlocked instances to be locked
    def allowed(self, request, instance):
        # if not locked, lock should be available
        if getattr(instance, 'locked', False):
            return False
        if not api.nova.extension_supported('AdminActions', request):
            return False
        return True

    def action(self, request, obj_id):
        api.nova.server_lock(request, obj_id)


class UnlockInstance(policy.PolicyTargetMixin, tables.BatchAction):
    name = "unlock"
    policy_rules = (("compute", "compute_extension:admin_actions:unlock"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Unlock Instance",
            u"Unlock Instances",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Unlocked Instance",
            u"Unlocked Instances",
            count
        )

    # to only allow locked instances to be unlocked
    def allowed(self, request, instance):
        if not getattr(instance, 'locked', True):
            return False
        if not api.nova.extension_supported('AdminActions', request):
            return False
        return True

    def action(self, request, obj_id):
        api.nova.server_unlock(request, obj_id)


class AttachVolume(tables.LinkAction):
    name = "attach_volume"
    verbose_name = _("Attach Volume")
    url = "horizon:project:instances:attach_volume"
    classes = ("ajax-modal",)
    policy_rules = (("compute", "compute:attach_volume"),)

    # This action should be disabled if the instance
    # is not active, or the instance is being deleted
    def allowed(self, request, instance=None):
        return instance.status in ("Running") \
            and not is_deleting(instance)


class DetachVolume(AttachVolume):
    name = "detach_volume"
    verbose_name = _("Detach Volume")
    url = "horizon:project:instances:detach_volume"
    policy_rules = (("compute", "compute:detach_volume"),)

    # This action should be disabled if the instance
    # is not active, or the instance is being deleted
    def allowed(self, request, instance=None):
        return instance.status in ("Running") \
            and not is_deleting(instance)


def get_ips(instance):
    template_name = 'aws/ec2/_instance_ips.html'
    context = {
        "publicDnsName": getattr(instance, "PublicDnsName", ""),
        "publicIpAddress": getattr(instance, "PublicIpAddress", "")
    }
    return template.loader.render_to_string(template_name, context)


def get_power_state(instance):
    return POWER_STATES.get(getattr(instance, "OS-EXT-STS:power_state", 0), '')


def get_state(instance):
    return getattr(instance, "State", {}).get("Name")


def get_az(instance):
    return getattr(instance, "Placement", {}).get("AvailabilityZone")


def get_launch_time(instance):
    datetime = getattr(instance, "LaunchTime", {})
    return datetime.isoformat()


TASK_DISPLAY_NONE = pgettext_lazy("Task status of an Instance", u"None")

POWER_DISPLAY_CHOICES = (
    ("NO STATE", pgettext_lazy("Power state of an Instance", u"No State")),
    ("RUNNING", pgettext_lazy("Power state of an Instance", u"Running")),
    ("BLOCKED", pgettext_lazy("Power state of an Instance", u"Blocked")),
    ("PAUSED", pgettext_lazy("Power state of an Instance", u"Paused")),
    ("SHUTDOWN", pgettext_lazy("Power state of an Instance", u"Shut Down")),
    ("SHUTOFF", pgettext_lazy("Power state of an Instance", u"Shut Off")),
    ("CRASHED", pgettext_lazy("Power state of an Instance", u"Crashed")),
    ("SUSPENDED", pgettext_lazy("Power state of an Instance", u"Suspended")),
    ("FAILED", pgettext_lazy("Power state of an Instance", u"Failed")),
    ("BUILDING", pgettext_lazy("Power state of an Instance", u"Building")),
)

STATUS_CHOICES = (
    ("Running", True),
    ("Stopped", False),
    ("Error", False),
    ("Terminated", False),
)


class InstancesFilterAction(tables.FilterAction):
    filter_type = "server"
    filter_choices = (('name', _("Instance Name ="), True),
                      ('status', _("Status ="), True),
                      ('image', _("Image ID ="), True),
                      ('flavor', _("Flavor ID ="), True))


class Ec2InstanceTable(tables.DataTable):
    name = tables.WrappingColumn("name",
                                 link="horizon:project:instances:detail",
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
        table_actions_menu = (StartInstance, StopInstance, SoftRebootInstance)
        launch_actions = ()
        if getattr(settings, 'LAUNCH_INSTANCE_LEGACY_ENABLED', False):
            launch_actions = (LaunchLink,) + launch_actions
        if getattr(settings, 'LAUNCH_INSTANCE_NG_ENABLED', True):
            launch_actions = (LaunchLinkNG,) + launch_actions
        table_actions = launch_actions + (DeleteInstance, InstancesFilterAction)
        row_actions = (StartInstance, ConfirmResize, RevertResize,
                       CreateSnapshot, SimpleAssociateIP, AssociateIP,
                       SimpleDisassociateIP, EditInstance, AttachVolume,
                       DetachVolume, UpdateMetadata,
                       EditInstanceSecurityGroups, ConsoleLink, LogLink,
                       TogglePause, ToggleSuspend, ToggleShelve,
                       ResizeLink, LockInstance, UnlockInstance,
                       SoftRebootInstance, RebootInstance,
                       StopInstance, RebuildInstance, DeleteInstance)
