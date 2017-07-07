================================
AWS Plugin For OpenStack Horizon
================================
.. image:: https://img.shields.io/badge/license-Apache%202-blue.svg
    :target: https://raw.githubusercontent.com/dennis-hong/aws-dashboard/master/LICENSE
On Developing... !! Experimental Project !!

AWS Plugin For Openstack Horizon

.. image:: https://cloud.githubusercontent.com/assets/23111859/26439340/af7acc86-4162-11e7-89de-48ef89451987.png

How To Install
--------------

1. Clone this repository::

    git clone https://github.com/dennis-hong/aws-dashboard.git

2. Copy the ``_3*.py`` file from ``aws-dashboard/aws_dashboard/enabled/_3*.py`` file to
   ``horizon/openstack_dashboard/local/enabled`` directory. Example::

    cd aws-dashboard
    cp ./aws_dashboard/local/enabled/_3*.py ../horizon/openstack_dashboard/local/enabled/
    cp ./aws_dashboard/local/local_settings.d/_30000_aws_dashboard.py ../horizon/openstack_dashboard/local/local_settings.d/

3. install plugin::

    sudo pip install -e .
    sudo python setup.py build
    sudo python setup.py install

4. Go back into the horizon repository and collect your static files::

    cd ../horizon
    python manage.py collectstatic --noinput && python manage.py compress --force

4. Restart your horizon and check plugin::

    sudo service apache2 restart

5. Configure "AWS API Key" in your horizon local setting::

    vi openstack_dashboard/local/local_settings.d/_30000_aws_dashboard.py
    
    AWS_API_KEY_DICT = {
        "$PROJECT_UUID": {
            "AWS_ACCESS_KEY_ID": "$AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY": "$AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME": "ap-northeast-2"
        },
        "$PROJECT_UUID": {
            "AWS_ACCESS_KEY_ID": "",
            "AWS_SECRET_ACCESS_KEY": "",
            "AWS_REGION_NAME": ""
        },
    }

DevStack Install
----------------

Add just one line in your local.conf::

    enable_plugin aws-dashboard https://github.com/dennis-hong/aws-dashboard.git stable/newton

Additional Settings
-------------------
1. Requires AWS API Key permission

    1) Go to(AWS IAM Menu) : https://console.aws.amazon.com/iam/home

    2) Requires Permission
     - AmazonEC2FullAccess
     - AmazonS3FullAccess
     - AWSImportExportFullAccess

 - DOC : http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html

2. Installing qemu-utils package is required for image conversion.(qemu-img convert)::

    sudo apt-get install -y qemu-utils
    OR
    sudo yum install -y qemu-img

 - DOC : http://docs.aws.amazon.com/vm-import/latest/userguide/how-vm-import-export-works.html

3. (Optional) Nova-compute's 'injected_network_template' setting is required
   to revert the interface settings that AWS modified when importing instances.
   *If your VM interface name is 'eht0' in your OpenStack environment, you do not need this setting.


How To Uninstall
----------------
::

    cd aws-dashboard
    pip uninstall .
    cd ../horizon
    rm openstack_dashboard/local/enabled/_30000_aws_dashboard.py
    rm openstack_dashboard/local/enabled/_31000_aws_compute_panel_group.py
    rm openstack_dashboard/local/enabled/_31100_aws_compute_ec2_panel.py
    rm openstack_dashboard/local/enabled/_31120_aws_compute_access_and_security_panel.py
    rm openstack_dashboard/local/enabled/_31110_aws_compute_images_panel.py
    rm openstack_dashboard/local/enabled/_31200_aws_compute_transport_panel.py
    rm openstack_dashboard/local/local_settings.d/_30000_aws_dashboard.py
    python manage.py collectstatic --noinput && python manage.py compress --force
    sudo service apache2 restart

