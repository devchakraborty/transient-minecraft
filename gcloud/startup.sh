#!/bin/bash

sudo apt update -y
sudo apt upgrade -y
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg2
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
sudo apt update -y
sudo apt install -y docker-ce git tmux
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft
docker build -t minecraft .
docker run -i minecraft
