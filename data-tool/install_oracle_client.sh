#!/bin/bash

set -e

# Replace with your shell config file
SHELL_RC="$HOME/.bash_profile"

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS"

    if ! command -v brew &> /dev/null; then
        echo "👷 Homebrew not found, installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "🍺 Homebrew is already installed."
    fi
  
    # Install Oracle Instant Client via Homebrew
    brew tap InstantClientTap/instantclient
    brew install instantclient-basic

    INSTANT_CLIENT_DIR=$(brew --prefix instantclient-basic)
    LIB_DIR="$INSTANT_CLIENT_DIR/lib"

    # Write into environment variable
    if ! grep -q "$INSTANT_CLIENT_DIR" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# Oracle Instant Client config" >> "$SHELL_RC"
        echo "export DYLD_LIBRARY_PATH=\"$LIB_DIR:\$DYLD_LIBRARY_PATH\"" >> "$SHELL_RC"
        echo "export PATH=\"$INSTANT_CLIENT_DIR:\$PATH\"" >> "$SHELL_RC"
        echo "✅ Oracle Instant Client config added to $SHELL_RC"
    else
        echo "✅ Oracle Instant Client config already set in $SHELL_RC, skipping."
    fi

    echo "🎉 Oracle Instant Client installed at: $INSTANT_CLIENT_DIR"
    echo "🎉 Please run this to apply environment variable:"
    echo "    source $SHELL_RC"

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux"

    DIR_NAME="instantclient_21_1"
    ARCHIVE_NAME="instantclient-basiclite-linux.x64-21.1.0.0.0.zip"
    BASIC_URL="https://download.oracle.com/otn_software/linux/instantclient/211000/$ARCHIVE_NAME"
    INSTANT_CLIENT_DIR="$HOME/oracle/$DIR_NAME"
  
    # Install dependencies
    echo "Updating & installing dependencies..."
    sudo apt update && sudo apt install -y libaio1 unzip wget

    mkdir -p "$HOME/oracle"
    cd "$HOME/oracle"

    # Download & Unzip
    if [ ! -d "$INSTANT_CLIENT_DIR" ]; then
        echo "👷 Downloading Oracle Instant Client..."
        wget "$BASIC_URL"
        echo "👷 Unzipping..."
        unzip -o "$ARCHIVE_NAME"
        rm -f "$ARCHIVE_NAME"
    else
        echo "✅ Instant Client already exists at $INSTANT_CLIENT_DIR, skipping download."
    fi

    # Write into environment variable
    if ! grep -q "$INSTANT_CLIENT_DIR" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# Oracle Instant Client config" >> "$SHELL_RC"
        echo "export LD_LIBRARY_PATH=\"$INSTANT_CLIENT_DIR:\$LD_LIBRARY_PATH\"" >> "$SHELL_RC"
        echo "export PATH=\"$INSTANT_CLIENT_DIR:\$PATH\"" >> "$SHELL_RC"
        echo "✅ Oracle Instant Client config added to $SHELL_RC"
    else
        echo "✅ Oracle Instant Client config already set in $SHELL_RC, skipping."
    fi

    echo "🎉 Oracle Instant Client installed at: $INSTANT_CLIENT_DIR"
    echo "🎉 Please run this to apply environment variable:"
    echo "    source $SHELL_RC"
  
else
  echo "Unsupported OS: $OSTYPE"
  exit 1
fi
