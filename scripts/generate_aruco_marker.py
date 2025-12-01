#!/usr/bin/env python3
"""
ArUco Marker Generator

Generates an ArUco marker to place on your phone for reliable detection.
"""

import cv2
import numpy as np
from pathlib import Path


def generate_marker(marker_id=0, size_mm=40, dpi=300, output_path="aruco_marker_0.png"):
    """
    Generate an ArUco marker image.

    Args:
        marker_id: ArUco marker ID (default: 0 for phone)
        size_mm: Size of marker in millimeters
        dpi: Print resolution in DPI
        output_path: Where to save the marker image
    """
    # Calculate size in pixels
    size_inches = size_mm / 25.4
    size_pixels = int(size_inches * dpi)

    # Get ArUco dictionary (4x4_50)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

    # Generate marker
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_pixels)

    # Add white border for better detection
    border_size = size_pixels // 10
    marker_with_border = cv2.copyMakeBorder(
        marker_image,
        border_size, border_size, border_size, border_size,
        cv2.BORDER_CONSTANT,
        value=255
    )

    # Save marker
    cv2.imwrite(output_path, marker_with_border)

    return marker_with_border, size_pixels + 2 * border_size


def main():
    print("=== ArUco Marker Generator ===\n")

    output_dir = Path(__file__).parent.parent / "aruco_markers"
    output_dir.mkdir(exist_ok=True)

    sizes = [
        (30, "Small (30mm - for small phones/cases)"),
        (40, "Medium (40mm - recommended)"),
        (50, "Large (50mm - for better long-distance detection)")
    ]

    print("Generating ArUco marker ID 0 for phone detection...\n")

    for size_mm, description in sizes:
        output_path = output_dir / f"phone_marker_{size_mm}mm.png"

        marker, pixels = generate_marker(
            marker_id=0,
            size_mm=size_mm,
            dpi=300,
            output_path=str(output_path)
        )

        print(f"✓ Generated {description}")
        print(f"  File: {output_path}")
        print(f"  Size: {size_mm}mm ({pixels}x{pixels} pixels @ 300dpi)")
        print()

    print("=" * 60)
    print("HOW TO USE:")
    print("=" * 60)
    print()
    print("1. Print one of the generated markers:")
    print(f"   Files are in: {output_dir}/")
    print()
    print("2. Choose the right size:")
    print("   - 30mm: Small phones or minimal visibility")
    print("   - 40mm: Recommended for most setups")
    print("   - 50mm: Better for cameras farther away")
    print()
    print("3. Attach to your phone:")
    print("   Option A: Print on sticker paper and stick directly to phone case")
    print("   Option B: Print on paper, laminate, and tape to phone")
    print("   Option C: Print on paper and tape to desk next to phone")
    print()
    print("4. IMPORTANT: Make sure marker is visible to camera!")
    print("   - Place marker on back of phone (facing camera)")
    print("   - Or place marker on desk next to where phone sits")
    print()
    print("5. Test detection:")
    print("   python3 scripts/test_detection.py")
    print()
    print("=" * 60)
    print()
    print("NOTE: The system detects marker ID 0 and expands the detection")
    print("      area to cover your entire phone.")
    print()


if __name__ == "__main__":
    main()
