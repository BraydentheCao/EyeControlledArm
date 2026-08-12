from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import numpy as np
import cv2

"""
TestZoom.py combined with FilteredCameraVideo.py
"""

app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (800, 600)})
picam2.configure(config)
picam2.start()

# Zoom in on the center of the image by a factor of 3

full_w,full_h = picam2.sensor_resolution
zoom_factor_x = 4
zoom_factor_y = 5
crop_w = int(full_w/zoom_factor_x)
crop_h = int(full_h/zoom_factor_y)
crop_xInit = int(full_w - crop_w)//2
crop_yInit = int(full_h - crop_h)//2

CENTER_X = 800//(2*zoom_factor_x)

picam2.set_controls({"ScalerCrop": (crop_xInit, crop_yInit, crop_w, crop_h)})

def generate_frames():
    while True:
        # Get a frame from picam, do initial set up to make sure it can be filtered
        frame = picam2.capture_array()
        frame = cv2.flip(frame,0)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # BilFiltFrame --> smooths image while preserving the edges
        bilateralFilteredFrame = cv2.bilateralFilter(frame_bgr, 9, 75, 75)
        hsv = cv2.cvtColor(bilateralFilteredFrame, cv2.COLOR_BGR2HSV)

        """
        the variable hsv is a 3d numpy array that has the same xy dimensions as the image, then is 3 layers thick
        each layer is a different hsv channel, hue, saturation, and value
        Each "x,y" coordinate contains each of the 3 hsv values for that pixel
        it's [row, col, hsv channel] 

        hsv[:,:,0] means every row (: = every row), every column, but only the first channel, hue
        
        """

        # hsv & histEqualize --> Basically smooths out the brightness via CDF
        # The "commonness" of each brightness is the same, the brightness of each pixel retains the same percentile
        #hsv[:,:,2] = cv2.equalizeHist(hsv[:,:,2])
        #finalFrame = cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)

        
        # The arguments inside v[] are a 2d array of true/false values. If true, the values in v are overriden to be 0
        # This is called masking
        v = hsv[:,:,2]
        v[(v<70)] = 0
        v[(v>=70)] = 255
        hsv[:,:,2] = v
        

        # Morphological openning to remove the black eyelash part

        kernel = np.ones((3,3), np.uint8)
        
        hsv[:,:,2] = cv2.erode(hsv[:,:,2], kernel, iterations = 2)
        hsv[:,:,2] = cv2.dilate(hsv[:,:,2], kernel, iterations = 2)
        
        #_ , threshFrameWhite = cv2.threshold(histEqualizedFrameBGR, )
        #_ , threshFrame = cv2.threshold(histEqualizedFrameBGR, 225, 255, cv2.THRESH_BINARY)


        # Inversion (255 -> 0 and vice versa) for contouring
        invertedHSV = cv2.bitwise_not(hsv[:,:,2])
        contours,_ = cv2.findContours(invertedHSV, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        finalFrame = cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)

        # Contouring to find the center of the largest possible shape
        if contours:
          largest = max(contours, key=cv2.contourArea)
          M = cv2.moments(largest)
          ((x,y), radius) = cv2.minEnclosingCircle(largest)

          if M["m00"] != 0:
              cX = int(M["m10"] / M["m00"])
              cY = int(M["m01"] / M["m00"])

              cv2.drawContours(frame, [largest], -1, (0, 255, 0), 2)
              cv2.circle(frame, (cX, cY), 5, (255, 0, 0), -1)
              cv2.line(frame, (cX, 0), (cX, frame.shape[0]), (255, 0, 0), 1)
              cv2.line(frame, (0, cY), (frame.shape[1], cY), (255, 0, 0), 1)
        

        #Convert to JPEG for streaming
        ret, buffer = cv2.imencode('.jpg',frame)
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
    <img src="{{ url_for('video_feed') }}" width="400" height="300">
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