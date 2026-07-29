import time
from picamera2 import Picamera2

print("Initializing camera...")
# Initialize the Picamera2 instance
picam2 = Picamera2()

# Configure the camera with default preview settings
camera_config = picam2.create_preview_configuration()
picam2.configure(camera_config)

# Start the camera stream
picam2.start()
print("Camera started! Waiting 2 seconds for sensor auto-exposure...")

# Allow the camera sensor time to adjust light levels
time.sleep(2)

# Save the picture
output_file = "test_image.jpg"
picam2.capture_file(output_file)

print(f"Success! Image captured and saved as '{output_file}'")

# Clean up and release the camera connection
picam2.stop()