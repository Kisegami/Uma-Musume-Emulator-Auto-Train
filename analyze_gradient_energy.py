#!/usr/bin/env python3
"""Analyze gradient energy bar from the example image"""

import cv2
import numpy as np
from PIL import Image

# Create a test image similar to the example
# Energy bar with gradient: blue -> cyan -> green -> yellow -> gray
width, height = 200, 40

# Create RGB image
img = np.zeros((height, width, 3), dtype=np.uint8)

# Fill with gradient
# Left part (filled): blue -> cyan -> green -> yellow
# Right part (empty): gray

# Filled portion (0-150): gradient
for x in range(150):
    ratio = x / 150.0
    
    if ratio < 0.25:  # Blue
        r = int(0 + (100 * (ratio / 0.25)))
        g = int(100 + (155 * (ratio / 0.25)))
        b = 255
    elif ratio < 0.5:  # Cyan to Green
        r = int(100 + (155 * ((ratio - 0.25) / 0.25)))
        g = 255
        b = int(255 - (155 * ((ratio - 0.25) / 0.25)))
    elif ratio < 0.75:  # Green to Yellow
        r = 255
        g = 255
        b = int(100 - (100 * ((ratio - 0.5) / 0.25)))
    else:  # Yellow to Orange
        r = 255
        g = int(255 - (100 * ((ratio - 0.75) / 0.25)))
        b = 0
    
    img[:, x] = [r, g, b]

# Empty portion (150-200): gray
img[:, 150:] = [117, 117, 117]

# Save the test image
cv2.imwrite("test_gradient_energy.png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
print("Created test_gradient_energy.png")

# Analyze it
hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
saturation = hsv[:, :, 1]

mid_y = height // 2
midline_sat = saturation[mid_y, :]

print(f"\nMidline saturation analysis:")
print(f"Position | Saturation | Type")
print(f"{'='*40}")

for x_pos in [0, 25, 50, 75, 100, 125, 150, 175, 200]:
    if x_pos < width:
        sat = midline_sat[x_pos]
        ptype = "FILLED" if sat > 30 else "EMPTY"
        print(f"{x_pos:3d}     | {sat:3d}        | {ptype}")

# Find filled positions
filled_mask = midline_sat > 30
filled_positions = np.where(filled_mask)[0]

print(f"\n\nFilled positions (saturation > 30):")
if len(filled_positions) > 0:
    print(f"First filled: {filled_positions[0]}")
    print(f"Last filled: {filled_positions[-1]}")
    print(f"Total filled pixels: {len(filled_positions)}")
    
    # Calculate energy
    left_border = 10
    rightmost_filled = filled_positions[-1]
    bar_content_width = width - left_border
    filled_content_width = max(0, rightmost_filled - left_border + 1)
    percentage = float(filled_content_width / bar_content_width * 100.0)
    percentage = min(100.0, max(0.0, percentage))
    
    print(f"\nCalculated energy: {percentage:.2f}%")
    print(f"Expected: 75.00% (150/200)")
else:
    print(f"No filled pixels found")


