/**
 * Created by dennis.hong on 2017. 5. 2..
 */
(function() {
  'use strict';

  angular
    .module('horizon.dashboard.aws', [])
    .controller('Ec2Controller', Ec2Controller);

  Ec2Controller.$inject = [ '$http' ];

  function Ec2Controller($http) {
    var ctrl = this;
    ctrl.items = [
      { name: 'abc', id: 123 },
      { name: 'efg', id: 345 },
      { name: 'hij', id: 678 }
    ];
  }
})();
