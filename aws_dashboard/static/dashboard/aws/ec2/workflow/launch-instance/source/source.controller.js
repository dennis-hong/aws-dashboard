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
   * @name LaunchEC2InstanceSourceController
   * @description
   * The `LaunchEC2InstanceSourceController` controller provides functions for
   * configuring the source step of the Launch Instance Wizard.
   *
   */
  var push = [].push;

  angular
    .module('horizon.dashboard.aws.workflow.launch-instance')
    .controller('LaunchEC2InstanceSourceController', LaunchEC2InstanceSourceController);

  LaunchEC2InstanceSourceController.$inject = [
    '$scope',
    'horizon.dashboard.aws.workflow.launch-instance.boot-source-types',
    'dateFilter',
    'horizon.dashboard.aws.workflow.launch-instance.basePath',
    'horizon.framework.widgets.transfer-table.events',
    'horizon.framework.widgets.magic-search.events'
  ];

  function LaunchEC2InstanceSourceController($scope,
    bootSourceTypes,
    dateFilter,
    basePath,
    events,
    magicSearchEvents
  ) {

    var ctrl = this;

    // Error text for invalid fields
    /*eslint-disable max-len */
    ctrl.bootSourceTypeError = gettext('Volumes can only be attached to 1 active instance at a time. Please either set your instance count to 1 or select a different source type.');
    /*eslint-enable max-len */

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
      image: {
        available: $scope.model.images,
        allocated: selection,
        displayedAvailable: $scope.model.images,
        displayedAllocated: selection
      },
      snapshot: {
        available: $scope.model.imageSnapshots,
        allocated: selection,
        displayedAvailable: [],
        displayedAllocated: selection
      }
    };

    // Mapping for dynamic table headers
    var tableHeadCellsMap = {
      image: [
        { text: gettext('Name'), sortable: true, sortDefault: true },
        { text: gettext('CreationDate'), sortable: true },
        { text: gettext('ImageType'), sortable: true },
        { text: gettext('Architecture'), sortable: true }
      ],
      snapshot: [
        { text: gettext('Name'), sortable: true, sortDefault: true },
        { text: gettext('CreationDate'), sortable: true },
        { text: gettext('ImageType'), sortable: true },
        { text: gettext('Architecture'), sortable: true }
      ]
    };

    // Mapping for dynamic table data
    var tableBodyCellsMap = {
      image: [
        { key: 'name', classList: ['hi-light', 'word-break'] },
        { key: 'create_at', filter: dateFilter, filterArg: 'short' },
        { key: 'type' },
        { key: 'architecture' }
      ],
      snapshot: [
        { key: 'name', classList: ['hi-light', 'word-break'] },
        { key: 'create_at', filter: dateFilter, filterArg: 'short' },
        { key: 'type' },
        { key: 'architecture' }
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
      }
    };

    // Mapping for filter facets based on boot source type
    var sourceTypeFacets = {
      image: [
        facets.name
      ],
      snapshot: [
        facets.name
      ]
    };

    var newSpecWatcher = $scope.$watch(
      function () {
        return $scope.model.newInstanceSpec.instance_count;
      },
      function (newValue, oldValue) {
        if (newValue !== oldValue) {
          validateBootSourceType();
        }
      }
    );


    // Since available transfer table for Launch Instance Source step is
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

    var imagesWatcher = $scope.$watchCollection(
      function getImages() {
        return $scope.model.images;
      },
      function onImagesChange() {
        $scope.initPromise.then(function () {
          $scope.$applyAsync(function () {
            if ($scope.launchContext.imageId) {
              setSourceImageWithId($scope.launchContext.imageId);
            }
          });
        });
      }
    );

    var imageSnapshotsWatcher = $scope.$watchCollection(
      function getImageSnapshots() {
        return $scope.model.imageSnapshots;
      },
      function onImageSnapshotsChange() {
        $scope.initPromise.then(function () {
          $scope.$applyAsync(function () {
            if ($scope.launchContext.imageId) {
              setSourceImageSnapshotWithId($scope.launchContext.imageId);
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
      newSpecWatcher();
      bootSourceWatcher();
      imagesWatcher();
      imageSnapshotsWatcher();
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

    /*
     * Validation
     */

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

    function setSourceImageWithId(id) {
      var pre = findSourceById($scope.model.images, id);
      if (pre) {
        changeBootSource(bootSourceTypes.IMAGE, [pre]);
        $scope.model.newInstanceSpec.source_type = {
          type: bootSourceTypes.IMAGE,
          label: gettext('Image')
        };
        ctrl.currentBootSource = bootSourceTypes.IMAGE;
      }
    }

    function setSourceImageSnapshotWithId(id) {
      var pre = findSourceById($scope.model.imageSnapshots, id);
      if (pre) {
        changeBootSource(bootSourceTypes.INSTANCE_SNAPSHOT, [pre]);
        $scope.model.newInstanceSpec.source_type = {
          type: bootSourceTypes.INSTANCE_SNAPSHOT,
          label: gettext('Snapshot')
        };
        ctrl.currentBootSource = bootSourceTypes.INSTANCE_SNAPSHOT;
      }
    }

  }
})();
