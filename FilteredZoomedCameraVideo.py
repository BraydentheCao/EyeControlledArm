from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import numpy as np
import cv2
from queue import Queue
import time


"""
TestZoom.py combined with FilteredCameraVideo.py
"""

app = Flask(__name__)
start_time = int(time.perf_counter()) #This means the eye zero funciton won't be perfectly three seconds, it's 3-4 second tech, but its much faster calculation wise

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
    global zeroX, zeroY, changeX, changeY, relativeX, relativeY
    zeroX, zeroY, changeX, changeY, relativeX, relativeY = -1, -1, 0, 0, 0, 0
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

              # Draw current position of the eye
              cv2.circle(frame, (cX, cY), 5, (255, 0, 0), -1)
              cv2.line(frame, (cX, 0), (cX, frame.shape[0]), (255, 0, 0), 1)
              cv2.line(frame, (0, cY), (frame.shape[1], cY), (255, 0, 0), 1)

              # Draw zero position of the eye  

              cv2.circle(frame, (zeroX, zeroY), 5, (0, 150, 250), -1)
              cv2.line(frame, (zeroX, 0), (zeroX, frame.shape[0]), (0, 150, 250), 1)
              cv2.line(frame, (0, zeroY), (frame.shape[1], zeroY), (0, 150, 250), 1)

              if zeroX == -1:
                zeroX, zeroY = ZeroPositionAlgorithm(cX,cY)  
                relativeX = zeroX
                relativeY = zeroY  
              else:
                changeX, changeY = EyeTrackingAlgorithm(cX, cY, sensitivity=1)

              if(x > 150):
                relativeX = cX - zeroX
                relativeY = cY - zeroY  

              cv2.putText(frame, f"Change X: {changeX} | Change Y: {changeY}",(10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,20,20), 2)
              cv2.putText(frame, f"Position X: {cX} | Position Y: {cX}",(10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,20,20), 2)
              cv2.putText(frame, f"Zero position X: {zeroX} | Zero position Y: {zeroY}",(10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,20,20), 2)
              cv2.putText(frame, f"Relative X: {relativeX} | Relative Y: {relativeY}",(10,120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,20,20), 2)
        

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
    <img src="{{ url_for('video_feed') }}" width="800" height="600">
  </body>
</html>
"""

QUEUE_SIZE = 5
eyeDataX = Queue(maxsize = QUEUE_SIZE)
eyeDataY = Queue(maxsize = QUEUE_SIZE)
changeX, changeY = 0,0

def EyeTrackingAlgorithm(x, y, sensitivity):
    """
    This function adds incoming xy data of the eye's 
    center to a list, then calculates average change, 
    returns a constant string of eye change data

    sensitivity changes how much the arm will move based on eye data
    """      

    global changeX, changeY

    if x > 150: # This is to prevent measuring the eyelashes that are tracked when I blink. My eye never goes below x = 200
      if eyeDataX.full():
        eyeDataX.get()
        eyeDataY.get()

      eyeDataX.put(x)
      eyeDataY.put(y)

      changeX = x - int(sum(eyeDataX.queue)/QUEUE_SIZE)
      changeY = y - int(sum(eyeDataY.queue)/QUEUE_SIZE)

    else:
       changeX = 0
       changeY = 0
    
    return changeX, changeY
    

ZEROQUEUE_MAX_SIZE = 25
eyeZeroDataX = Queue(maxsize = ZEROQUEUE_MAX_SIZE)
eyeZeroDataY = Queue(maxsize = ZEROQUEUE_MAX_SIZE)

def ZeroPositionAlgorithm(x,y):
    global start_time, eyeZeroDataX, eyeZeroDataY
    current_time = int(time.perf_counter())
    """
    Calculates the average x and y position of the eye after three seconds 
    of data collection
    returns average of x and y position of the eye
    """
    if x > 150:
      eyeZeroDataX.put(x)
      eyeZeroDataY.put(y)

    #print(f"Current time: {current_time}")
    #print(f"Start time: {start_time}")
    #print(f"diff: {current_time - start_time}")
    print(f"Queue size: {eyeZeroDataX.qsize()}")
    print(x)
    
    #if ((current_time - start_time) >= 3):
    if eyeZeroDataX.full() == True:
      start_time = current_time
      print(int(sum(eyeZeroDataX.queue)))

      #reset the eyeZeroDataX and Y queues to be zero
      xZeroDataSum = sum(eyeZeroDataX.queue)
      yZeroDataSum = sum(eyeZeroDataY.queue)

      eyeZeroDataX = Queue(maxsize = ZEROQUEUE_MAX_SIZE)
      eyeZeroDataY = Queue(maxsize = ZEROQUEUE_MAX_SIZE)

      return (int(xZeroDataSum/ZEROQUEUE_MAX_SIZE) , int(yZeroDataSum/ZEROQUEUE_MAX_SIZE))

    return -1,-1


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)