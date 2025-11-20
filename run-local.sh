#!/bin/bash

# Local development runner

echo "Starting Lemonade Stand Simulator locally..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Run the application
echo ""
echo "=========================================="
echo "Server running at: http://localhost:8080"
echo "=========================================="
echo "Press Ctrl+C to stop"
echo ""

python main.py
