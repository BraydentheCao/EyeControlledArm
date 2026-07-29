"""
The purpose of this folder is to run different test programs, such as making sure the 
master pi is connected properly to github. 

It will also test connection to peripheral devices:
    If the connection to the eye tracking headband's esp32-S3 module,
    The transmission of video feed from the ETH
    The arm's arduino module via bluetooth
    The eventual teensy board for controlling all the wheels and servos
"""
import RPi.GPIO as GPIO
from gpiozero import Motor
from gpiozero import Servo
from gpiozero import PWMOutputDevice
import time

fan = PWMOutputDevice(18, frequency=100,initial_value=0)

def testPiConnectionAndPiFan():
    """
    This func tests if the MP connects to github repo and vscode correctly
    It'll test if the pi's fan is working properly
    """
    print("Fan at 30 percent speed (Low)")
    fan.value = 0.3  # Value must be between 0.0 and 1.0
    time.sleep(5)

    print("Fan at 60 percent speed (Medium)")
    fan.value = 0.6
    time.sleep(5)
    
    print("Fan at 100 percent speed (Full Blast)")
    fan.value = 1.0
    time.sleep(5)
    
    print("Fan OFF")
    fan.value = 0.0
    time.sleep(3)

try:
    while True:
        testPiConnectionAndPiFan()
except KeyboardInterrupt:
    GPIO.cleanup
    