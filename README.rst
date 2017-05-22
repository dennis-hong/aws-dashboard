=========
Openstack Horizon Plugin Starter Kit
=========

This will help you quickly and easily develop Openstack Horizon plugins.

HOW TO USE
-------------------------

1. Clone the Stater Kit repository::

    git clone https://github.com/dennis-hong/horizon-plugin-starter-kit.git

2. Copy the ``_31000_myplugin.py`` file from ``$NEW_NAME/enabled/_31000_myplugin.py`` file to
   ``horizon/openstack_dashboard/local/enabled`` directory. Example, set as if being
   executed from the root of the stater kit repository::

    cd horizon-plugin-starter-kit
    cp ./myplugin_ui/enabled/_31000_myplugin.py ../horizon/openstack_dashboard/local/enabled/

3. pip install plugin(sudo)::

    pip install -e .

4. Go back into the horizon repository and collect your static files::

    cd ../horizon
    python manage.py collectstatic --noinput
    python manage.py compress --force

4. Restart your horizon and check plugin::

    sudo service apache2 restart

5. Customize your page : myplugin_ui/content/myplugin/templates/myplugin/index.html

* To uninstall::

    cd horizon-plugin-starter-kit
    pip uninstall .
    cd ../horizon
    rm openstack_dashboard/local/enabled/_31000_myplugin.py*
    python manage.py collectstatic --noinput
    python manage.py compress --force
    sudo service apache2 restart

