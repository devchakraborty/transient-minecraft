#!/bin/bash

sudo apt update -y
sudo apt install -y docker git tmux
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft
sudo service docker start
sudo gpasswd -a $USER docker
newgrp docker
docker build -t minecraft .
docker run -i minecraft
