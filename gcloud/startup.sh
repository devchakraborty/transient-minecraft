#!/bin/bash

# Get deps
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y build-essential libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev zlib1g zlib1g-dev git tmux

# Get, build, and install Python 3.7
wget https://www.python.org/ftp/python/3.7.7/Python-3.7.7.tgz
tar -xzvf Python-3.7.7.tgz
pushd Python-3.7.7
./configure
make
sudo make altinstall
popd

# Get Minecraft Python code
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft

# Get Python deps
python3.7 -m pip install poetry --user
python3.7 -m poetry install

# Run server in tmux
tmux new-session "python3.7 -m poetry run server --cloud gcloud"
