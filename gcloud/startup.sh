#!/bin/bash

sudo apt update -y
sudo apt upgrade -y
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg2
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update -y
sudo apt install -y git python3.7 tmux
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft
python3.7 -m pip install poetry
python3.7 -m poetry install
tmux new-session "python3.7 -m poetry run server --cloud gcloud"
