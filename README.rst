=========
AWS Plugin For Openstack Horizon
=========
AWS Plugin For Openstack Horizon On Developing...

HOW TO USE
-------------------------

1. Clone this repository::

    git clone https://github.com/dennis-hong/aws-dashboard.git

2. Copy the ``_3*.py`` file from ``aws-dashboard/aws_dashboard/enabled/_3*.py`` file to
   ``horizon/openstack_dashboard/local/enabled`` directory. Example::

    cd aws-dashboard
    cp ./aws-dashboard/local/enabled/_3*.py ../horizon/openstack_dashboard/local/enabled/
    cp ./aws-dashboard/local/local_settings.d/_30000_aws_dashboard.py ../horizon/openstack_dashboard/local/local_settings.d/

3. pip install plugin::

    sudo pip install -e .

4. Go back into the horizon repository and collect your static files::

    cd ../horizon
    python manage.py collectstatic --noinput
    python manage.py compress --force

4. Restart your horizon and check plugin::

    sudo service apache2 restart

5. Configure "AWS API Key" in your horizon local setting::

    vi horizon/openstack_dashboard/local/local_settings.d/_30000_aws_dashboard.py
    
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

* To uninstall::

    cd aws-dashboard
    pip uninstall .
    cd ../horizon
    rm openstack_dashboard/local/enabled/_3*.py*
    rm openstack_dashboard/local/local_settings.d/_30000_aws_dashboard.py
    python manage.py collectstatic --noinput
    python manage.py compress --force
    sudo service apache2 restart

