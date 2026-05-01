#!/bin/bash
# Survey High-Frequency Data Quality Checks — macOS Launcher
# Double-click this file to start the app.

cd "$(dirname "$0")"

echo "================================================"
echo "  Survey HFC — Data Quality Checks"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3 from https://www.python.org and try again."
    read -p "Press Enter to close..."
    exit 1
fi

# Create virtual environment on first run
if [ ! -d "venv" ]; then
    echo "First run — setting up virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        read -p "Press Enter to close..."
        exit 1
    fi
fi

# Activate
source venv/bin/activate

# Install / update dependencies (silent unless error)
echo "Checking dependencies..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies."
    echo "Check your internet connection and try again."
    read -p "Press Enter to close..."
    exit 1
fi

echo ""
echo "Starting the app..."
echo "It will open in your browser at http://localhost:8501"
echo "To stop, close this window or press Ctrl+C."
echo ""

streamlit run app.py --server.headless false
