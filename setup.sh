#!/bin/bash
# Phone Free Desk - Setup Script

set -e

echo "=== Phone Free Desk Setup ==="
echo

# Check if running on Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Step 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "Step 2: Installing system dependencies..."
sudo apt install -y python3-pip python3-venv pigpio

# Enable and start pigpio
echo "Step 3: Enabling pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Add user to gpio group
echo "Step 4: Adding user to gpio group..."
sudo usermod -a -G gpio $USER

# Create virtual environment
echo "Step 5: Creating Python virtual environment..."
python3 -m venv venv

# Activate and install dependencies
echo "Step 6: Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create log file
echo "Step 7: Creating log file..."
sudo touch /var/log/phone-free-desk.log
sudo chown $USER:$USER /var/log/phone-free-desk.log

echo
echo "=== Setup Complete! ==="
echo
echo "Next steps:"
echo "1. Edit config/settings.yaml with your GPIO pins"
echo "2. Run calibration scripts:"
echo "   source venv/bin/activate"
echo "   python3 scripts/calibrate_arm.py"
echo "   python3 scripts/calibrate_zone.py"
echo "3. Test the system:"
echo "   cd src && python3 main.py"
echo "4. Install as service:"
echo "   sudo cp systemd/phone-free-desk.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable phone-free-desk"
echo "   sudo systemctl start phone-free-desk"
echo
echo "Note: You may need to log out and back in for group changes to take effect"
