(function () {
  'use strict';

  var push = Array.prototype.push;
  var noop = angular.noop;

  /**
   * @ngdoc overview
   * @name horizon.dashboard.aws.workflow.export-instance
   *
   * @description
   * Manage workflow of creating server.
   */

  angular
    .module('horizon.dashboard.aws.workflow.export-instance')
    .factory('exportInstanceModel', exportInstanceModel);

  exportInstanceModel.$inject = [
    '$q',
    '$log',
    'horizon.app.core.openstack-service-api.glance',
    'horizon.app.core.openstack-service-api.neutron',
    'horizon.app.core.openstack-service-api.nova',
    'horizon.app.core.openstack-service-api.security-group',
    'horizon.app.core.openstack-service-api.serviceCatalog',
    'horizon.app.core.openstack-service-api.settings',
    'horizon.dashboard.aws.workflow.export-instance.boot-source-types',
    'horizon.framework.widgets.toast.service',
    'horizon.app.core.openstack-service-api.policy',
    'horizon.dashboard.project.workflow.launch-instance.step-policy',
    'horizon.dashboard.aws.aws-service-api.ec2'
  ];

  /**
   * @ngdoc service
   * @name exportInstanceModel
   *
   * @param {Object} $q
   * @param {Object} $log
   * @param {Object} glanceAPI
   * @param {Object} neutronAPI
   * @param {Object} novaAPI
   * @param {Object} securityGroup
   * @param {Object} serviceCatalog
   * @param {Object} settings
   * @param {Object} bootSourceTypes
   * @param {Object} toast
   * @param {Object} policy
   * @param {Object} stepPolicy
   * @description
   * This is the M part in MVC design pattern for export instance
   * wizard workflow. It is responsible for providing data to the
   * view of each step in export instance workflow and collecting
   * user's input from view for  creation of new instance.  It is
   * also the center point of communication between export instance
   * UI and services API.
   * @returns {Object} The model
   */
  function exportInstanceModel(
    $q,
    $log,
    glanceAPI,
    neutronAPI,
    novaAPI,
    securityGroup,
    serviceCatalog,
    settings,
    bootSourceTypes,
    toast,
    policy,
    stepPolicy,
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
        source_type: null,
        source: [],
        leave_original_instance: true,
        leave_instance_snapshot: false
      };
    }

    /**
     * @ngdoc method
     * @name exportInstanceModel.initialize
     * @returns {promise}
     *
     * @description
     * Send request to get all data to initialize the model.
     */

    function initialize(deep) {
      var deferred, promise;

      // Each time opening export instance wizard, we need to do this, or
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

        var exportInstanceDefaults = settings.getSetting('LAUNCH_INSTANCE_DEFAULTS');

        promise = $q.all([
          ec2API.getServers().then(onGetInstances, noop),
          novaAPI.getAvailabilityZones().then(onGetAvailabilityZones, noop),
          novaAPI.getFlavors(true, true).then(onGetFlavors, noop),
          novaAPI.getKeypairs().then(onGetKeypairs, noop),
          novaAPI.getLimits(true).then(onGetNovaLimits, noop),
          securityGroup.query().then(onGetSecurityGroups, noop),
          serviceCatalog.ifTypeEnabled('network').then(getNetworks, noop),
          exportInstanceDefaults.then(setDefaultValues, noop),
        ]);

        promise.then(onInitSuccess, onInitFail);
      }

      return promise;
    }

    function onInitSuccess() {
      model.initializing = false;
      model.initialized = true;
      // This provides supplemental data non-critical to exporting
      // an instance.  Therefore we load it only if the critical data
      // all loads successfully.
      getServerGroups();
      getMetadataDefinitions();
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
     * @name exportInstanceModel.createInstance
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
      setFinalSpecNetworks(finalSpec);
      setFinalSpecPorts(finalSpec);
      setFinalSpecKeyPairs(finalSpec);
      setFinalSpecSecurityGroups(finalSpec);
      setFinalSpecServerGroup(finalSpec);
      setFinalSpecSchedulerHints(finalSpec);
      setFinalSpecMetadata(finalSpec);

      return ec2API.exportServer(finalSpec).then(successMessage);
    }

    function successMessage() {
      var numberInstances = model.newInstanceSpec.instance_count;
      var message = ngettext('%s instance exported.', '%s instances exported.', numberInstances);
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
    function addAllowedBootSource(rawTypes, type, label) {
      if (rawTypes) {
        model.allowedBootSources.push({
          type: type,
          label: label
        });
      }
    }

    function onGetInstances(data) {
      model.instances.length = 0;
      push.apply(
        model.instances,
        data.data.items.filter(function (instance) {
          return instance.status === "running";
      }));

      if (model.instances.length === 1) {
        model.newInstanceSpec.source_id = model.instances[0].id;
      } else if (model.instances.length > 1) {
        model.instances.unshift({
          label: gettext("Any Instance"),
          value: ""
        });
        model.newInstanceSpec.source_id = model.instances[0].id;
      }

      addAllowedBootSource(
        model.instances,
        bootSourceTypes.INSTANCE,
        gettext('Instance')
      );

    }

    function onGetAvailabilityZones(data) {
      model.availabilityZones.length = 0;
      push.apply(
        model.availabilityZones,
        data.data.items.filter(function (zone) {
          return zone.zoneState && zone.zoneState.available;
        })
        .map(function (zone) {
          return {label: zone.zoneName, value: zone.zoneName};
        })
      );

      if (model.availabilityZones.length === 1) {
        model.newInstanceSpec.availability_zone = model.availabilityZones[0].value;
      } else if (model.availabilityZones.length > 1) {
        // There are 2 or more; allow ability for nova scheduler to pick,
        // and make that the default.
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
        data.data.items.map(function (e) {
          e.keypair.id = 'li_keypair:' + e.keypair.name;
          return e.keypair;
        }));
      if (data.data.items.length === 1) {
        model.newInstanceSpec.key_pair.push(data.data.items[0].keypair);
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
        // 'default' is a special security group in neutron. It can not be
        // deleted and is guaranteed to exist. It by default contains all
        // of the rules needed for an instance to reach out to the network
        // so the instance can provision itself.
        if (item.name === 'default') {
          model.newInstanceSpec.security_groups.push(item);
        }
      });
      push.apply(model.securityGroups, data.data.items);
    }

    function setFinalSpecSecurityGroups(finalSpec) {
      // pull out the ids from the security groups objects
      var securityGroupIds = [];
      finalSpec.security_groups.forEach(function(securityGroup) {
        if (model.neutronEnabled) {
          securityGroupIds.push(securityGroup.id);
        } else {
          securityGroupIds.push(securityGroup.name);
        }
      });
      finalSpec.security_groups = securityGroupIds;
    }

    // Server Groups

    function getServerGroups() {
      if (policy.check(stepPolicy.serverGroups)) {
        return novaAPI.getServerGroups().then(onGetServerGroups, noop);
      }
    }

    function onGetServerGroups(data) {
      model.serverGroups.length = 0;
      push.apply(model.serverGroups, data.data.items);
    }

    function setFinalSpecServerGroup(finalSpec) {
      if (finalSpec.server_groups.length > 0) {
        finalSpec.scheduler_hints.group = finalSpec.server_groups[0].id;
      }
      delete finalSpec.server_groups;
    }

    // Networks

    function getNetworks() {
      return neutronAPI.getNetworks().then(onGetNetworks, noop).then(getPorts, noop);
    }

    function onGetNetworks(data) {
      model.neutronEnabled = true;
      model.networks.length = 0;
      if (data.data.items.length === 1) {
        model.newInstanceSpec.networks.push(data.data.items[0]);
      }
      push.apply(model.networks,
        data.data.items.filter(function(net) {
          return net.subnets.length > 0;
        }));
      return data;
    }

    function setFinalSpecNetworks(finalSpec) {
      finalSpec.nics = [];
      finalSpec.networks.forEach(function (network) {
        finalSpec.nics.push(
          {
            "net-id": network.id,
            "v4-fixed-ip": ""
          });
      });
      delete finalSpec.networks;
    }

    function getPorts(networks) {
      model.ports.length = 0;
      networks.data.items.forEach(function(network) {
        return neutronAPI.getPorts({network_id: network.id}).then(
          function(ports) {
            onGetPorts(ports, network);
          }, noop
        );
      });
    }

    function onGetPorts(networkPorts, network) {
      var ports = [];
      networkPorts.data.items.forEach(function(port) {
        // no device_owner means that the port can be attached
        if (port.device_owner === "" && port.admin_state === "UP") {
          port.subnet_names = getPortSubnets(port, network.subnets);
          port.network_name = network.name;
          ports.push(port);
        }
      });
      push.apply(model.ports, ports);
    }

    // helper function to return an object of IP:NAME pairs for subnet mapping
    function getPortSubnets(port, subnets) {
      var subnetNames = {};
      port.fixed_ips.forEach(function (ip) {
        subnets.forEach(function (subnet) {
          if (ip.subnet_id === subnet.id) {
            subnetNames[ip.ip_address] = subnet.name;
          }
        });
      });

      return subnetNames;
    }

    function setFinalSpecPorts(finalSpec) {
      // nics should already be filled so we only append to it
      finalSpec.ports.forEach(function (port) {
        finalSpec.nics.push(
          {
            "port-id": port.id
          });
      });
      delete finalSpec.ports;
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

    // Scheduler hints

    function setFinalSpecSchedulerHints(finalSpec) {
      if (model.hintsTree) {
        var hints = model.hintsTree.getExisting();
        if (!angular.equals({}, hints)) {
          angular.forEach(hints, function(value, key) {
            finalSpec.scheduler_hints[key] = value + '';
          });
        }
      }
    }

    // Instance metadata

    function setFinalSpecMetadata(finalSpec) {
      if (model.metadataTree) {
        var meta = model.metadataTree.getExisting();
        if (!angular.equals({}, meta)) {
          angular.forEach(meta, function(value, key) {
            meta[key] = value + '';
          });
          finalSpec.meta = meta;
        }
      }
    }

    // Metadata Definitions

    /**
     * Metadata definitions provide supplemental information in source image detail
     * rows and are used on the metadata tab for adding metadata to the instance and
     * on the scheduler hints tab.
     */
    function getMetadataDefinitions() {
      // Metadata definitions often apply to multiple resource types. It is optimal to make a
      // single request for all desired resource types.
      //   <key>: [<resource_type>, <properties_target>]
      var resourceTypes = {
        flavor: ['OS::Nova::Flavor', ''],
        image: ['OS::Glance::Image', ''],
        volume: ['OS::Cinder::Volumes', ''],
        instance: ['OS::Nova::Server', 'metadata']
      };

      angular.forEach(resourceTypes, applyForResourceType);

      // Need to check setting and policy for scheduler hints
      $q.all([
        settings.ifEnabled('LAUNCH_INSTANCE_DEFAULTS.enable_scheduler_hints', true, true),
        policy.ifAllowed(stepPolicy.schedulerHints)
      ]).then(function getSchedulerHints() {
        applyForResourceType(['OS::Nova::Server', 'scheduler_hints'], 'hints');
      });
    }

    function applyForResourceType(resourceType, key) {
      glanceAPI
        .getNamespaces({ resource_type: resourceType[0],
                         properties_target: resourceType[1] }, true)
        .then(function(data) {
          var namespaces = data.data.items;
          // This will ensure that the metaDefs model object remains
          // unchanged until metadefs are fully loaded. Otherwise,
          // partial results are loaded and can result in some odd
          // display behavior.
          model.metadataDefs[key] = namespaces;
        });
    }

    return model;
  }

})();
