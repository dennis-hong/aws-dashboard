/*
 * © Copyright 2017 dennis hong.
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

  /**
   * @ngdoc overview
   * @ngname horizon.dashboard.aws
   *
   * @description
   * Dashboard module to host aws panels.
   */
  angular
    .module('horizon.dashboard.aws', [
      'horizon.dashboard.aws.containers',
      'horizon.dashboard.aws.workflow',
      'horizon.dashboard.aws.aws-service-api'
    ])
    .config(config);

  config.$inject = ['$provide', '$windowProvider'];

    /**
   * @name horizon.dashboard.aws.basePath
   * @param {Object} $provide
   * @param {Object} $windowProvider
   * @description Base path for the aws dashboard
   * @returns {undefined} Returns nothing
   */
  function config($provide, $windowProvider) {
    var path = $windowProvider.$get().STATIC_URL + 'dashboard/aws/';
    $provide.constant('horizon.dashboard.aws.basePath', path);

  }
})();
