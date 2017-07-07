# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
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

"""
Views for managing images.
"""
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import tabs
from horizon.utils import memoized

from openstack_dashboard.utils import filters

from aws_dashboard.content.aws.images.images \
    import forms as project_forms
from aws_dashboard.content.aws.images.images \
    import tables as project_tables
from aws_dashboard.content.aws.images.images \
    import tabs as project_tabs
from aws_dashboard.api import ec2


class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateImageForm
    form_id = "update_image_form"
    modal_header = _("Edit Image")
    submit_label = _("Edit Image")
    submit_url = "horizon:aws:images:images:update"
    template_name = 'aws/images/images/update.html'
    success_url = reverse_lazy("horizon:aws:images:index")
    page_title = _("Edit Image")

    @memoized.memoized_method
    def get_object(self):
        try:
            return ec2.get_image(self.request, self.kwargs['image_id'])
        except Exception:
            msg = _('Unable to retrieve image.')
            url = reverse('horizon:aws:images:index')
            exceptions.handle(self.request, msg, redirect=url)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['image'] = self.get_object()
        args = (self.kwargs['image_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        image = self.get_object()
        properties = getattr(image, 'properties', {})
        data = {'image_id': self.kwargs['image_id'],
                'name': getattr(image, 'name', None) or image.id,
                'description': properties.get('description', ''),
                'kernel': properties.get('kernel_id', ''),
                'ramdisk': properties.get('ramdisk_id', ''),
                'architecture': properties.get('architecture', ''),
                'minimum_ram': getattr(image, 'min_ram', None),
                'minimum_disk': getattr(image, 'min_disk', None),
                'public': getattr(image, 'is_public', None),
                'protected': getattr(image, 'protected', None)}
        disk_format = getattr(image, 'disk_format', None)
        if (disk_format == 'raw' and
                getattr(image, 'container_format') == 'docker'):
            disk_format = 'docker'
        data['disk_format'] = disk_format
        return data


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.ImageDetailTabs
    template_name = 'horizon/common/_detail.html'
    page_title = "{{ image.name }}"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        image = self.get_data()
        table = project_tables.ImagesTable(self.request)
        context["image"] = image
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(image)
        choices = project_tables.ImagesTable.STATUS_DISPLAY_CHOICES
        image.status_label = filters.get_display_label(choices, image.status)
        return context

    @staticmethod
    def get_redirect_url():
        return reverse_lazy('horizon:aws:images:index')

    @memoized.memoized_method
    def get_data(self):
        try:
            return ec2.get_image(self.request, self.kwargs['image_id'])
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve image details.'),
                              redirect=self.get_redirect_url())

    def get_tabs(self, request, *args, **kwargs):
        image = self.get_data()
        return self.tab_group_class(request, image=image, **kwargs)
