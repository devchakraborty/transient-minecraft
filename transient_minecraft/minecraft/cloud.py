import base64
import datetime
import json
import os
import pathlib
import pdb
import requests
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile

from abc import ABC, abstractmethod, abstractproperty
from typing import Optional, Dict, Any, Sequence
from collections import deque

import googleapiclient as google
import googleapiclient.discovery
from google.cloud import storage
from dotenv import load_dotenv


class Cloud(ABC):
    """
    Represents an interface to a cloud service for storage and server hosting
    """

    def __init__(self) -> None:
        load_dotenv()

        for env_var in self.required_env_vars:
            assert env_var in os.environ

    @abstractmethod
    def create_instance(self) -> None:
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

    @abstractproperty
    def required_env_vars(self) -> Sequence[str]:
        """
        Returns the env vars that must be set to run this cloud.
        """
        raise NotImplementedError()

    @abstractproperty
    def startup_script(self) -> str:
        """
        Returns the startup script to run on new instances.
        """
        raise NotImplementedError()

    def get_env_startup_script(self) -> str:
        """
        Returns the startup script to run on new instances, including environment
        variables copied from the current environment.
        """
        # Generate a line of bash code that writes env vars to a .env file
        env_var_assignments = "".join(
            f'{env_var}="{os.environ[env_var]}"\n' for env_var in self.required_env_vars
        )
        encoded_assignments = base64.b64encode(
            env_var_assignments.encode("utf-8")
        ).decode("ascii")
        env_file_line = f"echo '{encoded_assignments}' | base64 -d > .env"

        # Insert this line of code in the startup script right after
        # "cd transient-minecraft"
        startup_script_lines = self.startup_script.strip().splitlines()
        cd_idx = startup_script_lines.index("cd transient-minecraft")
        new_script_lines = (
            startup_script_lines[: cd_idx + 1]
            + [env_file_line]
            + startup_script_lines[cd_idx + 1 :]
        )

        return "".join(f"{line}\n" for line in new_script_lines)

    def get_timestamp(self) -> str:
        """
        Returns a timestamp for use in save filenames.
        """
        return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


class GCloud(Cloud):
    """
    An interface to Google Cloud for world storage and server hosting
    """

    SHORT_NAME = "gcloud"

    def __init__(self) -> None:
        super(GCloud, self).__init__()

        self.compute = google.discovery.build("compute", "v1")
        self.storage_client = storage.Client()

    @property
    def required_env_vars(self) -> Sequence[str]:
        return [
            "GCLOUD_ZONE",  # e.g., us-west1-a
            "GCLOUD_MACHINE_TYPE",  # e.g., e2-standard-2
            "GCLOUD_PROJECT_ID",
            "GCLOUD_BUCKET",
            "GCLOUD_FIREWALL_TAG",
        ]

    @property
    def startup_script(self) -> str:
        with open("gcloud/startup.sh", "r") as startup_script:
            return startup_script.read()

    def create_instance(self) -> None:
        # Get the latest Debian image
        image_response = (
            self.compute.images()
            .getFromFamily(project="debian-cloud", family="debian-9")
            .execute()
        )
        source_disk_image = image_response["selfLink"]

        # Configure the instance
        zone = os.environ["GCLOUD_ZONE"]
        machine_type = os.environ["GCLOUD_MACHINE_TYPE"]
        instance_name = f"mc-server-{uuid.uuid4()}"
        config = {
            "name": instance_name,
            "machineType": f"zones/{zone}/machineTypes/{machine_type}",
            "disks": [
                {
                    "boot": True,
                    "autoDelete": True,
                    "initializeParams": {"sourceImage": source_disk_image,},
                }
            ],
            "networkInterfaces": [
                {
                    "network": "global/networks/default",
                    "accessConfigs": [
                        {"type": "ONE_TO_ONE_NAT", "name": "External NAT"}
                    ],
                }
            ],
            "metadata": {
                "items": [
                    {"key": "startup-script", "value": self.get_env_startup_script()}
                ]
            },
            "serviceAccounts": [
                {
                    "email": "default",
                    "scopes": [
                        "https://www.googleapis.com/auth/devstorage.read_write",
                        "https://www.googleapis.com/auth/logging.write",
                        "https://www.googleapis.com/auth/compute",
                    ],
                }
            ],
            "tags": {"items": [os.environ["GCLOUD_FIREWALL_TAG"]]},
        }

        if "GCLOUD_IP" in os.environ:
            config["networkInterfaces"][0]["accessConfigs"][0]["natIP"] = os.environ[
                "GCLOUD_IP"
            ]

        # Create the instance
        project = os.environ["GCLOUD_PROJECT_ID"]
        create_result = (
            self.compute.instances()
            .insert(project=project, zone=zone, body=config)
            .execute()
        )

        print("Creating instance...")

        # Poll the operation until it is complete
        while True:
            poll_result = (
                self.compute.zoneOperations()
                .get(operation=create_result["id"], project=project, zone=zone)
                .execute()
            )

            if poll_result["status"] == "DONE":
                if "error" in poll_result:
                    raise Exception(poll_result["error"])
                break

            time.sleep(1)

        # Get the IP information from the created instance
        instance_result = (
            self.compute.instances()
            .get(instance=poll_result["targetId"], project=project, zone=zone)
            .execute()
        )
        instance_ip = instance_result["networkInterfaces"][0]["accessConfigs"][0][
            "natIP"
        ]

        print(f"Successfully created instance '{instance_name}' on Google Cloud.")
        print(f"IP: {instance_ip}")

    def get_save(self, local_path: str) -> None:
        blobs = list(
            self.storage_client.list_blobs(bucket_or_name=os.environ["GCLOUD_BUCKET"])
        )
        if len(blobs) == 0:
            print("No existing save!")
            return
        latest_blob = sorted(blobs, key=lambda b: b.name)[-1]
        print(f"Downloading save: {latest_blob.name}")
        zipped_save_file = tempfile.NamedTemporaryFile(delete=False)
        zipped_save_file.close()
        latest_blob.download_to_filename(zipped_save_file.name)
        print(f"Downloaded save: {latest_blob.name}")
        print(f"Extracting save: {latest_blob.name}")
        with zipfile.ZipFile(zipped_save_file.name, "r") as zip_file:
            zip_file.extractall(local_path)
        print(f"Extracted save: {latest_blob.name}")

    def put_save(self, local_path: str) -> None:
        bucket = self.storage_client.bucket(os.environ["GCLOUD_BUCKET"])
        blob_name = self.get_timestamp()
        blob = bucket.blob(blob_name)
        zipped_save_file = tempfile.NamedTemporaryFile(delete=False)
        zipped_save_file.close()
        print(f"Compressing save: {blob_name}")
        shutil.make_archive(zipped_save_file.name, "zip", local_path)
        print(f"Compressed save: {blob_name}")
        print(f"Uploading save: {blob_name}")
        blob.upload_from_filename(f"{zipped_save_file.name}.zip")
        print(f"Uploaded save: {blob_name}")

    def kill_instance(self) -> None:
        project = os.environ["GCLOUD_PROJECT_ID"]
        zone = os.environ["GCLOUD_ZONE"]
        # Get the instance name from the Goole Cloud Metadata server
        instance_name = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/name",
            headers={"Metadata-Flavor": "Google"},
        ).text
        print(f"Deleting instance {instance_name} in {zone}")
        self.compute.instances().delete(
            project=project, zone=zone, instance=instance_name
        ).execute()


class AWSCloud(Cloud):
    """
    An interface to AWS for world storage via S3 and server hosting via EC2
    """

    SHORT_NAME = "aws"
    DEFAULT_REGION = "us-west-1"
    IMAGE_ID = "ami-056ee704806822732"  # Amazon Linux 2
    INSTANCE_TYPE = "t2.micro"
    KEY_NAME = "id_aws"
    SECURITY_GROUP = "minecraft"

    def __init__(self, needs_auth=False, needs_storage=True) -> None:
        super(AWSCloud, self).__init__()

        self.needs_auth = needs_auth
        self.needs_storage = needs_storage

        if needs_auth:
            # AWS CLI initial configuration - using AWS CLI for sync command
            aws_commands = [
                "aws configure set aws_access_key_id %s"
                % os.environ["AWS_ACCESS_KEY_ID"],
                "aws configure set aws_secret_access_key %s"
                % os.environ["AWS_SECRET_ACCESS_KEY"],
                "aws configure set region %s"
                % os.environ.get("AWS_REGION", AWSCloud.DEFAULT_REGION),
            ]

            for command in aws_commands:
                subprocess.check_output(shlex.split(command))

    @property
    def required_env_vars(self) -> Sequence[str]:
        env_vars = []
        if self.needs_auth:
            env_vars += ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]
        if self.needs_storage:
            env_vars += ["AWS_S3_BUCKET", "AWS_S3_SAVE_KEY"]
        return env_vars

    def create_instance(self) -> None:
        # Create an instance

        startup_script = self.env_startup_script()
        print(startup_script)
        with tempfile.TemporaryFile(mode="w", delete=False) as startup_script_file:
            startup_script_file.write(startup_script)

        startup_script_uri = (
            pathlib.PurePath(startup_script_file.name)
            .as_uri()
            .replace("file:///", "file://")
        )

        command = (
            "python -m awscli ec2 run-instances --image-id %s "
            "--instance-type %s --user-data %s "
            "--instance-initiated-shutdown-behavior terminate --key-name %s "
            "--security-groups %s"
        ) % (
            AWSCloud.IMAGE_ID,
            AWSCloud.INSTANCE_TYPE,
            startup_script_uri,
            AWSCloud.KEY_NAME,
            AWSCloud.SECURITY_GROUP,
        )
        result = json.loads(subprocess.check_output(shlex.split(command)))

        os.remove(startup_script_file.name)

        instance_id = result["Instances"][0]["InstanceId"]

        # Poll for the public IP until the instance has one
        public_ip = None
        while public_ip is None:
            instances_result = json.loads(
                subprocess.check_output(
                    shlex.split("python -m awscli ec2 describe-instances")
                )
            )
            instance_result = [
                reservation["Instances"][0]
                for reservation in instances_result["Reservations"]
                if reservation["Instances"][0]["InstanceId"] == instance_id
            ]
            if len(instance_result) == 0:
                raise Exception("Lost instance %s" % instance_id)
            instance_result = instance_result[0]

            public_ip = instance_result.get("PublicIpAddress")
            if public_ip is None:
                time.sleep(1)

        print("Minecraft server launched on AWS.")
        print("Instance ID: %s" % instance_id)
        print("IP: %s" % public_ip)

    @property
    def startup_script(self) -> str:
        with open("aws/startup.sh") as startup_script:
            return startup_script.read()

    def get_save(self, local_path: str) -> None:
        print("Downloading save...")
        subprocess.check_output(
            shlex.split("aws s3 sync %s %s --delete" % (self._s3_path, local_path))
        )
        print("Download complete.")

    def put_save(self, local_path: str) -> None:
        print("Uploading save...")
        subprocess.check_output(
            shlex.split("aws s3 sync %s %s --delete" % (local_path, self._s3_path))
        )
        print("Upload complete.")

    @property
    def _s3_path(self) -> str:
        return "s3://%s/%s" % (
            os.environ["AWS_S3_BUCKET"],
            os.environ["AWS_S3_SAVE_KEY"],
        )

    def kill_instance(self) -> None:
        # By starting the instance with shutdown behavior = termination, we
        # simply need to shut down the instance
        subprocess.check_output(shlex.split("sudo shutdown now"))
