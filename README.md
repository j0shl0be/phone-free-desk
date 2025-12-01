# Phone Free Desk

A Raspberry Pi 5 project that uses computer vision and robotics to spray your face with water when you reach for your phone during Do Not Disturb mode.

**How it works:**
- **YOLOv8 object detection** finds your phone automatically (any color, any lighting)
- Person detection triggers when you reach for the phone
- Smart targeting aims at your head/face area
- Inverse kinematics calculates servo angles to aim at your face
- 2DOF robotic arm sprays water at your face

**Powered by YOLOv8!** Uses state-of-the-art object detection trained on the COCO dataset. No calibration, no special setup - just works with any phone in any lighting condition.

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
- **YOLOv8n (nano)** for lightweight object detection on Raspberry Pi 5
- Detects "cell phone" class from COCO dataset (any phone, any color)
- Detects "person" class for trigger and targeting
- Overlap detection between person and phone (trigger)
- Automatic targeting of person's head area (upper 20% of bbox)
- Robust to lighting, phone colors, orientations
- Runs at 10 FPS with Logitech C270 webcam

### 3. Hardware Controller (`src/hardware/`)
- 2-DOF robotic arm with servo motors
- Inverse kinematics for camera-to-servo mapping
- Water pump control via GPIO relay
- Dynamic targeting based on face position

### 4. Orchestrator (`src/core/`)
- Main control loop
- Trigger: Hand touching phone + DND active + face detected
- Target: Detected face position
- 10-second cooldown between sprays
- Requires multiple consecutive detections to prevent false triggers

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

### 4. Test YOLOv8 Detection

**Note:** On first run, YOLOv8 will automatically download the yolov8n.pt model weights (~6MB). This only happens once.

```bash
source venv/bin/activate
python3 scripts/test_detection.py
```

This shows real-time visualization of YOLOv8 detection:
- Phone (green box with confidence score)
- Person detection (cyan or red box with confidence)
- Target crosshair (blue, aims at head area)

When you reach for the phone → RED box + "TOUCHING!" appears (this triggers spray!)

**YOLOv8 Advantages:**
- Works with ANY phone (iPhone, Android, any color, any case)
- Robust to all lighting conditions (bright, dim, mixed)
- No calibration or special setup required
- Pre-trained on 1M+ images (COCO dataset)
- Fast inference on Raspberry Pi 5 (~20-30 FPS with YOLOv8n)

**If phone detection is unreliable:**

COCO's "cell phone" class was trained on phones held up (selfies), not phones lying flat. Try:

1. **Lower confidence threshold** in `config/settings.yaml`:
   ```yaml
   vision:
     phone_confidence: 0.2  # or even 0.1
     debug: true  # See what YOLO detects
   ```

2. **Use a specialized phone detection model** from Roboflow (see [docs/CUSTOM_PHONE_DETECTION.md](docs/CUSTOM_PHONE_DETECTION.md))
   - Pre-trained models specifically for phones on desks
   - Much better accuracy than COCO

3. **Train your own model** on your specific phone/desk (30-100 images, best results)

### 5. Calibration

#### Step 1: Calibrate Arm Rest Position

```bash
source venv/bin/activate
python3 scripts/calibrate_arm.py
```

Find the servo angles for the arm's rest position (where it sits when not spraying).

#### Step 2: Calibrate Kinematics (Targeting)

```bash
source venv/bin/activate
python3 scripts/calibrate_kinematics.py
```

This is the most important step! It teaches the arm how to aim at different positions:
1. For each corner of the camera view (top-left, top-right, bottom-left, bottom-right)
2. Place a marker (your hand, a sticky note, etc.) in that corner
3. Manually adjust the servos to aim the arm at the marker
4. Save the calibration for that corner

This creates a mapping between camera coordinates and servo angles, allowing the arm to accurately aim at your face wherever you are in frame.

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
│   ├── api/                    # FastAPI server
│   │   ├── server.py           # App setup
│   │   └── routes.py           # DND endpoints
│   ├── vision/                 # Computer vision
│   │   ├── detector.py         # Hand & face detection
│   │   └── zone.py             # Phone zone definition
│   ├── hardware/               # Hardware control
│   │   ├── arm.py              # Servo arm controller
│   │   ├── pump.py             # Water pump
│   │   ├── kinematics.py       # Inverse kinematics
│   │   └── spray_sequence.py   # Spray routine
│   ├── core/                   # Main logic
│   │   ├── orchestrator.py     # Coordinates everything
│   │   └── state.py            # State management
│   └── main.py                 # Entry point
├── config/
│   └── settings.yaml           # All configuration
├── scripts/
│   ├── test_detection.py       # Test phone/hand/face detection
│   ├── calibrate_arm.py        # Arm rest position
│   └── calibrate_kinematics.py # Targeting calibration
├── systemd/
│   └── phone-free-desk.service
└── requirements.txt
```

### Running Tests

Test individual components:

```bash
# Test all detection (phone, hand, face)
python3 scripts/test_detection.py

# Test servos
python3 scripts/calibrate_arm.py

# Test targeting
python3 scripts/calibrate_kinematics.py

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
