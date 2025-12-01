# Phone Free Desk

A Raspberry Pi 5 project that uses computer vision and robotics to spray you with water when you reach for your phone during Do Not Disturb mode.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi 5                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Web API    │    │   Vision     │    │    Hardware      │  │
│  │   (FastAPI)  │    │   Detector   │    │    Controller    │  │
│  │              │    │  (MediaPipe) │    │     (GPIO)       │  │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘  │
│         │                   │                     │             │
│         └───────────┬───────┴─────────────────────┘             │
│                     │                                           │
│              ┌──────▼───────┐                                   │
│              │ Orchestrator │                                   │
│              │   (Main)     │                                   │
│              └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
         ▲                              │
         │ HTTP POST                    │ GPIO
         │ /dnd                         ▼
┌────────┴────────┐           ┌─────────────────┐
│  Android App    │           │  Servos + Pump  │
│  (separate)     │           │                 │
└─────────────────┘           └─────────────────┘
```

## Components

### 1. Web API (`src/api/`)
- FastAPI server with endpoints for DND status
- `POST /dnd` - Set DND status from Android app
- `GET /dnd` - Get current DND status
- `GET /health` - Health check

### 2. Vision Detector (`src/vision/`)
- MediaPipe Hands for real-time hand detection
- Configurable detection zone for phone area
- Runs at 10 FPS with Logitech C270 webcam

### 3. Hardware Controller (`src/hardware/`)
- 2-DOF robotic arm with servo motors
- Water pump control via GPIO relay
- Coordinated spray sequence

### 4. Orchestrator (`src/core/`)
- Main control loop
- Coordinates vision detection with spray activation
- 10-second cooldown between sprays
- Requires multiple consecutive detections to trigger

## Hardware Requirements

- Raspberry Pi 5
- Logitech C270 USB webcam
- 2x SG90 servo motors (or similar)
- 1x DC water pump
- 1x Relay module (for pump)
- Power supply for servos and pump
- Robotic arm frame/structure

## Installation

### 1. System Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv git

# Install and enable pigpio for better PWM control
sudo apt install -y pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### 2. Clone and Setup Project

```bash
cd /home/pi
git clone <your-repo-url> phone-free-desk
cd phone-free-desk

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configuration

Edit `config/settings.yaml` to match your hardware setup:

```yaml
gpio:
  servo_1: 17  # Your GPIO pin for servo 1
  servo_2: 18  # Your GPIO pin for servo 2
  pump: 23     # Your GPIO pin for pump relay
```

### 4. Calibration

#### Calibrate Arm Positions

```bash
source venv/bin/activate
python3 scripts/calibrate_arm.py
```

This interactive script lets you find the correct servo angles for rest and spray positions.

#### Calibrate Detection Zone

```bash
source venv/bin/activate
python3 scripts/calibrate_zone.py
```

This shows the camera feed and lets you draw a box around where your phone sits.

### 5. Test Run

```bash
source venv/bin/activate
cd src
python3 main.py
```

### 6. Install as System Service

```bash
sudo cp systemd/phone-free-desk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable phone-free-desk
sudo systemctl start phone-free-desk
```

Check status:
```bash
sudo systemctl status phone-free-desk
```

View logs:
```bash
sudo journalctl -u phone-free-desk -f
```

## API Usage

### Set DND Status (from Android app)

```bash
curl -X POST http://10.0.0.197:8000/dnd \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

### Check Status

```bash
curl http://10.0.0.197:8000/dnd
```

Response:
```json
{
  "active": true,
  "last_updated": "2025-12-01T10:30:45.123456"
}
```

## Configuration Reference

### GPIO Pins
- Default servo 1: GPIO 17
- Default servo 2: GPIO 18
- Default pump: GPIO 23

### Timing
- Spray duration: 2 seconds
- Cooldown period: 10 seconds
- Min detection frames: 3 consecutive frames

### Camera
- Resolution: 640x480
- FPS: 10
- Device: /dev/video0 (C270)

### Detection Zone
Normalized coordinates (0-1):
- x: 0.4 (40% from left)
- y: 0.4 (40% from top)
- width: 0.2 (20% of frame)
- height: 0.2 (20% of frame)

## Troubleshooting

### Camera not found
```bash
# List video devices
ls /dev/video*

# Test camera
ffmpeg -f v4l2 -i /dev/video0 -frames 1 test.jpg
```

### GPIO permissions
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Reboot
sudo reboot
```

### Pigpio not running
```bash
sudo systemctl start pigpiod
sudo systemctl status pigpiod
```

### Check logs
```bash
# Service logs
sudo journalctl -u phone-free-desk -f

# Application logs
tail -f /var/log/phone-free-desk.log
```

## Development

### Project Structure

```
phone-free-desk/
├── src/
│   ├── api/              # FastAPI server
│   ├── vision/           # Hand detection
│   ├── hardware/         # Servo and pump control
│   ├── core/             # Orchestrator
│   └── main.py           # Entry point
├── config/
│   └── settings.yaml     # Configuration
├── scripts/
│   ├── calibrate_arm.py  # Servo calibration
│   └── calibrate_zone.py # Zone calibration
├── systemd/
│   └── phone-free-desk.service
└── requirements.txt
```

### Running Tests

Test individual components:

```bash
# Test camera
python3 scripts/calibrate_zone.py

# Test servos
python3 scripts/calibrate_arm.py

# Test pump (BE CAREFUL - will spray!)
python3 -c "from hardware import WaterPump; p = WaterPump(23); p.spray(0.5); p.cleanup()"
```

## Safety Notes

- Start with the water reservoir empty or disconnected
- Test servo movements without water first
- Ensure pump is properly secured to avoid spills
- Keep electronics away from water
- The spray duration is 2 seconds - adjust if needed
- Add a physical cutoff switch if desired

## Android App Integration

The Android app (not included in this repo) should:

1. Monitor DND status changes
2. Send POST requests to `http://10.0.0.197:8000/dnd`
3. Update periodically (suggested: every 30 seconds)

Example request body:
```json
{"active": true}  // When DND is enabled
{"active": false} // When DND is disabled
```

## License

MIT

## Credits

Created for YouTube video demonstration.
