#!/bin/bash

# Install Docker
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Get Minecraft Python code
git clone https://github.com/devchakraborty/transient-minecraft.git
cd transient-minecraft

# Build Docker image
docker build . -t minecraft

# Run docker container
docker run -d -p 25565:25565 -t minecraft

# sudo apt install -y default-jdk build-essential libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev zlib1g zlib1g-dev git tmux

# # Get pyenv and set up environment
# git clone https://github.com/pyenv/pyenv.git ~/.pyenv

# # Run setup commands in future bash sessions
# cat >> ~/.bashrc << EOF

# # pyenv setup
# export PYENV_ROOT="\$HOME/.pyenv"
# export PATH="\$PYENV_ROOT/bin:$PATH"
# eval "\$(pyenv init -)"

# EOF

# # Set up pyenv in this session
# export PYENV_ROOT="$HOME/.pyenv"
# export PATH="$PYENV_ROOT/bin:$PATH"
# eval "$(~/.pyenv/bin/pyenv init -)"

# # Build and install Python 3.7
# ~/.pyenv/bin/pyenv install 3.7.7
# ~/.pyenv/bin/pyenv global 3.7.7

# # Get Minecraft Python code
# git clone https://github.com/devchakraborty/transient-minecraft.git
# cd transient-minecraft

# # Get Python deps
# python -m pip install poetry --user
# python -m poetry install

# # Run server in tmux
# tmux new-session -d -s minecraft
# tmux send-keys -t minecraft "python -m poetry run server --cloud gcloud" C-m
