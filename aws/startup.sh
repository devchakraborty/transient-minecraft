#!/bin/bash

sudo yum update -y
sudo yum install -y docker git tmux
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft
docker build -t minecraft .
tmux new -s minecraft 'docker run -i minecraft'
