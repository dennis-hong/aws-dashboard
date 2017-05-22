/*
 * © Copyright 2017 kakao corp.
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
   * Provides all of the services and widgets required
   * to support and display Myplugin related content.
   */
  angular
    .module('horizon.dashboard.aws', [])
    .config(config);

  config.$inject = ['$provide', '$windowProvider'];

  function config($provide, $windowProvider) {

    var path = $windowProvider.$get().STATIC_URL + 'dashboard/admin/aws/';
    $provide.constant('horizon.dashboard.aws.basePath', path);

  }
})();
