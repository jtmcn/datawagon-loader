#!/bin/bash


git switch --quiet main

git fetch --quiet

if ! git diff --quiet origin/main main; then

    git pull --quiet -r --autostash origin main

    python3 -m venv .venv
    source .venv/bin/activate 
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    python3 -m pip install . 
    echo "Updated"
else
    echo "No changes"

fi