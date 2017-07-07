(function () {
  'use strict';

  var push = Array.prototype.push;
  var noop = angular.noop;

  /**
   * @ngdoc overview
   * @name horizon.dashboard.aws.workflow.import-instance
   *
   * @description
   * Manage workflow of creating server.
   */

  angular
    .module('horizon.dashboard.aws.workflow.import-instance')
    .factory('importEC2InstanceModel', importEC2InstanceModel);

  importEC2InstanceModel.$inject = [
    '$q',
    '$log',
    'horizon.app.core.openstack-service-api.nova',
    'horizon.dashboard.aws.workflow.import-instance.boot-source-types',
    'horizon.framework.widgets.toast.service',
    'horizon.dashboard.aws.aws-service-api.ec2'
  ];

  /**
   * @ngdoc service
   * @name importEC2InstanceModel
   *
   * @param {Object} $q
   * @param {Object} $log
   * @param {Object} novaAPI
   * @param {Object} bootSourceTypes
   * @param {Object} toast
   * @param {Object} ec2API
   * @description
   * This is the M part in MVC design pattern for import instance
   * wizard workflow. It is responsible for providing data to the
   * view of each step in import instance workflow and collecting
   * user's input from view for  creation of new instance.  It is
   * also the center point of communication between import instance
   * UI and services API.
   * @returns {Object} The model
   */
  function importEC2InstanceModel(
    $q,
    $log,
    novaAPI,
    bootSourceTypes,
    toast,
    ec2API
  ) {

    var initPromise;

    /**
     * @ngdoc model api object
     */
    var model = {

      initializing: false,
      initialized: false,

      /*eslint-disable max-len */
      /**
       * @name newInstanceSpec
       *
       * @description
       * A dictionary like object containing specification collected from user's
       * input.  Its required properties include:
       *
       * @property {String} name: The new server name.
       * @property {String} source_type: The type of source
       *   Valid options: (image | snapshot | volume | volume_snapshot)
       * @property {String} source_id: The ID of the image / volume to use.
       * @property {String} flavor_id: The ID of the flavor to use.
       *
       * Other parameters are accepted as per the underlying novaclient:
       *  - https://github.com/openstack/python-novaclient/blob/master/novaclient/v2/servers.py#L417
       * But may be required additional values as per nova:
       *  - https://github.com/openstack/horizon/blob/master/openstack_dashboard/api/rest/nova.py#L127
       *
       * The JS code only needs to set the values below as they are made.
       * The createInstance function will map them appropriately.
       */
      /*eslint-enable max-len */

      // see initializeNewInstanceSpec
      newInstanceSpec: {},

      /**
       * cloud service properties, they should be READ-ONLY to all UI controllers
       */

      instances: [],
      regions: [],
      availabilityZones: [],
      flavors: [],
      allowedBootSources: [],
      images: [],
      imageSnapshots: [],
      keypairs: [],
      leave_original_instance: true,
      leave_instance_snapshot: false,
      novaLimits: {},
      profiles: [],
      securityGroups: [],
      metadataTree: null,

      /**
       * api methods for UI controllers
       */

      initialize: initialize,
      importInstance: importInstance
    };

    // Local function.
    function initializeNewInstanceSpec() {

      model.newInstanceSpec = {
        instance_id: null,
        region: null,
        availability_zone: null,
        // REQUIRED
        flavor: null,
        instance_count: 1,
        // REQUIRED Server Key
        key_pair: [],
        // REQUIRED
        name: null,
        // REQUIRED Server Key. May be empty.
        security_groups: [],
        // REQUIRED for JS logic (instance | image | snapshot)
        source_type: null,
        source: [],
        vol_device_name: 'vda',
        leave_original_instance: true,
        leave_instance_snapshot: false
      };
    }

    /**
     * @ngdoc method
     * @name importEC2InstanceModel.initialize
     * @returns {promise}
     *
     * @description
     * Send request to get all data to initialize the model.
     */

    function initialize(deep) {
      var deferred, promise;

      // Each time opening import instance wizard, we need to do this, or
      // we can call the whole methods `reset` instead of `initialize`.
      initializeNewInstanceSpec();

      if (model.initializing) {
        promise = initPromise;

      } else if (model.initialized && !deep) {
        deferred = $q.defer();
        promise = deferred.promise;
        deferred.resolve();

      } else {
        model.initializing = true;

        model.allowedBootSources.length = 0;

        promise = $q.all([
          novaAPI.getServers().then(onGetInstances, noop),
          ec2API.getRegions().then(onGetRegions, noop),
          ec2API.getAvailabilityZones().then(onGetAvailabilityZones, noop),
          ec2API.getFlavors().then(onGetFlavors, noop),
          ec2API.getKeypairs().then(onGetKeypairs, noop),
          novaAPI.getLimits(true).then(onGetNovaLimits, noop),
          ec2API.getSecurityGroups().then(onGetSecurityGroups, noop),
        ]);

        promise.then(onInitSuccess, onInitFail);
      }

      return promise;
    }

    function onInitSuccess() {
      model.initializing = false;
      model.initialized = true;
    }

    function onInitFail() {
      model.initializing = false;
      model.initialized = false;
    }


    /**
     * @ngdoc method
     * @name importEC2InstanceModel.importInstance
     * @returns {promise}
     *
     * @description
     * Send request for importing server.
     */

    function importInstance() {
      var finalSpec = angular.copy(model.newInstanceSpec);

      cleanNullProperties(finalSpec);

      setFinalSpecBootsource(finalSpec);
      setFinalSpecFlavor(finalSpec);
      setFinalSpecKeyPairs(finalSpec);
      setFinalSpecSecurityGroups(finalSpec);

      return ec2API.importServer(finalSpec).then(successMessage);
    }

    function successMessage() {
      var numberInstances = 1;
      var message = ngettext('%s instance imported.', '%s instances imported.', numberInstances);
      toast.add('success', interpolate(message, [numberInstances]));
    }

    function cleanNullProperties(finalSpec) {
      // Initially clean fields that don't have any value.
      for (var key in finalSpec) {
        if (finalSpec.hasOwnProperty(key) && finalSpec[key] === null) {
          delete finalSpec[key];
        }
      }
    }

    //
    // Local
    //
    function onGetInstances(data) {
      model.instances.length = 0;
      push.apply(
        model.instances,
        data.data.items.filter(function (instance) {
          return ( instance.status === 'ACTIVE'
                || instance.status === 'SHUTOFF'
                || instance.status === 'PAUSED'
                || instance.status === 'SUSPENDED');
      }));

      if (model.instances.length === 1) {
        model.newInstanceSpec.instance_id = model.instances[0].id;
      } else if (model.instances.length > 1) {
        model.instances.unshift({
          label: gettext("Any Instance"),
          value: ""
        });
        model.newInstanceSpec.instance_id = model.instances[0].id;
      }

      addAllowedBootSource(
        model.instances,
        bootSourceTypes.INSTANCE,
        gettext('Instance')
      );

    }

    function onGetRegions(data) {
      model.regions.length = 0;
      push.apply(
        model.regions,
        data.data.items.filter(function (region) {
          return region.name && region.endpoint;
        })
        .map(function (region) {
          return {label: region.name, value: region.name};
        })
      );

      if (model.regions.length === 1) {
        model.newInstanceSpec.region = model.regions[0].value;
      } else if (model.regions.length > 1) {
        model.regions.unshift({
          label: gettext("Current Region"),
          value: ""
        });
        model.newInstanceSpec.region = model.regions[0].value;
      }

    }

    function onGetAvailabilityZones(data) {
      model.availabilityZones.length = 0;
      push.apply(
        model.availabilityZones,
        data.data.items.filter(function (zone) {
          return zone.zone_name && zone.state === 'available';
        })
        .map(function (zone) {
          return {label: zone.zone_name, value: zone.zone_name};
        })
      );

      if (model.availabilityZones.length === 1) {
        model.newInstanceSpec.availability_zone = model.availabilityZones[0].value;
      } else if (model.availabilityZones.length > 1) {
        model.availabilityZones.unshift({
          label: gettext("Any Availability Zone"),
          value: ""
        });
        model.newInstanceSpec.availability_zone = model.availabilityZones[0].value;
      }

    }

    // Flavors

    function onGetFlavors(data) {
      model.flavors.length = 0;
      push.apply(model.flavors, data.data.items.sort(function (a, b) {
        if(a.name > b.name) return -1;
        if(a.name < b.name) return 1;
        return 0;
      }));
    }

    function setFinalSpecFlavor(finalSpec) {
      if (finalSpec.flavor) {
        finalSpec.flavor_id = finalSpec.flavor.id;
      } else {
        delete finalSpec.flavor_id;
      }

      delete finalSpec.flavor;
    }

    // Keypairs

    function onGetKeypairs(data) {
      angular.extend(
        model.keypairs,
        data.data.items.map(function (keypair) {
          keypair.id = 'li_keypair:' + keypair.name;
          return keypair;
        }));
      if (data.data.items.length === 1) {
        model.newInstanceSpec.key_pair.push(data.data.items[0]);
      }
    }

    function setFinalSpecKeyPairs(finalSpec) {
      // Nova only wants the key name. It is a required field, even if None.
      if (!finalSpec.key_name && finalSpec.key_pair.length === 1) {
        finalSpec.key_name = finalSpec.key_pair[0].name;
      } else if (!finalSpec.key_name) {
        finalSpec.key_name = null;
      }

      delete finalSpec.key_pair;
    }

    // Security Groups

    function onGetSecurityGroups(data) {
      model.securityGroups.length = 0;
      angular.forEach(data.data.items, function addDefault(item) {
        if (item.GroupName === 'default') {
          model.newInstanceSpec.security_groups.push(item);
        }
      });
      push.apply(model.securityGroups, data.data.items);
    }

    function setFinalSpecSecurityGroups(finalSpec) {
      // pull out the ids from the security groups objects
      var securityGroupIds = [];
      finalSpec.security_groups.forEach(function(securityGroup) {
        securityGroupIds.push(securityGroup.id);
      });
      finalSpec.security_groups = securityGroupIds;
    }

    function addAllowedBootSource(rawTypes, type, label) {
      if (rawTypes) {
        model.allowedBootSources.push({
          type: type,
          label: label
        });
      }
    }

    function setFinalSpecBootsource(finalSpec) {
      finalSpec.source_id = finalSpec.source && finalSpec.source[0] && finalSpec.source[0].id;
      delete finalSpec.source;
    }

    // Nova Limits

    function onGetNovaLimits(data) {
      angular.extend(model.novaLimits, data.data);
    }

    return model;
  }

})();
