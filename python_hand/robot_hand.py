# Opens the camera and shows the vide window
import cv2
# Google's Hand tracking library
import mediapipe as mp
# Submodules inside mediapipe. Vision gives the HandLandmarker,
# the tool that finds hands
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
# Python talks to arduino over USB
import serial
import time
import numpy as np

# Opens a connection to the Arduino on port COM3. 9600 is the baud rate which must
# match Serial.begin(9600)
arduino = serial.Serial('COM3', 9600, timeout=1)
# When python opens the serial port, Arduino reboots for 2 seconds
time.sleep(2)

# File name of the AI model I downloaded - must be in the same file as this script
MODEL_PATH = "hand_landmarker.task"
# Tells mediapipe where to find the model
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
# This configures the hand detector: only track 1 hand, and only accept detections
# the AI is at least 70% confident about
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.7
)
# Actually creates the hand detector using those settings
detector = vision.HandLandmarker.create_from_options(options)

# Opens the default webcam
cap = cv2.VideoCapture(0)

# This function takes 21 landmarks and 3 index numbers from one finger (tip, middle joint, and knuckle)
def get_finger_angle(landmarks, tip, pip, mcp):

    # Here we grab the x, y coordinates of the index numbers so that we can perform math on them
    a = np.array([landmarks[tip].x, landmarks[tip].y])
    b = np.array([landmarks[pip].x, landmarks[pip].y])
    c = np.array([landmarks[mcp].x, landmarks[mcp].y])

    # Creates 2 vectors, both starting from the middle joint. One points towards the tip of the finer,
    # and the other points towards the knuckle
    ba = a - b
    bc = c - b

    # This is the dot product formula for finding an angle between two vectors
    # The + 1e-6 (a tiny number) just prevents a divide-by-zero crash if two points overlap.
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

# Servo mapping function
def angle_to_servo(angle):
    # Remaps one number range to another. A finger angle of 100 degrees (fairly bent) maps to a servo angle
    # of 100 degrees. A finger angle of 180 degrees (totally straight), maps to a servo angle of 0 degrees.
    # int() rounds it to a whole number since servos don't accept decimals
    return int(np.interp(angle, [100, 180], [100, 0]))

# A dictionary mapping each finger name to its 3 landmark numbers (tip, middle joint, knuckle). 
# These are fixed numbers defined by MediaPipe
FINGER_LANDMARKS = {
    "thumb":  (4, 3, 2),
    "index":  (8, 6, 5),
    "middle": (12, 10, 9),
    "ring":   (16, 14, 13),
    "pinky":  (20, 18, 17),
}

FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

# Stores the previous frame's servo angles, starting all fingers at the middle position (90)
prev_angles = [90, 90, 90, 90, 90]

# How much the new value blends with the old value each frame.
# 0 = servo never moves, 1 = no smoothing at all. 0.4 is a good middle ground
SMOOTHING = 0.4

# Loops forever as long as the camera is working
while cap.isOpened():
    # Grabs one frame of the camera. ret returns True/False depending on if it succeeded
    ret, frame = cap.read()
    if not ret:
        break

    # Mirrors the image horizontly so it feels like a mirror
    frame = cv2.flip(frame, 1)

    # Opencv stores images as Blue-Green-Red, but mediapipe expects Red-Green-Blue.
    # This line of code converts it
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Wraps the image in Mediapipe's own format so the detector can read it
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    # Runs the AI hand detector on the frame
    result = detector.detect(mp_image)

    if result.hand_landmarks:
        # Gets the landmarks for the hand. lm is now a list of 21 points, each
        # with an x, y, and z component
        lm = result.hand_landmarks[0]

        # Gets the height and width of the frame in pixels
        h, w, _ = frame.shape
        # Loops through all 21 landmarks. MediaPipe gives coordinates as 0.0–1.0 (percentages), 
        # so multiplying by width/height converts them to actual pixel positions. 
        for landmark in lm:
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

        # Find the angles of each finger
        angles = []

        # Loops through each finger, calculates the bend angle for each, maps it to a servo
        # angle, then blends it with the previous frame's value to smooth out jittery movement
        for i, (finger, (tip, pip, mcp)) in enumerate(FINGER_LANDMARKS.items()):
            raw_angle = get_finger_angle(lm, tip, pip, mcp)
            servo_val = angle_to_servo(raw_angle)

            # Blend the new value with the previous value.
            # e.g. if prev was 90 and new is 0: (90 * 0.6) + (0 * 0.4) = 54
            # The servo moves gradually instead of snapping instantly
            smoothed = int(prev_angles[i] * (1 - SMOOTHING) + servo_val * SMOOTHING)
            angles.append(smoothed)

        # Remember the smoothed angles for the next frame
        prev_angles = angles

        # Draws the finger name and servo angles on each screen. Each label is spaced
        # 30 pixels lower than the previous one
        for i, (name, val) in enumerate(zip(FINGER_NAMES, angles)):
            cv2.putText(frame, f"{name}: {val}", (10, 30 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Converts the list of angles into a string of angles
        msg = ','.join(map(str, angles)) + '\n'

        # Sends the string to Arduino over USB. encode() converts the string to bytes
        # since serial only accepts bytes
        try:
            # Clears messages python already sent but Arduino hasn't read yet.
            arduino.reset_input_buffer()
            # Clears messages python tried to send but got stuck in Python's own
            # outgoing queue.
            arduino.flushOutput()
            
            arduino.write(msg.encode())
            print("Sent:", msg.strip())
        except serial.SerialException:
            print("Arduino disconnected!")
            break

        # Waits 0.1 seconds before sending the next message (10 times per second).
        # This stops Python from flooding the Arduino faster than the servos can move
        time.sleep(0.1)

    # Shows the current frame, with dots and labels drawn on it, in a window called
    # "Hand Tracking"
    cv2.imshow("Hand Tracking", frame)
    key = cv2.waitKey(1) & 0xFF
    # Exits if you press 'q'
    if key == ord('q') or key == 27:
        break

# Properly releases the camera so other programs can use it
cap.release()
# Closes the video window
cv2.destroyAllWindows()
# Closes serial connection to the Arduino
arduino.close()