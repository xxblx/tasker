#!/bin/bash
set -e

# Expects that the image already has been built
# podman build -t tasker-test -f Dockerfile.fedora-32 .
CONTAINER=tasker-test-f32
IMAGE=tasker-test
TESTS_DIRECTORY=$(dirname "$(readlink -f "$0")")
ROOT_DIRECTORY=$(dirname "$TESTS_DIRECTORY")

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

podman cp "$ROOT_DIRECTORY/server/." "$CONTAINER:/tasker/server"
podman cp "$ROOT_DIRECTORY/db_manage.py" "$CONTAINER:/tasker/db_manage.py"
podman cp "$ROOT_DIRECTORY/run_server.py" "$CONTAINER:/tasker/run_server.py"
podman cp "$TESTS_DIRECTORY/test_api" "$CONTAINER:/tasker/tests/test_api"
podman cp "$TESTS_DIRECTORY/conf.pytest-container.py" "$CONTAINER:/tasker/server/conf.py"
podman exec $CONTAINER find /tasker/server -name '__pycache__' -type d -exec rm -r {} +

podman exec -u taskeruser $CONTAINER /tasker/db_manage.py init-db
# `cmd || true` masks non-zero exit code of cmd, it is needed for future
# stop and rm commands when `set -e` is used
podman exec -u taskeruser -w /tasker $CONTAINER \
  python3 -m pytest tests/test_api -W ignore::DeprecationWarning -p no:cacheprovider \
  || true

podman container stop $CONTAINER
podman container rm $CONTAINER
