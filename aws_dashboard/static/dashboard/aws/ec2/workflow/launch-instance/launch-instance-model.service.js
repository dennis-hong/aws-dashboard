(function () {
  'use strict';

  var push = Array.prototype.push;
  var noop = angular.noop;

  /**
   * @ngdoc overview
   * @name horizon.dashboard.aws.workflow.launch-instance
   *
   * @description
   * Manage workflow of creating server.
   */

  angular
    .module('horizon.dashboard.aws.workflow.launch-instance')
    .factory('launchEC2InstanceModel', launchEC2InstanceModel);

  launchEC2InstanceModel.$inject = [
    '$q',
    '$log',
    'horizon.app.core.openstack-service-api.nova',
    'horizon.app.core.openstack-service-api.settings',
    'horizon.dashboard.aws.workflow.launch-instance.boot-source-types',
    'horizon.framework.widgets.toast.service',
    'horizon.dashboard.aws.aws-service-api.ec2'
  ];

  /**
   * @ngdoc service
   * @name launchEC2InstanceModel
   *
   * @param {Object} $q
   * @param {Object} $log
   * @param {Object} novaAPI
   * @param {Object} settings
   * @param {Object} bootSourceTypes
   * @param {Object} toast
   * @param {Object} ec2API
   * @description
   * This is the M part in MVC design pattern for launch instance
   * wizard workflow. It is responsible for providing data to the
   * view of each step in launch instance workflow and collecting
   * user's input from view for  creation of new instance.  It is
   * also the center point of communication between launch instance
   * UI and services API.
   * @returns {Object} The model
   */
  function launchEC2InstanceModel(
    $q,
    $log,
    novaAPI,
    settings,
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

      availabilityZones: [],
      flavors: [],
      allowedBootSources: [],
      images: [],
      allowCreateVolumeFromImage: false,
      arePortProfilesSupported: false,
      imageSnapshots: [],
      keypairs: [],
      metadataDefs: {
        flavor: null,
        image: null,
        volume: null,
        instance: null,
        hints: null
      },
      networks: [],
      ports: [],
      neutronEnabled: false,
      novaLimits: {},
      profiles: [],
      securityGroups: [],
      serverGroups: [],
      volumeBootable: false,
      volumes: [],
      volumeSnapshots: [],
      metadataTree: null,
      hintsTree: null,

      /**
       * api methods for UI controllers
       */

      initialize: initialize,
      createInstance: createInstance
    };

    // Local function.
    function initializeNewInstanceSpec() {

      model.newInstanceSpec = {
        availability_zone: null,
        admin_pass: null,
        config_drive: false,
        // REQUIRED Server Key.  Null allowed.
        user_data: '',
        disk_config: 'AUTO',
        // REQUIRED
        flavor: null,
        instance_count: 1,
        // REQUIRED Server Key
        key_pair: [],
        // REQUIRED
        name: null,
        networks: [],
        ports: [],
        profile: {},
        scheduler_hints: {},
        // REQUIRED Server Key. May be empty.
        security_groups: [],
        server_groups: [],
        // REQUIRED for JS logic (image | snapshot | volume | volume_snapshot)
        source_type: null,
        source: [],
        // REQUIRED for JS logic
        vol_create: false,
        // May be null
        vol_device_name: 'vda',
        vol_delete_on_instance_delete: false,
        vol_size: 1
      };
    }

    /**
     * @ngdoc method
     * @name launchEC2InstanceModel.initialize
     * @returns {promise}
     *
     * @description
     * Send request to get all data to initialize the model.
     */

    function initialize(deep) {
      var deferred, promise;

      // Each time opening launch instance wizard, we need to do this, or
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

        var launchInstanceDefaults = settings.getSetting('LAUNCH_INSTANCE_DEFAULTS');

        promise = $q.all([
          ec2API.getAvailabilityZones().then(onGetAvailabilityZones, noop),
          ec2API.getFlavors().then(onGetFlavors, noop),
          ec2API.getKeypairs().then(onGetKeypairs, noop),
          novaAPI.getLimits(true).then(onGetNovaLimits, noop),
          ec2API.getSecurityGroups().then(onGetSecurityGroups, noop),
          launchInstanceDefaults.then(addImageSourcesIfEnabled, noop),
          launchInstanceDefaults.then(setDefaultValues, noop)
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

    function setDefaultValues(defaults) {
      if (!defaults) {
        return;
      }
      if ('config_drive' in defaults) {
        model.newInstanceSpec.config_drive = defaults.config_drive;
      }
    }

    /**
     * @ngdoc method
     * @name launchEC2InstanceModel.createInstance
     * @returns {promise}
     *
     * @description
     * Send request for creating server.
     */

    function createInstance() {
      var finalSpec = angular.copy(model.newInstanceSpec);

      cleanNullProperties(finalSpec);

      setFinalSpecBootsource(finalSpec);
      setFinalSpecFlavor(finalSpec);
      setFinalSpecKeyPairs(finalSpec);
      setFinalSpecSecurityGroups(finalSpec);

      return ec2API.createServer(finalSpec).then(successMessage);
    }

    function successMessage() {
      var numberInstances = model.newInstanceSpec.instance_count;
      var message = ngettext('%s instance launched.', '%s instances launched.', numberInstances);
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
      push.apply(model.flavors, data.data.items);
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

    function addImageSourcesIfEnabled(config) {
      // in case settings are deleted or not present
      var allEnabled = !config;
      // if the settings are missing or the specific setting is missing default to true
      var enabledImage = allEnabled || !config.disable_image;
      var enabledSnapshot = allEnabled || !config.disable_instance_snapshot;

      if (enabledImage || enabledSnapshot) {
        return ec2API.getImages({State: 'available'}).then(function getEnabledImages(data) {
          if (enabledImage) {
            onGetImages(data);
          }
          if (enabledSnapshot) {
            onGetSnapshots(data);
          }
        });
      }
    }

    function isBootableImageType(image) {
      // This is a blacklist of images that can not be booted.
      // If the image container type is in the blacklist
      // The evaluation will result in a 0 or greater index.
      return bootSourceTypes.NON_BOOTABLE_IMAGE_TYPES.indexOf(image.container_format) < 0;
    }

    function onGetImages(data) {
      model.images.length = 0;
      push.apply(model.images, data.data.items.filter(function (image) {
        return true
      }));
      addAllowedBootSource(model.images, bootSourceTypes.IMAGE, gettext('Image'));
    }

    function onGetSnapshots(data) {
      model.imageSnapshots.length = 0;
      push.apply(model.imageSnapshots, data.data.items.filter(function (image) {
        return isBootableImageType(image) &&
          (image.properties && image.properties.image_type === 'snapshot');
      }));

      addAllowedBootSource(
        model.imageSnapshots,
        bootSourceTypes.INSTANCE_SNAPSHOT,
        gettext('Instance Snapshot')
      );
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
      delete finalSpec.source_type;
    }

    // Nova Limits

    function onGetNovaLimits(data) {
      angular.extend(model.novaLimits, data.data);
    }

    return model;
  }

})();
