/*
 *    (c) Copyright 2015 Hewlett-Packard Development Company, L.P.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
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
    .module('horizon.dashboard.aws.workflow.launch-instance')
    .controller('LaunchEC2InstanceFlavorController', LaunchEC2InstanceFlavorController);

  LaunchEC2InstanceFlavorController.$inject = [
    '$scope',
    'horizon.framework.widgets.charts.quotaChartDefaults',
    'launchEC2InstanceModel'
  ];

  function LaunchEC2InstanceFlavorController($scope, quotaChartDefaults, launchEC2InstanceModel) {
    var ctrl = this;

    ctrl.defaultIfUndefined = defaultIfUndefined;
    ctrl.validateFlavor = validateFlavor;
    ctrl.buildFlavorFacades = buildFlavorFacades;
    ctrl.updateFlavorFacades = updateFlavorFacades;
    ctrl.getChartData = getChartData;
    ctrl.getErrors = getErrors;

    // Labels used by quota charts
    ctrl.chartTotalInstancesLabel = gettext('Total Instances');
    ctrl.chartTotalVcpusLabel = gettext('Total VCPUs');
    ctrl.chartTotalRamLabel = gettext('Total RAM');

    ctrl.filterFacets = [
      {
        label: gettext('Name'),
        name: 'InstanceType',
        singleton: true
      },
      {
        label: gettext('VCPUs'),
        name: 'vCPU',
        singleton: true
      },
      {
        label: gettext('RAM(GiB)'),
        name: 'Memory(GiB)',
        singleton: true
      },
      {
        label: gettext('Storage(GB)'),
        name: 'Storage(GB)',
        singleton: true
      }
    ];

    // Labels for error message on ram/disk validation
    ctrl.sourcesLabel = {
      image: gettext('image'),
      snapshot: gettext('snapshot')
    };

    /*
     * Flavor "facades" are used instead of just flavors because per-flavor
     * data needs to be associated with each flavor to support the quota chart
     * in the flavor details. A facade simply wraps an underlying data object,
     * exposing only the data needed by this specific view.
     */
    ctrl.availableFlavorFacades = [];
    ctrl.displayedAvailableFlavorFacades = [];
    ctrl.allocatedFlavorFacades = [];
    ctrl.displayedAllocatedFlavorFacades = [];

    // Convenience references to launch instance model elements
    ctrl.flavors = [];
    ctrl.metadataDefs = launchEC2InstanceModel.metadataDefs;
    ctrl.novaLimits = {};
    ctrl.instanceCount = 1;

    // Data that drives the transfer table for flavors
    ctrl.transferTableModel = {
      allocated:          ctrl.allocatedFlavorFacades,
      displayedAllocated: ctrl.displayedAllocatedFlavorFacades,
      available:          ctrl.availableFlavorFacades,
      displayedAvailable: ctrl.displayedAvailableFlavorFacades
    };

    // Each flavor has an instances chart...but it is the same for all flavors
    ctrl.instancesChartData = {};

    // We can pick at most, 1 flavor at a time
    ctrl.allocationLimits = {
      maxAllocation: 1
    };

    // Flavor facades and the new instance chart depend on nova limit data
    var novaLimitsWatcher = $scope.$watch(function () {
      return launchEC2InstanceModel.novaLimits;
    }, function (newValue, oldValue, scope) {
      var ctrl = scope.selectFlavorCtrl;
      ctrl.novaLimits = newValue;
      ctrl.updateFlavorFacades();
    }, true);

    // Flavor facades depend on flavors
    var flavorsWatcher = $scope.$watchCollection(function() {
      return launchEC2InstanceModel.flavors;
    }, function (newValue, oldValue, scope) {
      var ctrl = scope.selectFlavorCtrl;
      ctrl.flavors = newValue;
      ctrl.updateFlavorFacades();
    });

    // Flavor quota charts depend on the current instance count
    var instanceCountWatcher = $scope.$watch(function () {
      return launchEC2InstanceModel.newInstanceSpec.instance_count;
    }, function (newValue, oldValue, scope) {
      if (angular.isDefined(newValue)) {
        var ctrl = scope.selectFlavorCtrl;
        // Ignore any values <1
        ctrl.instanceCount = Math.max(1, newValue);
        ctrl.updateFlavorFacades();
        ctrl.validateFlavor();
      }
    });

    // Update the new instance model when the allocated flavor changes
    var facadesWatcher = $scope.$watchCollection(
      "selectFlavorCtrl.allocatedFlavorFacades",
      function (newValue, oldValue, scope) {
        if (newValue && newValue.length > 0) {
          launchEC2InstanceModel.newInstanceSpec.flavor = newValue[0].flavor;
          scope.selectFlavorCtrl.validateFlavor();
        } else {
          delete launchEC2InstanceModel.newInstanceSpec.flavor;
        }
      }
    );

    var sourceWatcher = $scope.$watchCollection(function() {
      return launchEC2InstanceModel.newInstanceSpec.source;
    }, function (newValue, oldValue, scope) {
      var ctrl = scope.selectFlavorCtrl;
      ctrl.source = newValue && newValue.length ? newValue[0] : null;
      ctrl.updateFlavorFacades();
      ctrl.validateFlavor();
    });

    //
    $scope.$on('$destroy', function() {
      novaLimitsWatcher();
      flavorsWatcher();
      instanceCountWatcher();
      facadesWatcher();
      sourceWatcher();
    });

    //////////

    // Convenience function to return a sensible value instead of undefined
    function defaultIfUndefined(value, defaultValue) {
      return angular.isUndefined(value) ? defaultValue : value;
    }

    /*
     * Validator for flavor selected. Checks if this flavor is
     * valid based on instance count and source selected.
     * If flavor is invalid, enabled is false.
     */
    function validateFlavor() {
      var allocatedFlavors = ctrl.allocatedFlavorFacades;
      if (allocatedFlavors && allocatedFlavors.length > 0) {
        var allocatedFlavorFacade = allocatedFlavors[0];
        var isValid = allocatedFlavorFacade.enabled;
        $scope.launchInstanceFlavorForm['allocated-flavor']
              .$setValidity('flavor', isValid);
      }
    }

    /*
     * Given flavor data, build facades that expose the specific attributes
     * needed by this view. These facades will be updated to include per-flavor
     * data, such as charts, as that per-flavor data is modified.
     */
    function buildFlavorFacades() {
      var facade, flavor;



      for (var i = 0; i < ctrl.flavors.length; i++) {
        flavor = ctrl.flavors[i];
        facade = {
          flavor:        flavor,
          id:            flavor.id,
          name:          flavor.InstanceType,
          vcpus:         flavor.vCPU,
          ram:           flavor.Memory,
          storage:       flavor.Storage,
          network:       flavor.NetworkingPerformance
        };
        ctrl.availableFlavorFacades.push(facade);
      }
    }

    /*
     * Some change in the underlying data requires we update our facades
     * primarily the per-flavor chart data.
     */
    function updateFlavorFacades() {
      if (ctrl.availableFlavorFacades.length !== ctrl.flavors.length) {
        // Build the facades to match the flavors
        ctrl.buildFlavorFacades();
      }

      // The instance chart is the same for all flavors, create it once
      var instancesChartData = ctrl.getChartData(
        ctrl.chartTotalInstancesLabel,
        ctrl.instanceCount,
        launchEC2InstanceModel.novaLimits.totalInstancesUsed,
        launchEC2InstanceModel.novaLimits.maxTotalInstances);

      /*
       * Each flavor has a different cpu and ram chart, create them here and
       * add that data to the flavor facade
       */
      for (var i = 0; i < ctrl.availableFlavorFacades.length; i++) {
        var facade = ctrl.availableFlavorFacades[i];

        facade.instancesChartData = instancesChartData;

        facade.vcpusChartData = ctrl.getChartData(
          ctrl.chartTotalVcpusLabel,
          ctrl.instanceCount * facade.vcpus,
          launchEC2InstanceModel.novaLimits.totalCoresUsed,
          launchEC2InstanceModel.novaLimits.maxTotalCores);

        facade.ramChartData = ctrl.getChartData(
          ctrl.chartTotalRamLabel,
          ctrl.instanceCount * facade.ram,
          launchEC2InstanceModel.novaLimits.totalRAMUsed,
          launchEC2InstanceModel.novaLimits.maxTotalRAMSize);

        var errors = ctrl.getErrors(facade.flavor);
        facade.errors = errors;
        facade.enabled = Object.keys(errors).length === 0;
      }
    }

    function getChartData(title, added, totalUsed, maxAllowed) {

      var used = ctrl.defaultIfUndefined(totalUsed, 0);
      var allowed = ctrl.defaultIfUndefined(maxAllowed, 1);
      var quotaCalc = Math.round((used + added) / allowed * 100);
      var overMax = quotaCalc > 100;

      var usageData = {
        label: quotaChartDefaults.usageLabel,
        value: used,
        colorClass: quotaChartDefaults.usageColorClass
      };
      var addedData = {
        label: quotaChartDefaults.addedLabel,
        value: added,
        colorClass: quotaChartDefaults.addedColorClass
      };
      var remainingData = {
        label: quotaChartDefaults.remainingLabel,
        value: Math.max(0, allowed - used - added),
        colorClass: quotaChartDefaults.remainingColorClass
      };
      var chartData = {
        title: title,
        maxLimit: allowed,
        label: quotaCalc + '%',
        overMax: overMax,
        data:  [usageData, addedData, remainingData]
      };

      return chartData;
    }

    // Generate error messages for flavor based on source (if selected) and instance count
    function getErrors(flavor) {
      var messages = {};
      var source = ctrl.source;
      var instanceCount = ctrl.instanceCount;

      // Check RAM resources
      var totalRamUsed = ctrl.defaultIfUndefined(
        ctrl.novaLimits.totalRAMUsed, 0);
      var maxTotalRam = ctrl.defaultIfUndefined(
        ctrl.novaLimits.maxTotalRAMSize, 0);
      var availableRam = maxTotalRam - totalRamUsed;
      var ramRequired = instanceCount * flavor.ram;
      if (ramRequired > availableRam) {
        /*eslint-disable max-len */
        messages.ram = gettext('This flavor requires more RAM than your quota allows. Please select a smaller flavor or decrease the instance count.');
        /*eslint-enable max-len */
      }

      // Check VCPU resources
      var totalCoresUsed = ctrl.defaultIfUndefined(
        ctrl.novaLimits.totalCoresUsed, 0);
      var maxTotalCores = ctrl.defaultIfUndefined(
        ctrl.novaLimits.maxTotalCores, 0);
      var availableCores = maxTotalCores - totalCoresUsed;
      var coresRequired = instanceCount * flavor.vcpus;
      if (coresRequired > availableCores) {
        /*eslint-disable max-len */
        messages.vcpus = gettext('This flavor requires more VCPUs than your quota allows. Please select a smaller flavor or decrease the instance count.');
        /*eslint-enable max-len */
      }

      // Check source minimum requirements against this flavor
      var sourceType = launchEC2InstanceModel.newInstanceSpec.source_type;
      if (source && sourceType &&
        (sourceType.type === 'image' || sourceType.type === 'snapshot')) {
        if (source.min_disk > 0 && source.min_disk > flavor.disk) {
          /*eslint-disable max-len */
          var srcMinDiskMsg = gettext('The selected %(sourceType)s source requires a flavor with at least %(minDisk)s GB of root disk. Select a flavor with a larger root disk or use a different %(sourceType)s source.');
          /*eslint-enable max-len */
          messages.disk = interpolate(
            srcMinDiskMsg,
            {
              minDisk: source.min_disk,
              sourceType: ctrl.sourcesLabel[sourceType.type]
            },
            true
          );
        }
        if (source.min_ram > 0 && source.min_ram > flavor.ram) {
          /*eslint-disable max-len */
          var srcMinRamMsg = gettext('The selected %(sourceType)s source requires a flavor with at least %(minRam)s MB of RAM. Select a flavor with more RAM or use a different %(sourceType)s source.');
          /*eslint-enable max-len */
          messages.ram = interpolate(
            srcMinRamMsg,
            {
              minRam: source.min_ram,
              sourceType: ctrl.sourcesLabel[sourceType.type]
            },
            true
          );
        }
      }

      return messages;
    }
  }
})();
