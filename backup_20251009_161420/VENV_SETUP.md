# Virtual Environment Setup for IDS Project

## Overview
This project uses a Python virtual environment to isolate dependencies and avoid conflicts with system packages.

## Quick Start

### Activate the virtual environment:
```bash
source venv/bin/activate
# or use the helper script:
source activate_venv.sh
```

### Deactivate when done:
```bash
deactivate
```

## Initial Setup (Already Completed)

The virtual environment has already been set up with the following steps:

1. **Installed required system packages:**
   - python3.12-venv
   - build-essential
   - pkg-config
   - python3-dev
   - libnuma-dev
   - libpcap-dev
   - And other development dependencies

2. **Created virtual environment:**
   ```bash
   python3 -m venv venv
   ```

3. **Installed Python packages:**
   ```bash
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Installed Packages

Key packages installed in the virtual environment:
- **Core:** numpy, pandas, scikit-learn, psutil
- **ML/AI:** tensorflow, torch, keras
- **Networking:** scapy, pyshark, kafka-python
- **Development:** pytest, black, flake8, mypy
- **Monitoring:** prometheus-client, structlog

## Usage

Always activate the virtual environment before running any Python scripts:

```bash
source venv/bin/activate
python src/basic_dpdk_test.py
# or any other script
```

## Troubleshooting

### If you see "externally-managed-environment" error:
This means you're trying to install packages to system Python. Always activate the virtual environment first.

### If the virtual environment is corrupted:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Notes

- The virtual environment directory (`venv/`) is already in `.gitignore` and won't be committed to version control
- Each user needs to create their own virtual environment
- System-wide packages won't interfere with project dependencies
