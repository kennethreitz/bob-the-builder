import os
import time

from uuid import uuid4
from pathlib import Path

import logme
import delegator


@logme.log
class Build:
    def __init__(
        self,
        *,
        name,
        codepath,
        push=False,
        username=None,
        password=None,
        trigger_build=True,
        trigger_push=True,
    ):
        self.uuid = uuid4().hex
        self.name = name
        self.codepath = Path(codepath)
        self.push_to = push
        self.username = username
        self.password = password
        self.was_built = None

        assert os.path.exists(self.codepath)

        if trigger_build:
            self.build()

        if trigger_push:
            self.push()

    @property
    def requires_login(self):
        return all([self.username, self.password])

    @property
    def tag(self):
        if not self.push_to:
            return f"{self.name}:{self.uuid}"
        else:
            return f"{self.push_to}/{self.name}:{self.uuid}"

    @property
    def has_dockerfile(self):
        return os.path.isfile((self.codepath / "Dockerfile").resolve())

    def ensure_docker(self):
        c = delegator.run("service docker start")
        time.sleep(0.3)

        try:
            if self.requires_login:
                c = delegator.run(f"docker login -u {self.username} -p {self.password}")
                assert c.ok
            c = delegator.run("docker ps")
            assert c.ok
        except AssertionError:
            raise RuntimeError("Docker is not available.")

    def docker_build(self):
        self.logger.info(f"Using Docker to build {self.uuid!r} of {self.name!r}.")

        self.ensure_docker()

        c = delegator.run(f"docker build {self.codepath} --tag {self.tag}")
        self.logger.debug(c.out)
        self.logger.debug(c.err)
        assert c.ok

    def buildpack_build(self):
        self.logger.info(f"Using buildpacks to build {self.uuid!r}.")

    def build(self):
        self.logger.info(f"Starting build {self.uuid!r} of {self.name!r}.")
        if self.has_dockerfile:
            self.docker_build()
        else:
            self.buildpack_build()

        self.was_built = True

    def push(self):
        assert self.was_built
        assert self.push

        c = delegator.run(f"docker push {self.tag}")
        self.logger.debug(c.out)
        self.logger.debug(c.err)
        assert c.ok