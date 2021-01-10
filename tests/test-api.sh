#!/bin/bash
set -e

# Expects that the image already has been built
# podman build -t tasker-test -f Dockerfile.fedora-32 .
CONTAINER=tasker-test-f32
IMAGE=tasker-test

podman run -d --name $CONTAINER $IMAGE
until podman exec $CONTAINER systemctl status | grep running
do
    echo '>>> Wait container to start'
    sleep 1
done
podman exec $CONTAINER postgresql-setup --initdb
podman exec $CONTAINER systemctl enable --now postgresql
podman exec -u postgres $CONTAINER createuser taskeruser
podman exec -u postgres $CONTAINER createdb taskerdb --owner='taskeruser'

podman cp ../server/. $CONTAINER:/tasker/server
podman cp ../db_manage.py $CONTAINER:/tasker/db_manage.py
podman cp ../run_server.py $CONTAINER:/tasker/run_server.py
podman cp test_api.py $CONTAINER:/tasker/tests/test_api.py
podman cp conf.pytest-container.py $CONTAINER:/tasker/server/conf.py
podman exec $CONTAINER find /tasker/server -name '__pycache__' -type d -exec rm -r {} +

podman exec -u taskeruser $CONTAINER /tasker/db_manage.py init-db
# `cmd || true` masks non-zero exit code of cmd
# it is needed for future stop and rm commands
podman exec -u taskeruser $CONTAINER pytest /tasker/tests/test_api.py -W ignore::DeprecationWarning -p no:cacheprovider || true

podman container stop $CONTAINER
podman container rm $CONTAINER
