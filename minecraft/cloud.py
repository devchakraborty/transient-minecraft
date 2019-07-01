import subprocess
import shlex
import os
import json
import time

from abc import ABC, abstractmethod, abstractstaticmethod
from typing import Optional, Dict, Any

from environs import Env


class Cloud(ABC):
    """
    Represents an interface to a cloud service for storage and server hosting
    """

    def __init__(self) -> None:
        self.env = Env()
        self.env.read_env()

    @abstractstaticmethod
    def create_instance() -> None:
        """
        Creates a new cloud instance running a Minecraft server. Assumed to be
        running on a computer with the AWS CLI installed and authenticated.
        """
        raise NotImplementedError()

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
        """
        Kills the current cloud instance running a Minecraft server
        """
        raise NotImplementedError()


class AWSCloud(Cloud):
    """
    An interface to AWS for world storage via S3 and server hosting via EC2
    """

    DEFAULT_REGION = 'us-west-1'
    IMAGE_ID = 'ami-056ee704806822732'  # Amazon Linux 2
    INSTANCE_TYPE = 't2.micro'
    KEY_NAME = 'id_aws'
    SECURITY_GROUP = 'minecraft'

    def __init__(self, needs_auth=False, needs_storage=True) -> None:
        super(AWSCloud, self).__init__()

        if needs_auth:
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

        if needs_storage:
            # Check accessibility of these mandatory env vars upfront
            self.env.str('AWS_S3_BUCKET')
            self.env.str('AWS_S3_SAVE_KEY')

    @staticmethod
    def create_instance() -> None:
        # Create an instance
        command = (
            'python -m awscli ec2 run-instances --image-id %s '
            '--instance-type %s --user-data file://aws/startup.sh '
            '--instance-initiated-shutdown-behavior terminate --key-name %s'
            '--security-groups %s'
        ) % (
            AWSCloud.IMAGE_ID, AWSCloud.INSTANCE_TYPE, AWSCloud.KEY_NAME,
            AWSCloud.SECURITY_GROUP
        )
        result = json.loads(subprocess.check_output(shlex.split(command)))
        instance_id = result['Instances'][0]['InstanceId']

        # Poll for the public IP until the instance has one
        public_ip = None
        while public_ip is None:
            instances_result = json.loads(
                subprocess.check_output(
                    shlex.split('python -m awscli ec2 describe-instances')
                )
            )
            instance_result = [
                reservation['Instances'][0]
                for reservation in instances_result['Reservations']
                if reservation['Instances'][0]['InstanceId'] == instance_id
            ]
            if len(instance_result) == 0:
                raise Exception('Lost instance %s' % instance_id)
            instance_result = instance_result[0]

            public_ip = instance_result.get('PublicIpAddress')
            if public_ip is None:
                time.sleep(1)

        print('Minecraft server launched on AWS.')
        print('Instance ID: %s' % instance_id)
        print('IP: %s' % public_ip)

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
        # By starting the instance with shutdown behavior = termination, we
        # simply need to shut down the instance
        subprocess.check_output(shlex.split('sudo shutdown now'))
