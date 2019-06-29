import subprocess
import shlex
import os

from abc import ABC, abstractmethod
from typing import Optional

from environs import Env


class Cloud(ABC):
    """
    Represents an interface to a cloud service for storage and server hosting
    """

    def __init__(self) -> None:
        self.env = Env()
        self.env.read_env()

    @abstractmethod
    def get_save(self, local_path: str) -> None:
        """
        Downloads a save to the given path
        """
        raise NotImplementedError()

    @abstractmethod
    def put_save(self, local_path: str) -> None:
        """
        Uploads a save given its path
        """
        raise NotImplementedError()

    @abstractmethod
    def kill_instance(self) -> None:
        raise NotImplementedError()


class AWSCloud(Cloud):
    """
    An interface to AWS for world storage via S3 and server hosting via EC2
    """

    DEFAULT_REGION = 'us-west-1'

    def __init__(self) -> None:
        super(AWSCloud, self).__init__()
        # AWS CLI initial configuration - using AWS CLI for sync command
        aws_commands = [
            'aws configure set aws_access_key_id %s' %
            self.env.str('AWS_ACCESS_KEY_ID'),
            'aws configure set aws_secret_access_key %s' %
            self.env.str('AWS_SECRET_ACCESS_KEY'),
            'aws configure set region %s' %
            self.env.str('AWS_REGION', default=AWSCloud.DEFAULT_REGION)
        ]

        for command in aws_commands:
            subprocess.check_output(shlex.split(command))

        # Check accessibility of these mandatory env vars upfront
        self.env.str('AWS_S3_BUCKET')
        self.env.str('AWS_S3_SAVE_KEY')

    def get_save(self, local_path: str) -> None:
        print('Downloading save...')
        subprocess.check_output(
            shlex.split(
                'aws s3 sync %s %s --delete' % (self._s3_path, local_path)
            )
        )
        print('Download complete.')

    def put_save(self, local_path: str) -> None:
        print('Uploading save...')
        subprocess.check_output(
            shlex.split(
                'aws s3 sync %s %s --delete' % (local_path, self._s3_path)
            )
        )
        print('Upload complete.')

    @property
    def _s3_path(self) -> str:
        return 's3://%s/%s' % (
            self.env.str('AWS_S3_BUCKET'), self.env.str('AWS_S3_SAVE_KEY')
        )

    def kill_instance(self) -> None:
        # TODO: Kill EC2 instance
        print('Killing EC2 instance unimplemented.')
