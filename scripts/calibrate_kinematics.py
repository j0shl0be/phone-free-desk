#!/usr/bin/env python3
"""
Kinematics Calibration Script

Interactive script to calibrate the mapping between camera coordinates and servo angles.
This helps the arm accurately aim at detected faces in the camera view.
"""

import sys
import yaml
import cv2
from pathlib import Path
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def angle_to_servo_range(angle: float) -> float:
    """Convert 0-180 degree range to servo's -90 to 90 range."""
    return angle - 90


def main():
    print("=== Kinematics Calibration ===\n")
    print("This script helps you calibrate the arm's targeting accuracy.")
    print("You'll aim the arm at each corner of the camera view and record the servo angles.\n")

    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    gpio_config = config['gpio']
    camera_config = config['camera']

    # Initialize camera
    print("Initializing camera...")
    cap = cv2.VideoCapture(camera_config['device_index'])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config['width'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config['height'])

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera resolution: {frame_width}x{frame_height}\n")

    # Initialize servos
    print("Initializing servos...")
    try:
        factory = PiGPIOFactory()
    except:
        print("Warning: Could not initialize pigpio, using default")
        factory = None

    servo_1 = AngularServo(gpio_config['servo_1'], min_angle=-90, max_angle=90, pin_factory=factory)
    servo_2 = AngularServo(gpio_config['servo_2'], min_angle=-90, max_angle=90, pin_factory=factory)

    # Current servo angles (0-180 range)
    angles = {
        1: 90,
        2: 90
    }

    def move_servo(servo_num, angle):
        """Move specified servo to angle (0-180 range)."""
        servo_angle = angle_to_servo_range(angle)
        if servo_num == 1:
            servo_1.angle = servo_angle
        else:
            servo_2.angle = servo_angle

    # Move to initial position
    move_servo(1, angles[1])
    move_servo(2, angles[2])

    print("\nCalibration Instructions:")
    print("=" * 50)
    print("You'll calibrate 4 corner points of the camera view:")
    print("  1. Top-Left")
    print("  2. Top-Right")
    print("  3. Bottom-Left")
    print("  4. Bottom-Right")
    print("\nFor each corner:")
    print("  - Use 1/2 to select servo, +/- to adjust angle")
    print("  - Position a marker (like your hand) in that corner")
    print("  - Aim the arm to point at the marker")
    print("  - Press 's' to save that corner's calibration")
    print("  - Press 'n' to move to next corner")
    print("\nPress any key to start...")
    print("=" * 50)
    input()

    # Calibration corners
    corners_to_calibrate = [
        ('top_left', 'Top-Left (x=0, y=0)'),
        ('top_right', 'Top-Right (x=1, y=0)'),
        ('bottom_left', 'Bottom-Left (x=0, y=1)'),
        ('bottom_right', 'Bottom-Right (x=1, y=1)')
    ]

    calibrated_corners = {}
    current_servo = 1

    for corner_key, corner_name in corners_to_calibrate:
        print(f"\n{'='*50}")
        print(f"Calibrating: {corner_name}")
        print(f"{'='*50}")
        print("Place a marker in the corner shown in the camera view.")
        print("Controls: 1/2=select servo, +/-=adjust, s=save, n=next\n")

        saved = False
        cv2.namedWindow('Calibration View')

        while not saved:
            # Show camera feed
            ret, frame = cap.read()
            if ret:
                # Draw crosshairs at corners
                h, w = frame.shape[:2]
                corners_px = {
                    'top_left': (10, 10),
                    'top_right': (w - 10, 10),
                    'bottom_left': (10, h - 10),
                    'bottom_right': (w - 10, h - 10)
                }

                # Highlight current corner
                if corner_key in corners_px:
                    x, y = corners_px[corner_key]
                    cv2.drawMarker(frame, (x, y), (0, 0, 255),
                                  cv2.MARKER_CROSS, 40, 3)
                    cv2.putText(frame, "AIM HERE", (x - 50, y - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # Draw other corners
                for key, pos in corners_px.items():
                    if key != corner_key:
                        cv2.circle(frame, pos, 5, (0, 255, 0), -1)

                # Show current servo angles
                cv2.putText(frame, f"Servo 1: {angles[1]:.0f}deg", (10, h - 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"Servo 2: {angles[2]:.0f}deg", (10, h - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"Selected: Servo {current_servo}", (w - 200, h - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                cv2.imshow('Calibration View', frame)

            key = cv2.waitKey(100) & 0xFF

            if key == ord('1'):
                current_servo = 1
                print("Selected Servo 1")
            elif key == ord('2'):
                current_servo = 2
                print("Selected Servo 2")
            elif key == ord('+') or key == ord('='):
                angles[current_servo] = min(180, angles[current_servo] + 5)
                move_servo(current_servo, angles[current_servo])
                print(f"Servo {current_servo} -> {angles[current_servo]}°")
            elif key == ord('-') or key == ord('_'):
                angles[current_servo] = max(0, angles[current_servo] - 5)
                move_servo(current_servo, angles[current_servo])
                print(f"Servo {current_servo} -> {angles[current_servo]}°")
            elif key == ord('s'):
                # Get camera coordinates for this corner
                cam_coords = {
                    'top_left': (0.0, 0.0),
                    'top_right': (1.0, 0.0),
                    'bottom_left': (0.0, 1.0),
                    'bottom_right': (1.0, 1.0)
                }

                cam_x, cam_y = cam_coords[corner_key]

                calibrated_corners[corner_key] = {
                    'cam_x': cam_x,
                    'cam_y': cam_y,
                    'servo1': angles[1],
                    'servo2': angles[2]
                }

                print(f"✓ Saved {corner_name}: Servo1={angles[1]}°, Servo2={angles[2]}°")
                saved = True
            elif key == ord('n'):
                if corner_key in calibrated_corners:
                    print("Moving to next corner...")
                    saved = True
                else:
                    print("Please save this corner first (press 's')")

        cv2.destroyAllWindows()

    # Save calibration to config
    print("\n" + "="*50)
    print("Saving calibration to config...")

    config['kinematics']['corners'] = calibrated_corners

    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Calibration saved to {config_path}")
    print("\nCalibrated corners:")
    for corner_key, data in calibrated_corners.items():
        print(f"  {corner_key}: cam({data['cam_x']:.1f}, {data['cam_y']:.1f}) -> servo({data['servo1']}°, {data['servo2']}°)")

    # Cleanup
    servo_1.close()
    servo_2.close()
    cap.release()
    print("\nCalibration complete!")


if __name__ == "__main__":
    main()
