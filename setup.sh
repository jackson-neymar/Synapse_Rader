#!/bin/bash
set -e
echo "=== Synapse_Rader Setup ==="

# Check Python
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0")
echo "Python: $PYVER"
if [ "$(echo "$PYVER >= 3.10" | bc)" != "1" ]; then
    echo "ERROR: Python 3.10+ required. On Ubuntu 20.04, install via:"
    echo "  sudo add-apt-repository ppa:deadsnakes/ppa"
    echo "  sudo apt install python3.10 python3.10-venv"
    exit 1
fi

# Check Node
NODEVER=$(node -v 2>/dev/null | tr -d 'v' || echo "0")
echo "Node: $NODEVER"
if [ "$(echo "$NODEVER >= 18" | bc 2>/dev/null)" != "1" ]; then
    echo "ERROR: Node.js 18+ required"
    exit 1
fi

# Create data dirs
mkdir -p data logs config

# Copy .env if not exists
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo ".env created from .env.example — please edit with real credentials"
fi

# Install deps
echo "Installing Python dependencies..."
cd backend && pip install -r requirements.txt -q && cd ..
echo "Installing Node dependencies..."
cd frontend && npm install --silent && cd ..

# Init database
echo "Initializing database..."
cd backend && python init_db.py && cd ..

echo ""
echo "Setup complete!"
echo "  Run ./start.sh to launch the application"
