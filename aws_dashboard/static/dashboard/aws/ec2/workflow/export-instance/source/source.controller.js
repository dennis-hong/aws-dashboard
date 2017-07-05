/*
 * Copyright 2015 IBM Corp.
 *
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

  /**
   * @ngdoc controller
   * @name ExportEC2InstanceSourceController
   * @description
   * The `ExportEC2InstanceSourceController` controller provides functions for
   * configuring the source step of the Export Instance Wizard.
   *
   */
  var push = [].push;

  angular
    .module('horizon.dashboard.aws.workflow.export-instance')
    .controller('ExportEC2InstanceSourceController', ExportEC2InstanceSourceController);

  ExportEC2InstanceSourceController.$inject = [
    '$scope',
    'horizon.dashboard.aws.workflow.export-instance.boot-source-types',
    'horizon.dashboard.aws.workflow.export-instance.basePath',
    'horizon.framework.widgets.transfer-table.events',
    'horizon.framework.widgets.magic-search.events'
  ];

  function ExportEC2InstanceSourceController($scope,
    bootSourceTypes,
    basePath,
    events,
    magicSearchEvents
  ) {

    var ctrl = this;

    // toggle button label/value defaults
    ctrl.toggleButtonOptions = [
      { label: gettext('Yes'), value: true },
      { label: gettext('No'), value: false }
    ];

    /*
     * Boot Sources
     */
    ctrl.updateBootSourceSelection = updateBootSourceSelection;
    var selection = ctrl.selection = $scope.model.newInstanceSpec.source;

    /*
     * Transfer table
     */
    ctrl.tableHeadCells = [];
    ctrl.tableBodyCells = [];
    ctrl.tableData = {
      available: [],
      allocated: selection,
      displayedAvailable: [],
      displayedAllocated: []
    };
    ctrl.helpText = {};
    ctrl.sourceDetails = basePath + 'source/source-details.html';

    var bootSources = {
      instance: {
        available: $scope.model.instances,
        allocated: selection,
        displayedAvailable: [],
        displayedAllocated: selection
      }
    };

    // Mapping for dynamic table headers
    var tableHeadCellsMap = {
      instance: [
        { text: gettext('Name'), sortable: true, sortDefault: true },
        { text: gettext('Instance Type'), sortable: true },
        { text: gettext('Image ID'), sortable: true },
        { text: gettext('State'), sortable: true }
      ]
    };

    // Mapping for dynamic table data
    var tableBodyCellsMap = {
      instance: [
        { key: 'name', classList: ['hi-light', 'word-break'] },
        { key: 'instance_type' },
        { key: 'image_id' },
        { key: 'status' }
      ]
    };

    /**
     * Filtering - client-side MagicSearch
     */
    ctrl.sourceFacets = [];

    // All facets for source step
    var facets = {
      name: {
        label: gettext('Name'),
        name: 'name',
        singleton: true
      },
      instance_type: {
        label: gettext('Instance Type'),
        name: 'instance_type',
        singleton: true
      },
      image_id: {
        label: gettext('Image Id'),
        name: 'image_id',
        singleton: true
      },
      type: {
        label: gettext('Status'),
        name: 'status',
        singleton: true,
        options: [
          { label: gettext('Running'), key: 'running' },
          { label: gettext('Creating'), key: 'creating' },
          { label: gettext('Terminated'), key: 'terminated' },
          { label: gettext('Error'), key: 'error' },
          { label: gettext('Error Deleting'), key: 'error_deleting' }
        ]
      }
    };

    // Mapping for filter facets based on boot source type
    var sourceTypeFacets = {
      instance: [
        facets.name, facets.instance_type, facets.image_id, facets.type
      ]
    };

    var allocatedWatcher = $scope.$watch(
      function () {
        return ctrl.tableData.allocated.length;
      }
    );

    // Since available transfer table for Export Instance Source step is
    // dynamically selected based on Boot Source, we need to update the
    // model here accordingly. Otherwise it will only calculate the items
    // available based on the original selection Boot Source: Image.
    var bootSourceWatcher = $scope.$watch(
      function getBootSource() {
        return ctrl.currentBootSource;
      },
      function onBootSourceChange(newValue, oldValue) {
        if (newValue !== oldValue) {
          $scope.$broadcast(events.AVAIL_CHANGED, {
            'data': bootSources[newValue]
          });
        }
      }
    );

    var instancesWatcher = $scope.$watchCollection(
      function getInstances() {
        return $scope.model.instances;
      },
      function onInstancesChange() {
        $scope.initPromise.then(function () {
          $scope.$applyAsync(function () {
            if ($scope.launchContext.instanceId) {
              setSourceInstanceWithId($scope.launchContext.instanceId);
            }
          });
        });
      }
    );


    // When the allowedboot list changes, change the source_type
    // and update the table for the new source selection. Only done
    // with the first item for the list
    var allowedBootSourcesWatcher = $scope.$watchCollection(
      function getAllowedBootSources() {
        return $scope.model.allowedBootSources;
      },
      function changeBootSource(newValue) {
        if (angular.isArray(newValue) && newValue.length > 0 &&
          !$scope.model.newInstanceSpec.source_type) {
          updateBootSourceSelection(newValue[0].type);
          $scope.model.newInstanceSpec.source_type = newValue[0];
        }
      }
    );

    // Explicitly remove watchers on destruction of this controller
    $scope.$on('$destroy', function() {
      allowedBootSourcesWatcher();
      allocatedWatcher();
      bootSourceWatcher();
      instancesWatcher();
    });

    ////////////////////

    function updateBootSourceSelection(selectedSource) {
      ctrl.currentBootSource = selectedSource;

      changeBootSource(selectedSource);
    }

    // Dynamically update page based on boot source selection
    function changeBootSource(key, preSelection) {
      updateDataSource(key, preSelection);
      updateHelpText(key);
      updateTableHeadCells(key);
      updateTableBodyCells(key);
      updateFacets(key);
    }

    function updateDataSource(key, preSelection) {
      selection.length = 0;
      if (preSelection) {
        push.apply(selection, preSelection);
      }
      angular.extend(ctrl.tableData, bootSources[key]);
    }

    function updateHelpText() {
      angular.extend(ctrl.helpText, {
        noneAllocText: gettext('Select a source from those listed below.'),
        availHelpText: gettext('Select one'),
        /*eslint-disable max-len */
        volumeAZHelpText: gettext('When selecting volume as boot source, please ensure the instance\'s availability zone is compatible with your volume\'s availability zone.')
        /*eslint-enable max-len */
      });
    }

    function updateTableHeadCells(key) {
      refillArray(ctrl.tableHeadCells, tableHeadCellsMap[key]);
    }

    function updateTableBodyCells(key) {
      refillArray(ctrl.tableBodyCells, tableBodyCellsMap[key]);
    }

    function updateFacets(key) {
      refillArray(ctrl.sourceFacets, sourceTypeFacets[key]);
      $scope.$broadcast(magicSearchEvents.FACETS_CHANGED);
    }

    function refillArray(arrayToRefill, contentArray) {
      arrayToRefill.length = 0;
      Array.prototype.push.apply(arrayToRefill, contentArray);
    }

    function findSourceById(sources, id) {
      var len = sources.length;
      var source;
      for (var i = 0; i < len; i++) {
        source = sources[i];
        if (source.id === id) {
          return source;
        }
      }
    }

    function setSourceInstanceWithId(id) {
      var pre = findSourceById($scope.model.instances, id);
      if (pre) {
        changeBootSource(bootSourceTypes.INSTANCE, [pre]);
        $scope.model.newInstanceSpec.source_type = {
          type: bootSourceTypes.INSTANCE,
          label: gettext('Instance')
        };
        ctrl.currentBootSource = bootSourceTypes.INSTANCE;
      }
    }

  }
})();