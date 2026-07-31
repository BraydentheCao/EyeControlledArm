from flask import Flask, render_template_string, Response
import cv2
import io

app = Flask(__name__)

# Initialize the camera (0 is usually the default Pi camera or USB webcam)
camera = cv2.VideoCapture(0)

# Lower resolution slightly for smoother network streaming
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def generate_frames():
    while True:
        # Read the camera frame
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            # Yield the output frame in byte format for HTTP multipart streaming
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Minimal HTML template
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
    # Return the response supplied with the specific media type (mime type)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Listen on all local network interfaces on port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)