#!/usr/bin/env python3
"""
Detection Test Script

Interactive script to test phone, hand, and face detection.
Shows real-time visualization of all detections and triggers.
"""

import sys
import yaml
import cv2
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from vision import HandDetector


def main():
    print("=== Phone Free Desk - Detection Test ===\n")

    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    camera_config = config['camera']
    vision_config = config['vision']

    print("This script visualizes YOLOv8 object detection:")
    print("  - Phone detection (green box - YOLO cell phone class)")
    print("  - Person detection (cyan or red box)")
    print("  - Target (blue crosshair on person's head area)")
    print("\nWhen you move near the phone, the person box turns RED")
    print("and 'TOUCHING!' appears - this is what triggers the spray!")
    print("\nYOLOv8 is robust to all lighting/colors - no special setup needed!\n")

    print(f"Camera: {camera_config['width']}x{camera_config['height']} @ {camera_config['fps']}fps")
    print(f"Phone confidence: {vision_config.get('phone_confidence', 0.3)}")
    print(f"Person confidence: {vision_config.get('person_confidence', 0.5)}")
    print(f"Frame skip: {vision_config.get('frame_skip', 2)}")
    print(f"Debug mode: {vision_config.get('debug', False)}")
    print("\nPress 'q' to quit\n")

    # Initialize detector
    detector = HandDetector(
        camera_config,
        vision_config  # Pass full vision config
    )

    print("Starting detection... Place your phone on the desk and move your hand near it.\n")

    cv2.namedWindow('Detection Test')
    trigger_count = 0

    try:
        while True:
            # Get annotated frame
            frame = detector.get_annotated_frame()

            if frame is None:
                print("Failed to read frame")
                break

            # Get detection status
            person_touching, person_position, _ = detector.detect_hand_in_zone()

            # Show trigger status
            status_text = "TRIGGERED!" if person_touching else "Ready"
            status_color = (0, 0, 255) if person_touching else (0, 255, 0)

            if person_touching:
                trigger_count += 1

            # Draw status
            cv2.putText(frame, f"Status: {status_text}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
            cv2.putText(frame, f"Trigger count: {trigger_count}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if person_position:
                cv2.putText(frame, f"Target: ({person_position['x']:.2f}, {person_position['y']:.2f})",
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            else:
                cv2.putText(frame, "No target detected", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)

            # Show legend
            legend_y = frame.shape[0] - 100
            cv2.putText(frame, "Legend:", (10, legend_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (10, legend_y + 10), (30, legend_y + 30), (0, 255, 0), 3)
            cv2.putText(frame, "Phone", (35, legend_y + 27),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (10, legend_y + 35), (30, legend_y + 55), (255, 255, 0), 2)
            cv2.putText(frame, "Person (not touching)", (35, legend_y + 52),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (10, legend_y + 60), (30, legend_y + 80), (0, 0, 255), 2)
            cv2.putText(frame, "Person (TOUCHING!)", (35, legend_y + 77),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow('Detection Test', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nInterrupted")

    # Cleanup
    detector.cleanup()
    cv2.destroyAllWindows()

    print(f"\nTest complete! Total triggers: {trigger_count}")
    print("\nYOLOv8 Detection Tips:")
    print("  - Works with any phone color/type (YOLOv8 trained on COCO dataset)")
    print("  - Good lighting helps but not strictly required")
    print("  - Phone should be visible to camera (not covered)")
    print("  - System triggers when person/hand overlaps with phone")
    print()
    print("If detection is unreliable:")
    print("  - Ensure phone is clearly visible in frame")
    print("  - Adjust camera angle to see both phone and person")
    print("  - Consider lowering confidence threshold in config/settings.yaml")


if __name__ == "__main__":
    main()
