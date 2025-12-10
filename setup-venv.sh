#!/bin/bash
set -e

# DataWagon Setup Script - Runtime Installation (Non-Poetry)
# This script creates a standard Python virtual environment and installs
# DataWagon with runtime dependencies ONLY (no development tools).
# For development with full tooling, use Poetry: make setup-poetry

# Variables
VENV=".venv"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Utility functions for colored output
print_success() { printf '\033[0;32m✓\033[0m %s\n' "$1"; }
print_error() { printf '\033[0;31m✗\033[0m %s\n' "$1"; }
print_warning() { printf '\033[1;33m!\033[0m %s\n' "$1"; }
print_info() { printf '→ %s\n' "$1"; }

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    major=$(echo "$version" | cut -d'.' -f1)
    minor=$(echo "$version" | cut -d'.' -f2)

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 9 ]; }; then
        print_error "Python 3.9+ required (found: Python $version)"
        exit 1
    fi

    print_success "Python found: $(python3 --version)"
}

# Create virtual environment
create_venv() {
    if [ -d "$VENV" ]; then
        print_warning "Virtual environment already exists at $VENV"
        read -p "Remove and recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi

    print_info "Creating virtual environment at $VENV..."
    python3 -m venv "$VENV" || {
        print_error "Failed to create virtual environment"
        exit 1
    }
    print_success "Virtual environment created"
}

# Install dependencies
install_deps() {
    print_info "Upgrading pip..."
    "$VENV/bin/pip" install --upgrade pip --quiet || {
        print_error "Failed to upgrade pip"
        exit 1
    }

    print_info "Installing DataWagon and runtime dependencies..."
    "$VENV/bin/pip" install -e . --quiet || {
        print_error "Failed to install DataWagon"
        exit 1
    }

    print_success "Dependencies installed"
}

# Verify installation
verify_installation() {
    print_info "Verifying installation..."

    if ! "$VENV/bin/pip" show datawagon &> /dev/null; then
        print_error "DataWagon package not found in virtual environment"
        return 1
    fi

    if ! "$VENV/bin/python" -c "import datawagon" 2>/dev/null; then
        print_error "Failed to import datawagon module"
        return 1
    fi

    if ! "$VENV/bin/datawagon" --help &> /dev/null; then
        print_error "datawagon command exists but failed to run"
        return 1
    fi

    for pkg in click pandas pydantic google-cloud-storage; do
        if ! "$VENV/bin/pip" show "$pkg" &> /dev/null; then
            print_error "Required package '$pkg' not found"
            return 1
        fi
    done

    print_success "Installation verified successfully"
    return 0
}

# Check and create .env file
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            print_warning ".env file not found"
            print_info "Copying $ENV_EXAMPLE to $ENV_FILE"
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_warning "Please edit .env and configure your settings:"
            print_info "  - DW_CSV_SOURCE_DIR"
            print_info "  - DW_GCS_PROJECT_ID"
            print_info "  - DW_GCS_BUCKET"
        else
            print_warning ".env file not found and no .env.example to copy from"
        fi
    else
        print_success ".env file exists"
    fi
}

# Main function
main() {
    print_info "DataWagon Setup Script (Non-Poetry)"
    print_info "===================================="
    print_info ""

    check_python
    check_env_file
    create_venv
    install_deps

    if ! verify_installation; then
        print_error "Installation verification failed"
        print_info "Try: rm -rf .venv && ./setup-venv.sh"
        exit 1
    fi

    print_info ""
    print_success "Setup complete!"
    print_info ""
    print_info "Next steps:"
    print_info "  1. Edit .env with your configuration"
    print_info "  2. Activate: source .venv/bin/activate"
    print_info "  3. Run: datawagon --help"
    print_info ""
    print_info "Note: Runtime-only install (no dev tools)."
    print_info "For development, use Poetry: make setup-poetry"
}

main "$@"
