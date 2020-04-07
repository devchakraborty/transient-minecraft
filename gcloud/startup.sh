#!/bin/bash

# Get deps
sudo apt update -y
sudo apt upgrade -y
sudo apt install -y default-jdk build-essential libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev zlib1g zlib1g-dev git tmux

# Get, build, and install Python 3.7
curl https://pyenv.run | bash
export PATH="/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv install 3.7.7
pyenv global 3.7.7

# Get Minecraft Python code
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft

# Get Python deps
python -m pip install poetry --user
python -m poetry install

# Run server in tmux
tmux new-session -d -s minecraft
tmux send-keys -t minecraft "python -m poetry run server --cloud gcloud" C-m
