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
    .module('horizon.dashboard.aws.workflow.import-instance')
    .factory('horizon.dashboard.aws.workflow.import-instance.workflow', importInstanceWorkflow);

  importInstanceWorkflow.$inject = [
    'horizon.dashboard.aws.workflow.import-instance.basePath',
    'horizon.app.core.workflow.factory'
  ];

  function importInstanceWorkflow(basePath, dashboardWorkflow) {
    return dashboardWorkflow({
      title: gettext('Import Instance'),

      steps: [
        {
          id: 'source',
          title: gettext('Source'),
          templateUrl: basePath + 'source/source.html',
          helpUrl: basePath + 'source/source.help.html',
          formName: 'importInstanceSourceForm'
        },
        {
          id: 'flavor',
          title: gettext('Flavor'),
          templateUrl: basePath + 'flavor/flavor.html',
          helpUrl: basePath + 'flavor/flavor.help.html',
          formName: 'importInstanceFlavorForm'
        },
        {
          id: 'secgroups',
          title: gettext('Security Groups'),
          templateUrl: basePath + 'security-groups/security-groups.html',
          helpUrl: basePath + 'security-groups/security-groups.help.html',
          formName: 'importInstanceAccessAndSecurityForm'
        },
        {
          id: 'keypair',
          title: gettext('Key Pair'),
          templateUrl: basePath + 'keypair/keypair.html',
          helpUrl: basePath + 'keypair/keypair.help.html',
          formName: 'importInstanceKeypairForm'
        }
      ],

      btnText: {
        finish: gettext('Import Instance')
      },

      btnIcon: {
        finish: 'fa-cloud-download'
      }
    });
  }

})();
