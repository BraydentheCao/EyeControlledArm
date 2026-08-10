from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import numpy as np
import cv2

app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()

config = picam2.create_preview_configuration(main={"size": (1200, 1200)})
picam2.configure(config)
picam2.start()

full_w,full_h = picam2.sensor_resolution
zoom_factor_x = 3.0
zoom_factor_y = 3.5
crop_w = int(full_w/zoom_factor_x)
crop_h = int(full_h/zoom_factor_y)
crop_xInit = int(full_w - crop_w)//2
crop_yInit = int(full_h - crop_h)//2

picam2.set_controls({"ScalerCrop": (crop_xInit, crop_yInit, crop_w, crop_h)})

def generate_frames():
    while True:
        # Get a frame from picam, do initial set up to make sure it can be filtered
        frame = picam2.capture_array()
        frame = cv2.flip(frame,0)
        
        finalFrame = frame

        #Convert to JPEG for streaming
        ret, buffer = cv2.imencode('.jpg',finalFrame)
        if not ret:
            continue

        finalFrameBytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + finalFrameBytes + b'\r\n')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <title>Raspberry Pi Video Feed</title>
    <style>
      body { background-color: #121212; color: white; text-align: center; font-family: sans-serif; }
      img { border: 2px solid #333; border-radius: 8px; margin-top: 20px; }
    </style>
  </head>
  <body>
    <h1>Live Video Feed</h1>
    <img src="{{ url_for('video_feed') }}" width="640" height="480">
  </body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)