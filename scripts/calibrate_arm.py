#!/usr/bin/env python3
"""
Arm Calibration Script

Interactive script to find the correct servo angles for rest and spray positions.
"""

import sys
import yaml
from pathlib import Path
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def angle_to_servo_range(angle: float) -> float:
    """Convert 0-180 degree range to servo's -90 to 90 range."""
    return angle - 90


def main():
    print("=== Robotic Arm Calibration ===\n")

    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    gpio_config = config['gpio']
    servo_config = config['servo']

    print(f"Using GPIO pins: Servo 1={gpio_config['servo_1']}, Servo 2={gpio_config['servo_2']}")

    # Initialize servos
    try:
        factory = PiGPIOFactory()
    except:
        print("Warning: Could not initialize pigpio, using default")
        factory = None

    servo_1 = AngularServo(gpio_config['servo_1'], min_angle=-90, max_angle=90, pin_factory=factory)
    servo_2 = AngularServo(gpio_config['servo_2'], min_angle=-90, max_angle=90, pin_factory=factory)

    print("\nControls:")
    print("  1/2: Select Servo 1 or Servo 2")
    print("  +/-: Increase/decrease angle by 5 degrees")
    print("  r: Save as REST position")
    print("  s: Save as SPRAY position")
    print("  q: Quit and save config")
    print()

    current_servo = 1
    angles = {
        1: servo_config['servo_1_rest'],
        2: servo_config['servo_2_rest']
    }

    def move_servo(servo_num, angle):
        """Move specified servo to angle (0-180 range)."""
        servo_angle = angle_to_servo_range(angle)
        if servo_num == 1:
            servo_1.angle = servo_angle
        else:
            servo_2.angle = servo_angle
        print(f"Servo {servo_num} -> {angle}° (servo range: {servo_angle}°)")

    # Move to initial positions
    move_servo(1, angles[1])
    move_servo(2, angles[2])

    try:
        while True:
            print(f"\nCurrent: Servo {current_servo} at {angles[current_servo]}°")
            cmd = input("Command: ").strip().lower()

            if cmd == '1':
                current_servo = 1
                print("Selected Servo 1")
            elif cmd == '2':
                current_servo = 2
                print("Selected Servo 2")
            elif cmd == '+':
                angles[current_servo] = min(180, angles[current_servo] + 5)
                move_servo(current_servo, angles[current_servo])
            elif cmd == '-':
                angles[current_servo] = max(0, angles[current_servo] - 5)
                move_servo(current_servo, angles[current_servo])
            elif cmd == 'r':
                config['servo'][f'servo_{current_servo}_rest'] = angles[current_servo]
                print(f"✓ Saved Servo {current_servo} REST position: {angles[current_servo]}°")
            elif cmd == 's':
                config['servo'][f'servo_{current_servo}_spray'] = angles[current_servo]
                print(f"✓ Saved Servo {current_servo} SPRAY position: {angles[current_servo]}°")
            elif cmd == 'q':
                break
            else:
                print("Invalid command")

    except KeyboardInterrupt:
        print("\n\nInterrupted")

    # Save config
    print("\nSaving configuration...")
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"✓ Configuration saved to {config_path}")

    # Cleanup
    servo_1.close()
    servo_2.close()
    print("Done!")


if __name__ == "__main__":
    main()
