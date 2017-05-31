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

  describe('horizon.dashboard.aws', function () {
    it('should be defined', function () {
      expect(angular.module('horizon.dashboard.aws')).toBeDefined();
    });
  });

  describe('horizon.dashboard.aws.basePath constant', function () {
    var awsBasePath, staticUrl;

    beforeEach(module('horizon.dashboard.aws'));
    beforeEach(inject(function ($injector) {
      awsBasePath = $injector.get('horizon.dashboard.aws.basePath');
      staticUrl = $injector.get('$window').STATIC_URL;
    }));

    it('should be defined', function () {
      expect(awsBasePath).toBeDefined();
    });

    it('should equal to "/static/dashboard/aws/"', function () {
      expect(awsBasePath).toEqual(staticUrl + 'dashboard/aws/');
    });
  });

})();
