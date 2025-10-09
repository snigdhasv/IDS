#!/bin/bash
# Script to activate the virtual environment for IDS project

echo "Activating IDS virtual environment..."
source venv/bin/activate

echo "Virtual environment activated!"
echo "Python version: $(python --version)"
echo ""
echo "To deactivate, run: deactivate"
echo ""
echo "Virtual environment is ready. You can now run your IDS scripts."
