import shlex
import subprocess
import os
import sys
import re
import logging
import os
import shutil
import argparse

from dataclasses import dataclass
from typing import Optional
from distutils.version import StrictVersion

from environs import Env

from .cloud import Cloud, AWSCloud

JARS_PATH = 'jars'
DEFAULT_MINECRAFT_PATH = '/opt/minecraft'


class Server:
    """
    Represents a transient Minecraft server that pulls a save from the cloud,
    runs the server, and then on shutdown, pushes the new save back to the cloud
    and frees its compute resources.
    """

    def __init__(self, cloud: Cloud) -> None:
        self.cloud = cloud

        self.env = Env()
        self.env.read_env()

    def start(self) -> None:
        """
        Downloads the save, starts the Minecraft server, and uploads the save
        upon termination
        """
        try:
            self._create_minecraft_path()
            self.cloud.get_save(
                self.env.str('MINECRAFT_PATH', default=DEFAULT_MINECRAFT_PATH)
            )
            self._create_minecraft_eula()
            command = self._build_minecraft_cmd()

            with subprocess.Popen(
                args=shlex.split(command),
                stdin=sys.stdin,
                stdout=sys.stdout,
                cwd=self.env.str(
                    'MINECRAFT_PATH', default=DEFAULT_MINECRAFT_PATH
                )
            ):
                print('Starting Minecraft server...')
        finally:
            print('Minecraft server stopped.')
            self.cloud.put_save(
                self.env.str('MINECRAFT_PATH', default=DEFAULT_MINECRAFT_PATH)
            )
            self.cloud.kill_instance()

    def _create_minecraft_path(self) -> None:
        """
        Creates the path where Minecraft will run
        """
        os.makedirs(
            self.env.str('MINECRAFT_PATH', default=DEFAULT_MINECRAFT_PATH)
        )

    def _create_minecraft_eula(self) -> None:
        """
        Creates the EULA file with EULA accepted
        """
        eula_path = os.path.join(
            self.env.str('MINECRAFT_PATH', default=DEFAULT_MINECRAFT_PATH),
            'eula.txt'
        )
        if not os.path.exists(eula_path):
            shutil.copy('eula.txt', eula_path)

    def _build_minecraft_cmd(self) -> str:
        """
        Builds the java call to start the Minecraft server
        """
        jar_file = self._get_minecraft_jar()
        ram_mb = self.env.int('MINECRAFT_RAM_MB', default=1024)

        return 'java -Xmx%dM -Xms%dM -jar %s nogui' % (ram_mb, ram_mb, jar_file)

    def _get_minecraft_jar(self) -> str:
        """
        Gets the path to the Minecraft jar file to run based on the versions
        available and the MINECRAFT_VERSION environment variable
        """
        files = os.listdir(JARS_PATH)
        minecraft_versions = []
        for file in files:
            matches = re.search('minecraft_server\.([\d\.]+)\.jar', file)
            if matches is not None:
                minecraft_versions.append(matches[1])
        minecraft_versions.sort(key=StrictVersion)

        preferred_version = self.env.str('MINECRAFT_VERSION', default='latest')

        if len(minecraft_versions) == 0:
            raise Exception('No Minecraft versions available')
        elif (
            preferred_version != 'latest' and
            preferred_version not in minecraft_versions
        ):
            raise Exception(
                'Minecraft version %s not available' % preferred_version
            )
        elif preferred_version == 'latest':
            preferred_version = minecraft_versions[-1]

        return os.path.abspath(
            os.path.join(
                JARS_PATH, 'minecraft_server.%s.jar' % preferred_version
            )
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--cloud', type=str, choices=['aws'])

    args = parser.parse_args()

    if args.cloud == 'aws':
        AWSCloud.create_instance()
    else:
        server = Server(cloud=AWSCloud())
        server.start()
