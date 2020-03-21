#!/bin/bash

sudo yum update -y
sudo amazon-linux-extras install docker
sudo yum install -y git tmux
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft
sudo service docker start
sudo gpasswd -a $USER docker
newgrp docker
docker build -t minecraft .
docker run -i minecraft
