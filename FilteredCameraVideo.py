from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import numpy as np
import cv2

app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (800, 600)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # Get a frame from picam, do initial set up to make sure it can be filtered
        frame = picam2.capture_array()
        frame = cv2.flip(frame,0)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        bilateralFilteredFrame = cv2.bilateralFilter(frame_bgr, 9, 75, 75)
        hsv = cv2.cvtColor(bilateralFilteredFrame, cv2.COLOR_BGR2HSV)

        """
        the variable hsv is a 3d numpy array that has the same xy dimensions as the image, then is 3 layers thick
        each layer is a different hsv channel, hue, saturation, and value
        Each "x,y" coordinate contains each of the 3 hsv values for that pixel
        it's [row, col, hsv channel] 

        hsv[:,:,0] means every row (: = every row), every column, but only the first channel, hue
        
        """
        
        hsv[:,:,2] = cv2.equalizeHist(hsv[:,:,2])

        # histEqualizedFrameBGR = cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)

        finalFrame = bilateralFilteredFrame

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