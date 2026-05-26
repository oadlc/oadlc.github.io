#include <Servo.h>

// Creates 5 servo objects, one for each finger
Servo thumb, index, middle, ring, pinky;

void setup() {
  // Starts serial communication at 9600 baud
  Serial.begin(9600);

  // Tells the servo which pin its connected to
  thumb.attach(7);
  index.attach(6);
  middle.attach(5);
  ring.attach(4);
  pinky.attach(3);
}

void loop() {
  // Checks if any data has been recieved by python
  if (Serial.available()) {

    // Keeps looping as long as there are messages waiitng in the buffer
    // Reads all of the messages.
    while (Serial.available() > 0) {

      // Reads one message from the buffer. It's called discard because most
      // of the time we're going to throw it away. We only care about the last one.
      // We need this bit of code because python sends messages via USB to the Arduino
      // faster than the Arduino can process them: so the messages pile up. For example,
      // by the time the Arduino finishes moving the servos from the first message, there are 
      // already 3 or 4 old messages waiting. To fix this, we drain the queue and only act
      // on the last message.
      String discard = Serial.readStringUntil('\n');

      // Checks if the buffer is now empty after that read
      if (Serial.available() == 0) {
        // An empty array to store 5 angles
        int angles[5];
        int idx = 0;

        // Converts the Arduino string into a plain char string
        char buf[40];
        discard.toCharArray(buf, 40);

        // Splits the string to commas and returns the first chunk
        char* token = strtok(buf, ",");

        // Keeps looping as long as there are more chunks to read and we haven't
        // filled all 5 fingers yet
        while (token != NULL && idx < 5) {
          // atoi() turns an ascii character to an int
          angles[idx] = atoi(token);
          idx++;

          // Gets the next comma seperated chunk. Passing NULL tells strtok
          // to continue where it left off.
          token = strtok(NULL, ",");
        }
        // Write to the servos while making sure the angles are constrained: 0 <angle < 180.
        if (idx == 5) {
          thumb.write(constrain(angles[0], 0, 180));
          index.write(constrain(angles[1], 0, 180));
          middle.write(constrain(angles[2], 0, 180));
          ring.write(constrain(angles[3], 0, 180));
          pinky.write(constrain(angles[4], 0, 180));
        }
      }
    }
  }
}