/**
 * Copyright 2017, dennis hong.
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
    .module('horizon.dashboard.aws.aws-service-api')
    .factory('horizon.dashboard.aws.aws-service-api.ec2', ec2API);

  ec2API.$inject = [
    'horizon.framework.util.http.service',
    'horizon.framework.widgets.toast.service',
    '$window'
  ];

  /**
   * @ngdoc service
   * @param {Object} apiService
   * @param {Object} toastService
   * @param {Object} $window
   * @name ec2Api
   * @description Provides access to EC2 APIs.
   * @returns {Object} The service
   */
  function ec2API(apiService, toastService, $window) {

    var service = {
      createServer: createServer,
      importServer: importServer,
      exportServer: exportServer,
      getServers: getServers,
      getImages: getImages,
      getFlavors: getFlavors,
      getSecurityGroups: getSecurityGroups,
      getKeypairs: getKeypairs,
      getCreateKeypairUrl: getCreateKeypairUrl,
      getRegenerateKeypairUrl: getRegenerateKeypairUrl,
      createKeypair: createKeypair,
      getAvailabilityZones: getAvailabilityZones,
      getRegions: getRegions
    };

    return service;

    ///////////

    // Servers

    /**
     * @name createServer
     * @param {Object} newServer - The new server
     * @description
     * Create a server using the parameters supplied in the
     * newServer. The required parameters:
     *
     * "name", "source_id", "flavor_id", "key_name", "user_data"
     *     All strings
     * "security_groups"
     *     An array of one or more objects with a "name" attribute.
     *
     * Other parameters are accepted as per the underlying novaclient:
     * "block_device_mapping", "block_device_mapping_v2", "nics", "meta",
     * "availability_zone", "instance_count", "admin_pass", "disk_config",
     * "config_drive"
     *
     * @returns {Object} The result of the API call
     */
    function createServer(newServer) {
      return apiService.post('/api/aws/ec2/instances/', newServer)
        .error(function () {
          toastService.add('error', gettext('Unable to create the server.'));
        });
    }

    function getServers(params) {
      var config = params ? { 'params' : params} : {};
      return apiService.get('/api/aws/ec2/instances/', config)
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the instances.'));
        });
    }

    function getImages(params) {
      var config = params ? { 'params' : params} : {};
      return apiService.get('/api/aws/ec2/images/', config)
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the images.'));
        });
    }

    function getFlavors(params) {
      var config = params ? { 'params' : params} : {};
      return apiService.get('/api/aws/ec2/flavors/', config)
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the flavors.'));
        });
    }

    function getSecurityGroups() {
      return apiService.get('/api/aws/ec2/security-groups/')
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the security groups.'));
        });
    }

    function getKeypairs() {
      return apiService.get('/api/aws/ec2/keypairs/')
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the keypairs.'));
        });
    }

    function getRegenerateKeypairUrl(keyPairName) {
      return getCreateKeypairUrl(keyPairName) + "?regenerate=true";
    }

    function getCreateKeypairUrl(keyPairName) {
      // NOTE: WEBROOT by definition must end with a slash (local_settings.py).
      return $window.WEBROOT + "api/aws/ec2/keypairs/" +
        encodeURIComponent(keyPairName) + "/";
    }

    function createKeypair(key_pair) {
      return apiService.post('/api/aws/ec2/keypairs/', key_pair)
        .error(function () {
          toastService.add('error', gettext('Unable to create the keypairs.'));
        });
    }

    function importServer(server) {
      return apiService.post('/api/aws/ec2/import-instances/', server)
        .error(function () {
          toastService.add('error', gettext('Unable to import the server.'));
        });
    }

    function exportServer(server) {
      return apiService.post('/api/aws/ec2/export-instances/', server)
        .error(function () {
          toastService.add('error', gettext('Unable to export the server.'));
        });
    }

    function getRegions() {
      return apiService.get('/api/aws/ec2/regions/')
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the region.'));
        });
    }

    function getAvailabilityZones() {
      return apiService.get('/api/aws/ec2/availability-zones/')
        .error(function () {
          toastService.add('error', gettext('Unable to retrieve the availability zones.'));
        });
    }

  }
}());
