
Project is under development. I haven't made a decision about the project name. It is my just-for-fun home project.

Licensed under AGPL-3.0 (or newer) license. Check `LICENSE` for details.

# TODO
* Write README
* Code the Project

# API
## Tests
Build an image and run tests with podman in a container.
```
$ cd tests
$ podman build -t tasker-test -f Dockerfile.fedora-32 .
$ ./test-api.sh
```
