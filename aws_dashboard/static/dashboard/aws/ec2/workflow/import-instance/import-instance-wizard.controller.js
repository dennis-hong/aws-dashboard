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
    .controller('ImportEC2InstanceWizardController', ImportEC2InstanceWizardController);

  ImportEC2InstanceWizardController.$inject = [
    '$scope',
    'importEC2InstanceModel',
    'horizon.dashboard.aws.workflow.import-instance.workflow'
  ];

  function ImportEC2InstanceWizardController($scope, importEC2InstanceModel, importInstanceWorkflow) {
    // Note: we set these attributes on the $scope so that the scope inheritance used all
    // through the import instance wizard continues to work.
    $scope.workflow = importInstanceWorkflow;     // eslint-disable-line angular/controller-as
    $scope.model = importEC2InstanceModel;           // eslint-disable-line angular/controller-as
    $scope.model.initialize(true);
    $scope.submit = $scope.model.importInstance;  // eslint-disable-line angular/controller-as
  }

})();
