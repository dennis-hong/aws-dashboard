# Copyright 2012 Nebula, Inc.
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

from collections import defaultdict

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon.utils.memoized import memoized  # noqa

from aws_dashboard.api import ec2

NOT_LAUNCHABLE_FORMATS = ['aki', 'ari']


class LaunchImage(tables.LinkAction):
    name = "launch_image"
    verbose_name = _("Launch Instance")
    url = "horizon:aws:ec2:launch"
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"
    policy_rules = (("compute", "compute:create"),)

    def get_link_url(self, datum):
        base_url = reverse(self.url)

        if get_image_type(datum) == "image":
            source_type = "image_id"
        else:
            source_type = "instance_snapshot_id"

        params = urlencode({"source_type": source_type,
                            "source_id": self.table.get_object_id(datum)})
        return "?".join([base_url, params])


class LaunchImageNG(LaunchImage):
    name = "launch_image_ng"
    verbose_name = _("Launch")
    url = "horizon:aws:images:index"
    classes = ("btn-launch", )
    ajax = False

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        super(LaunchImage, self).__init__(attrs, **kwargs)

    def get_link_url(self, datum):
        imageId = self.table.get_object_id(datum)
        url = reverse(self.url)
        ngclick = "modal.openLaunchEC2InstanceWizard(" \
            "{successUrl: '%s', source_type: 'image', source_id: '%s'})" % (url, imageId)
        self.attrs.update({
            "ng-controller": "LaunchEC2InstanceModalController as modal",
            "ng-click": ngclick
        })
        return "javascript:void(0);"


class DeleteImage(tables.DeleteAction):
    help_text = _("Deleted images are not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Image",
            u"Delete Images",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Image",
            u"Deleted Images",
            count
        )

    def delete(self, request, obj_id):
        ec2.delete_image(request, obj_id)


def filter_tenants():
    return getattr(settings, 'IMAGES_LIST_FILTER_TENANTS', [])


@memoized
def filter_tenant_ids():
    return [ft['tenant'] for ft in filter_tenants()]


def get_image_categories(im, user_tenant_id):
    categories = []
    if im.is_public:
        categories.append('public')
    if im.owner == user_tenant_id:
        categories.append('project')
    elif im.owner in filter_tenant_ids():
        categories.append(im.owner)
    elif not im.is_public:
        categories.append('shared')
        categories.append('other')
    return categories


def get_image_name(image):
    return getattr(image, "name", None) or image.id


def get_image_type(image):
    return getattr(image, "properties", {}).get("image_type", "image")


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, image_id):
        image = ec2.get_image(request, image_id)
        return image

    def load_cells(self, image=None):
        super(UpdateRow, self).load_cells(image)
        # Tag the row with the image category for client-side filtering.
        image = self.datum
        my_tenant_id = self.table.request.user.tenant_id
        image_categories = get_image_categories(image, my_tenant_id)
        for category in image_categories:
            self.classes.append('category-' + category)


class InstancesFilterAction(tables.FilterAction):
    filter_type = "query"
    filter_choices = (('name', _("Image Name ="), True),
                      ('status', _("Status ="), True),
                      ('id', _("Image ID ="), True))


class ImagesTable(tables.DataTable):
    STATUS_CHOICES = (
        ("available", True),
        ("pending", None),
        ("deregistered", False),
        ("deleted", False),
        ("failed", False),
        ("error", False),
        ("transient", False),
    )
    STATUS_DISPLAY_CHOICES = (
        ("available", pgettext_lazy("Current status of an Image", u"Available")),
        ("pending", pgettext_lazy("Current status of an Image", u"Pending")),
        ("deregistered", pgettext_lazy("Current status of an Image",
                                       u"Deregistered")),
        ("failed", pgettext_lazy("Current status of an Image", u"Failed")),
        ("error", pgettext_lazy("Current status of an Image", u"Error")),
        ("transient", pgettext_lazy("Current status of an Image", u"Transient")),
        ("deleted", pgettext_lazy("Current status of an Image", u"Deleted")),
        ("deactivated", pgettext_lazy("Current status of an Image",
                                      u"Deactivated")),
    )
    TYPE_CHOICES = (
        ("image", pgettext_lazy("Type of an image", u"Image")),
        ("snapshot", pgettext_lazy("Type of an image", u"Snapshot")),
    )
    name = tables.WrappingColumn(get_image_name,
                                 # TODO TBD
                                 # link="horizon:aws:images:images:detail",
                                 verbose_name=_("Image Name"),)
    image_id = tables.Column("id",
                             verbose_name=_("Image ID"))
    image_type = tables.Column(get_image_type,
                               verbose_name=_("Type"),
                               display_choices=TYPE_CHOICES)
    status = tables.Column("status",
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)
    public = tables.Column("is_public",
                           verbose_name=_("Public"),
                           empty_value=False,
                           filters=(filters.yesno, filters.capfirst))

    class Meta(object):
        name = "images"
        row_class = UpdateRow
        status_columns = ["status"]
        verbose_name = _("Images")
        table_actions = (InstancesFilterAction, DeleteImage,)
        launch_actions = (LaunchImageNG,)
        row_actions = launch_actions + (DeleteImage, )
