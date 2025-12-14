#!/bin/bash
set -e

# Variables
BRANCH="main"
VENV=".venv"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Utility functions for colored output
print_success() { printf '\033[0;32m✓\033[0m %s\n' "$1"; }
print_error() { printf '\033[0;31m✗\033[0m %s\n' "$1"; }
print_warning() { printf '\033[1;33m!\033[0m %s\n' "$1"; }
print_info() { printf '→ %s\n' "$1"; }

# Check if Poetry is installed
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed."
        print_info "Install Poetry: https://python-poetry.org/docs/#installation"
        exit 1
    fi
    print_success "Poetry found: $(poetry --version)"
}

# Check if poetry-plugin-export is installed
check_poetry_export_plugin() {
    if ! poetry self show plugins 2>/dev/null | grep -q "poetry-plugin-export"; then
        print_warning "poetry-plugin-export not found"
        print_info "Installing poetry-plugin-export..."
        poetry self add poetry-plugin-export || {
            print_error "Failed to install poetry-plugin-export"
            exit 1
        }
        print_success "poetry-plugin-export installed"
    fi
}

# Check and create .env file if needed
check_env_file() {
    # Verify .env.example exists (critical repo file)
    if [ ! -f "$ENV_EXAMPLE" ]; then
        print_error ".env.example not found in repository"
        print_error "Repository may be corrupted or incomplete"
        print_info "Try: git fetch origin && git reset --hard origin/main"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found"
        print_info "Copying $ENV_EXAMPLE to $ENV_FILE"
        cp "$ENV_EXAMPLE" "$ENV_FILE" || {
            print_error "Failed to copy .env.example to .env"
            exit 1
        }
        print_warning "Please edit .env and configure: DW_CSV_SOURCE_DIR, DW_GCS_PROJECT_ID, DW_GCS_BUCKET"
    else
        print_success ".env file exists"
    fi
}

# Update git repository
update_git() {
    print_info "Checking for git updates on $BRANCH..."

    # Switch to the branch silently
    git switch --quiet "$BRANCH" || {
        print_error "Failed to switch to branch $BRANCH"
        return 1
    }

    # Fetch any changes from origin silently
    git fetch --quiet || {
        print_warning "Failed to fetch from remote (continuing anyway)"
        return 1
    }

    # Check if there are any changes
    if ! git diff --quiet origin/"$BRANCH" "$BRANCH" 2>/dev/null; then
        print_info "Updates found, pulling changes..."

        # Check for uncommitted changes
        if ! git diff --quiet || ! git diff --cached --quiet; then
            print_warning "You have uncommitted changes"
            print_info "Git will temporarily stash them during the update"
            read -p "Continue? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Update cancelled"
                exit 0
            fi
        fi

        git pull --quiet -r --autostash origin "$BRANCH" || {
            print_error "Failed to pull from origin"
            exit 1
        }
        print_success "Git repository updated"
        return 0  # Return 0 to indicate updates were pulled
    else
        print_success "Repository is up to date"
        return 1  # Return 1 to indicate no updates
    fi
}

# Setup or update Python environment with Poetry
setup_python_env() {
    print_info "Setting up Python environment with Poetry..."

    # Configure Poetry to create virtualenv in project
    poetry config virtualenvs.in-project true

    # Check if poetry.lock exists
    if [ ! -f "poetry.lock" ]; then
        print_warning "poetry.lock not found, generating..."
        poetry lock || {
            print_error "Failed to generate poetry.lock"
            exit 1
        }
    fi

    # Install dependencies
    print_info "Installing dependencies with Poetry..."
    poetry install || {
        print_error "Failed to install dependencies"
        exit 1
    }

    print_success "Python environment ready"

    # Show activation instructions
    print_info ""
    print_info "To activate the virtual environment, run:"
    print_info "  source .venv/bin/activate"
    print_info ""
    print_info "Or run commands with Poetry:"
    print_info "  poetry run datawagon --help"
}

# Update requirements.txt from poetry.lock
update_requirements() {
    print_info "Generating requirements.txt from poetry.lock..."

    # shellcheck disable=SC2094
    {
        echo "# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY"
        echo "# Generated from poetry.lock using 'make requirements'"
        echo "# Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        echo ""
        poetry export --without-hashes -f requirements.txt
    } > requirements.txt || {
        print_error "Failed to generate requirements.txt"
        print_warning "Make sure poetry-plugin-export is installed"
        return 1
    }

    print_success "requirements.txt updated"
}

# Main function
main() {
    local git_updated=false

    print_info "DataWagon Update Script"
    print_info "======================="
    print_info ""

    # Step 1: Check prerequisites
    check_poetry
    check_poetry_export_plugin
    check_env_file

    # Step 2: Update git (if possible)
    if update_git; then
        git_updated=true
    fi

    print_info ""

    # Step 3: Setup/update Python environment
    # Always run if git was updated, or if .venv doesn't exist
    if [ "$git_updated" = true ] || [ ! -d "$VENV" ]; then
        setup_python_env
        update_requirements
    else
        print_info "No git updates and virtualenv exists"
        print_info "Run 'poetry install' manually to update dependencies"
    fi

    print_info ""
    print_success "Update complete!"

    # Show installed version
    if [ -d "$VENV" ] && [ -f "$VENV/bin/python" ]; then
        print_info ""
        print_info "Installed version:"
        "$VENV/bin/python" -c "import importlib.metadata; print('  DataWagon v' + importlib.metadata.version('datawagon'))" 2>/dev/null || {
            print_warning "Could not determine installed version"
        }
    fi
}

main "$@"
