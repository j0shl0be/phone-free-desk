#!/usr/bin/env python3
"""
Detection Zone Calibration Script [DEPRECATED]

*** THIS SCRIPT IS DEPRECATED ***

With YOLOv8, manual zone calibration is no longer needed!
YOLOv8 automatically detects phones anywhere in the camera frame.

Use scripts/test_detection.py instead to verify phone detection.

---

This script was used for the old zone-based detection system.
Interactive script to define the phone detection zone in the camera frame.
"""

import sys
import yaml
import cv2
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from vision import HandDetector, PhoneZone


def main():
    print("=== Phone Detection Zone Calibration ===\n")

    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    camera_config = config['camera']
    zone_config = config['detection_zone']

    print("Instructions:")
    print("1. Position your phone in the desired location on your desk")
    print("2. Use mouse to drag a rectangle around the phone area")
    print("3. Press 's' to save the zone")
    print("4. Press 'q' to quit\n")
    print("Note: Green box shows the current detection zone")
    print("      Hand landmarks will be drawn when detected\n")

    # Initialize camera
    cap = cv2.VideoCapture(camera_config['device_index'])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config['width'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config['height'])

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Camera resolution: {frame_width}x{frame_height}")

    # Current zone
    zone = PhoneZone.from_config(zone_config)

    # Mouse callback state
    drawing = False
    start_point = None
    current_rect = None

    def mouse_callback(event, x, y, flags, param):
        nonlocal drawing, start_point, current_rect, zone

        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start_point = (x, y)
            current_rect = None

        elif event == cv2.EVENT_MOUSEMOVE:
            if drawing:
                current_rect = (start_point[0], start_point[1], x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            if start_point:
                x1, y1 = start_point
                x2, y2 = x, y

                # Ensure x1,y1 is top-left
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)

                # Convert to normalized coordinates
                norm_x = x1 / frame_width
                norm_y = y1 / frame_height
                norm_width = (x2 - x1) / frame_width
                norm_height = (y2 - y1) / frame_height

                zone = PhoneZone(norm_x, norm_y, norm_width, norm_height)
                print(f"New zone: x={norm_x:.3f}, y={norm_y:.3f}, w={norm_width:.3f}, h={norm_height:.3f}")

    cv2.namedWindow('Zone Calibration')
    cv2.setMouseCallback('Zone Calibration', mouse_callback)

    # Initialize hand detector for visualization
    hand_detector = HandDetector(camera_config, zone, config['vision']['confidence_threshold'])

    try:
        while True:
            frame = hand_detector.get_annotated_frame()
            if frame is None:
                print("Failed to read frame")
                break

            # Draw current selection rectangle
            if current_rect:
                x1, y1, x2, y2 = current_rect
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, "New Zone", (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # Show instructions on frame
            cv2.putText(frame, "Drag to define zone | 's' to save | 'q' to quit",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow('Zone Calibration', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Quitting without saving")
                break
            elif key == ord('s'):
                # Save zone to config
                config['detection_zone']['x'] = zone.x
                config['detection_zone']['y'] = zone.y
                config['detection_zone']['width'] = zone.width
                config['detection_zone']['height'] = zone.height

                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

                print(f"✓ Zone saved to {config_path}")
                print(f"  x={zone.x:.3f}, y={zone.y:.3f}, width={zone.width:.3f}, height={zone.height:.3f}")
                break

    except KeyboardInterrupt:
        print("\nInterrupted")

    # Cleanup
    hand_detector.cleanup()
    cv2.destroyAllWindows()
    print("Done!")


if __name__ == "__main__":
    main()
