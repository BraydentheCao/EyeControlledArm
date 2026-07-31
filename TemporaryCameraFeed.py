from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import io

app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # Capture frame directly as JPEG in memory
        stream = io.BytesIO()
        picam2.capture_file(stream, format='jpeg')
        frame_bytes = stream.getvalue()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

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