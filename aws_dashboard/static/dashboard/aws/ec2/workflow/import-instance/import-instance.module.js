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
    .module('horizon.dashboard.aws.workflow.import-instance', [])
    .config(config)
    .constant('horizon.dashboard.aws.workflow.import-instance.modal-spec', {
      backdrop: 'static',
      size: 'lg',
      controller: 'ModalContainerController',
      template: '<wizard class="wizard" ng-controller="ImportEC2InstanceWizardController"></wizard>'
    })

    /**
     * @name horizon.dashboard.aws.workflow.import-instance.boot-source-types
     * @description Boot source types
     */
    .constant('horizon.dashboard.aws.workflow.import-instance.boot-source-types', {
      INSTANCE: 'instance',
      IMAGE: 'image',
      SNAPSHOT: 'snapshot'
    });

  config.$inject = [
    '$provide',
    '$windowProvider'
  ];

  /**
   * @name config
   * @param {Object} $provide
   * @param {Object} $windowProvider
   * @description Base path for the import-instance code
   * @returns {undefined} No return value
   */
  function config($provide, $windowProvider) {
    var path = $windowProvider.$get().STATIC_URL + 'dashboard/aws/ec2/workflow/import-instance/';
    $provide.constant('horizon.dashboard.aws.workflow.import-instance.basePath', path);
  }

})();
