#!/bin/bash
set -e

# Variables
BRANCH="main"
VENV=".venv"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Utility functions for colored output
print_success() { echo -e "\033[0;32m✓\033[0m $1"; }
print_error() { echo -e "\033[0;31m✗\033[0m $1"; }
print_warning() { echo -e "\033[1;33m!\033[0m $1"; }
print_info() { echo -e "→ $1"; }

# Check virtual environment exists
check_venv() {
    if [ ! -d "$VENV" ]; then
        print_error "Virtual environment not found at $VENV"
        print_info "Run ./setup-venv.sh first"
        exit 1
    fi
    print_success "Virtual environment found"
}

# Update git repository
update_git() {
    print_info "Checking for git updates on $BRANCH..."

    git switch --quiet "$BRANCH" || {
        print_error "Failed to switch to branch $BRANCH"
        return 1
    }

    git fetch --quiet || {
        print_warning "Failed to fetch from remote (continuing anyway)"
        return 1
    }

    if ! git diff --quiet origin/"$BRANCH" "$BRANCH" 2>/dev/null; then
        print_info "Updates found, pulling changes..."
        git pull --quiet -r --autostash origin "$BRANCH" || {
            print_error "Failed to pull from origin"
            exit 1
        }
        print_success "Git repository updated"
        return 0
    else
        print_success "Repository is up to date"
        return 1
    fi
}

# Update Python dependencies
update_deps() {
    print_info "Updating dependencies..."

    "$VENV/bin/pip" install --upgrade pip --quiet

    print_info "Upgrading DataWagon..."
    "$VENV/bin/pip" install -e . --upgrade --quiet || {
        print_error "Failed to upgrade DataWagon"
        exit 1
    }

    if [ -f "requirements-dev.txt" ]; then
        print_info "Upgrading dev dependencies..."
        "$VENV/bin/pip" install -r requirements-dev.txt --upgrade --quiet || {
            print_warning "Failed to upgrade some dev dependencies"
        }
    fi

    print_success "Dependencies updated"
}

# Check .env file
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            print_warning ".env file not found"
            print_info "Copying $ENV_EXAMPLE to $ENV_FILE"
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_warning "Please edit .env with your configuration"
        fi
    else
        print_success ".env file exists"
    fi
}

# Main function
main() {
    local git_updated=false

    print_info "DataWagon Update Script (Non-Poetry)"
    print_info "====================================="
    print_info ""

    check_venv
    check_env_file

    if update_git; then
        git_updated=true
    fi

    print_info ""

    if [ "$git_updated" = true ]; then
        update_deps
    else
        print_info "No git updates"
        print_info "Run '$VENV/bin/pip install -e . --upgrade' to update anyway"
    fi

    print_info ""
    print_success "Update complete!"
}

main "$@"
