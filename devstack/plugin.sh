# plugin.sh - DevStack plugin.sh dispatch script ironic-ui

function install_aws_dashboard {
    setup_develop ${AWS_DASHBOARD_DIR}

    mv $AWS_DASHBOARD_DIR/_test-requirements.txt $AWS_DASHBOARD_DIR/test-requirements.txt
}

# check for service enabled
if is_service_enabled horizon && is_service_enabled aws-dashboard; then

    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # Set up system services
        # no-op
        :
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing AWS Dashboard"
        install_aws_dashboard
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring AWS Dashboard"
        cp -a ${AWS_DASHBOARD_DIR}/aws_dashboard/local/enabled/* ${DEST}/horizon/openstack_dashboard/local/enabled/
        cp -a ${AWS_DASHBOARD_DIR}/aws_dashboard/local/local_settings.d/* ${DEST}/horizon/openstack_dashboard/local/local_settings.d/
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # no-op
        :
    fi

    if [[ "$1" == "unstack" ]]; then
        # no-op
        :
    fi

    if [[ "$1" == "clean" ]]; then
        # Remove state and transient data
        # Remember clean.sh first calls unstack.sh
        # no-op
        :
    fi
fi