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

    print("This script visualizes the hybrid detection system:")
    print("  - Phone detection (green box - YOLOv8 cell phone class)")
    print("  - Hand detection (cyan or red box - MediaPipe Hands)")
    print("  - Face targeting (blue box with crosshair - MediaPipe Face)")
    print("\nWhen your HAND overlaps the phone, hand box turns RED")
    print("and 'TOUCHING!' appears - this is what triggers the spray!")
    print("\nHybrid system: YOLOv8 for phones + MediaPipe for hands/face\n")

    print(f"Camera: {camera_config['width']}x{camera_config['height']} @ {camera_config['fps']}fps")
    print(f"Phone confidence (YOLOv8): {vision_config.get('phone_confidence', 0.3)}")
    print(f"Hand confidence (MediaPipe): {vision_config.get('hand_confidence', 0.7)}")
    print(f"Face confidence (MediaPipe): {vision_config.get('face_confidence', 0.7)}")
    print(f"Phone cache duration: {vision_config.get('phone_cache_duration', 30.0)}s (stays valid even when occluded)")
    print(f"YOLOv8 image size: {vision_config.get('yolo_imgsz', 320)}")
    print(f"Debug mode: {vision_config.get('debug', False)}")
    print(f"Show timing: {vision_config.get('show_timing', False)}")
    print("\nPress 'q' to quit, 't' to toggle timing info, 'r' to re-detect phone\n")

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
            hand_touching, face_position, _ = detector.detect_hand_in_zone()

            # Show trigger status
            status_text = "TRIGGERED!" if hand_touching else "Ready"
            status_color = (0, 0, 255) if hand_touching else (0, 255, 0)

            if hand_touching:
                trigger_count += 1

            # Draw status
            cv2.putText(frame, f"Status: {status_text}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
            cv2.putText(frame, f"Trigger count: {trigger_count}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if face_position:
                cv2.putText(frame, f"Target: ({face_position['x']:.2f}, {face_position['y']:.2f})",
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            else:
                cv2.putText(frame, "No face target", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)

            # Show legend
            legend_y = frame.shape[0] - 100
            cv2.putText(frame, "Legend:", (10, legend_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (10, legend_y + 10), (30, legend_y + 30), (0, 255, 0), 3)
            cv2.putText(frame, "Phone", (35, legend_y + 27),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (10, legend_y + 35), (30, legend_y + 55), (255, 255, 0), 2)
            cv2.putText(frame, "Hand (not touching)", (35, legend_y + 52),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.rectangle(frame, (10, legend_y + 60), (30, legend_y + 80), (0, 0, 255), 2)
            cv2.putText(frame, "Hand (TOUCHING!)", (35, legend_y + 77),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow('Detection Test', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('t'):
                # Toggle timing display
                detector.show_timing = not detector.show_timing
                print(f"Timing display: {'ON' if detector.show_timing else 'OFF'}")
            elif key == ord('r'):
                # Force re-detect phone
                detector.invalidate_phone_cache()
                print("Phone cache invalidated - will re-detect on next frame...")

    except KeyboardInterrupt:
        print("\nInterrupted")

    # Cleanup
    detector.cleanup()
    cv2.destroyAllWindows()

    print(f"\nTest complete! Total triggers: {trigger_count}")
    print("\nHybrid Detection System:")
    print("  - Phone: YOLOv8 (works with any phone color/type)")
    print("  - Hands: MediaPipe (precise hand landmark detection)")
    print("  - Face: MediaPipe (accurate face center targeting)")
    print()
    print("Performance Tips:")
    print("  - Phone position cached for 30 seconds (stays valid even when occluded)")
    print("  - Hand/face detection runs EVERY frame for instant response")
    print("  - If phone moves: Press 'r' to force re-detection")
    print("  - Phone cache auto-expires after spray cooldown")
    print("  - Enable show_timing: true in config to see bottlenecks")
    print()
    print("Detection Tips:")
    print("  - Ensure phone is clearly visible to camera")
    print("  - Good lighting helps MediaPipe hand/face detection")
    print("  - System triggers when HAND overlaps with phone")
    print("  - Targets the center of detected FACE")
    print()
    print("If detection is unreliable:")
    print("  - Lower phone_confidence in config/settings.yaml (for phone)")
    print("  - Lower hand_confidence/face_confidence (for hands/face)")
    print("  - Adjust camera angle to see phone, hands, and face clearly")


if __name__ == "__main__":
    main()
