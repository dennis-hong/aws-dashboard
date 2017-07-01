/*
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
(function () {
  'use strict';

  angular
    .module('horizon.dashboard.aws.workflow.import-instance')
    .controller('ImportEC2InstanceSecurityGroupsController', ImportEC2InstanceSecurityGroupsController);

  ImportEC2InstanceSecurityGroupsController.$inject = [
    'importEC2InstanceModel',
    'horizon.dashboard.aws.workflow.import-instance.basePath'
  ];

  /**
   * @ngdoc controller
   * @name ImportEC2InstanceSecurityGroupsController
   * @param {Object} importEC2InstanceModel
   * @param {string} basePath
   * @description
   * Allows selection of security groups.
   * @returns {undefined} No return value
   */
  function ImportEC2InstanceSecurityGroupsController(importEC2InstanceModel, basePath) {
    var ctrl = this;

    ctrl.tableData = {
      available: importEC2InstanceModel.securityGroups,
      allocated: importEC2InstanceModel.newInstanceSpec.security_groups,
      displayedAvailable: [],
      displayedAllocated: []
    };

    ctrl.tableDetails = basePath + 'security-groups/security-group-details.html';

    ctrl.tableHelp = {
      /*eslint-disable max-len */
      noneAllocText: gettext('Select one or more security groups from the available groups below.'),
      /*eslint-enable max-len */
      availHelpText: gettext('Select one or more')
    };

    ctrl.tableLimits = {
      maxAllocation: -1
    };

    ctrl.filterFacets = [
      {
        label: gettext('GroupName'),
        name: 'GroupName',
        singleton: true
      },
      {
        label: gettext('Description'),
        name: 'Description',
        singleton: true
      }
    ];
  }
})();
