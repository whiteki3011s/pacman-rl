#!/bin/bash

# ==============================================================================
# Pac-Man RL — Development Server & Vite Launcher
# ==============================================================================
# - In Finder: Double-click `start.command` to open Terminal and launch Vite.
# - In Terminal: Run `./start.command` or `./start_dev.sh`.
# Automatically ensures dependencies, frees port 5173, starts Vite, and
# opens your default browser at http://localhost:5173.
# ==============================================================================

# Ensure standard macOS tool paths are available (Homebrew, NVM, standard bin)
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node 2>/dev/null | tail -n 1)/bin:$PATH"

# Navigate to the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo ""
echo "=========================================================="
echo "   🟡  PAC-MAN RL — DEEP REINFORCEMENT LEARNING LAB"
echo "=========================================================="
echo "  Starting Vite Development Server..."
echo "  Project Root: $SCRIPT_DIR"
echo "=========================================================="
echo ""

# Verify Node.js and npm are installed
if ! command -v node >/dev/null 2>&1; then
    echo "❌ Error: Node.js is not found in PATH."
    echo "   Please install Node.js from https://nodejs.org or via Homebrew: brew install node"
    read -p "Press Enter to exit..."
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "❌ Error: npm is not found."
    read -p "Press Enter to exit..."
    exit 1
fi

# Ensure node_modules exist
if [ ! -d "web/node_modules" ]; then
    echo "📦 Dependencies not found in web/. Installing npm packages..."
    npm --prefix web install || {
        echo "❌ npm install failed."
        read -p "Press Enter to exit..."
        exit 1
    }
fi

# Free port 5173 if a stale dev server is currently hanging on it
STALE_PIDS=$(lsof -ti :5173 2>/dev/null)
if [ -n "$STALE_PIDS" ]; then
    echo "🔄 Freeing port 5173 from previous session (PID: $STALE_PIDS)..."
    kill -9 $STALE_PIDS 2>/dev/null
    sleep 0.5
fi

# Function to auto-open browser once Vite is ready
(
    for i in {1..30}; do
        sleep 0.5
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 | grep -q "200\|304"; then
            echo ""
            echo "🚀 Server is live at http://localhost:5173! Opening your browser..."
            open "http://localhost:5173"
            break
        fi
    done
) &

echo "⚡ Launching Vite dev server on port 5173..."
echo "   Press [Ctrl + C] in this window to stop the server."
echo ""

# Start the Vite development server
exec npm --prefix web run dev
