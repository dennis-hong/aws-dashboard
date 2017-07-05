/*
 *    (c) Copyright 2015 Hewlett-Packard Development Company, L.P.
 *
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
(function () {
  'use strict';

  angular
    .module('horizon.dashboard.aws.workflow.export-instance', [])
    .config(config)
    .constant('horizon.dashboard.aws.workflow.export-instance.modal-spec', {
      backdrop: 'static',
      size: 'lg',
      controller: 'ModalContainerController',
      template: '<wizard class="wizard" ng-controller="ExportInstanceWizardController"></wizard>'
    })

    /**
     * @name horizon.dashboard.aws.workflow.export-instance.boot-source-types
     * @description Boot source types
     */
    .constant('horizon.dashboard.aws.workflow.export-instance.boot-source-types', {
      INSTANCE: 'instance',
      NON_BOOTABLE_IMAGE_TYPES: ['aki', 'ari']
    })
    .constant('horizon.dashboard.aws.workflow.export-instance.non_bootable_image_types',
      ['aki', 'ari'])

  config.$inject = [
    '$provide',
    '$windowProvider'
  ];

  /**
   * @name config
   * @param {Object} $provide
   * @param {Object} $windowProvider
   * @description Base path for the export-instance code
   * @returns {undefined} No return value
   */
  function config($provide, $windowProvider) {
    var path = $windowProvider.$get().STATIC_URL + 'dashboard/aws/ec2/workflow/export-instance/';
    $provide.constant('horizon.dashboard.aws.workflow.export-instance.basePath', path);
  }

})();
