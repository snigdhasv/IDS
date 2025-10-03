#!/bin/bash

# Install Missing Python Packages for IDS Pipeline
# Run this if you encounter import errors

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="/home/sujay/Programming/IDS/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Installing Missing Python Packages           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}✗ Virtual environment not found at: $VENV_PATH${NC}"
    echo -e "${YELLOW}Run: python3 -m venv $VENV_PATH${NC}"
    exit 1
fi

# Activate venv
echo -e "${BLUE}▶ Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to activate virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo

# Upgrade pip
echo -e "${BLUE}▶ Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel

# Install missing packages
echo
echo -e "${BLUE}▶ Installing missing packages...${NC}"
echo

# LightGBM (for LightGBM model support)
echo -e "${YELLOW}Installing LightGBM...${NC}"
pip install lightgbm

# XGBoost (optional, for future models)
echo -e "${YELLOW}Installing XGBoost...${NC}"
pip install xgboost

# Ensure all base requirements are met
echo
echo -e "${BLUE}▶ Verifying core packages...${NC}"
pip install --upgrade \
    kafka-python \
    pandas \
    numpy \
    scikit-learn \
    joblib \
    pyyaml \
    psutil

# Additional useful packages
echo
echo -e "${BLUE}▶ Installing additional utilities...${NC}"
pip install \
    matplotlib \
    seaborn \
    tqdm \
    colorama

# Verify installation
echo
echo -e "${BLUE}▶ Verification...${NC}"
echo -e "${BLUE}$(printf '─%.0s' {1..50})${NC}"

python << 'EOF'
import sys

packages = [
    ('kafka', 'kafka-python', 'Kafka client'),
    ('pandas', 'pandas', 'Data processing'),
    ('numpy', 'numpy', 'Numerical computing'),
    ('sklearn', 'scikit-learn', 'ML library'),
    ('joblib', 'joblib', 'Model persistence'),
    ('lightgbm', 'lightgbm', 'LightGBM models'),
    ('xgboost', 'xgboost', 'XGBoost models'),
    ('yaml', 'pyyaml', 'YAML config'),
    ('psutil', 'psutil', 'System monitoring'),
]

all_ok = True
for module, package, description in packages:
    try:
        __import__(module)
        print(f"✅ {description:20} ({package})")
    except ImportError:
        print(f"❌ {description:20} ({package}) - MISSING")
        all_ok = False

if all_ok:
    print("\n✅ All packages installed successfully!")
    sys.exit(0)
else:
    print("\n❌ Some packages failed to install")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Installation Complete!                     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "You can now run the ML consumer:"
    echo -e "${BLUE}python src/ml_kafka_consumer.py --config config/pipeline.conf${NC}"
else
    echo
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  Some packages failed to install          ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "Try installing manually:"
    echo -e "${YELLOW}source $VENV_PATH/bin/activate${NC}"
    echo -e "${YELLOW}pip install lightgbm xgboost${NC}"
fi
