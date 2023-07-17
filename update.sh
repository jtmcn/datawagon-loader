#!/bin/bash
set -e

# Variables
BRANCH="main"
VENV=".venv"

# This script will check for updates on the main branch of the specified repository
# If changes are found, it will pull the changes and update the Python environment
# It assumes the Python virtual environment and the branch are already set

function update_git() {
    # Switch to the branch silently
    git switch --quiet "$BRANCH"

    # Fetch any changes from origin silently
    git fetch --quiet

    if ! git diff --quiet origin/"$BRANCH" "$BRANCH"; then
        git pull --quiet -r --autostash origin "$BRANCH" || {
            echo "Failed to pull from origin. Exiting."
            exit 1
        }
        return 0;
    else
        echo "No changes"
        return 1;
    fi
}

function update_python_env() {
    # Check if virtual environment exists, if not, create it 
    if [ ! -d "$VENV" ]; then
        python3 -m venv "$VENV"
    fi

    # Activate the virtual environment
    source "$VENV"/bin/activate 
    
    # Make sure we're operating with the virtualenv python and pip
    PYTHON="$VENV/bin/python"
    PIP="$VENV/bin/pip"

    # Upgrade pip and install requirements
    "$PYTHON" -m pip install --upgrade pip
    
    "$PIP" install -r requirements.txt
    "$PIP" install . 

    echo "Python environment updated"
}

function main() {
    if update_git; then
        update_python_env
    fi
}

main "$@"
