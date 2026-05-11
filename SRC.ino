#include <Servo.h>

#define SERVO_PIN 9
#define IR_PIN A0

// Create a servo object
Servo myservo;

//PID Constants (keep it at 0 for now because we don't know)
float kP = 18;
float kI = .2;
float kD = 5;
float reference_dist = 25;  // So that we can make the beam 30 cm long?
double actual_dist, error, P, I, D, PID;
double now, dt;
double prev_error = 0, prev_time = 0;

// Functions
double pid_controller(double error, double dt);
float find_dist(int n);

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(IR_PIN, INPUT);
  myservo.attach(SERVO_PIN);

}

void loop() {
  // put your main code here, to run repeatedly:
  // Use millis to find the time, and if less than 20 miliseconds have passed, exit the loop
  now = millis();
  if (now - prev_time < 20) return;
  // Turns miliseconds into seconds
  dt = (now - prev_time) / 1000;
  prev_time = now;

  // Find the distance from the IR sensor and sample it 10 times
  // Find the error to be inputed into the PID controller
  actual_dist = find_dist(10); 
  error = reference_dist - actual_dist;
  double output = pid_controller(error, dt);
  
  // Write it out to the servo
  // Map the PID output to the servo, and clamp it to the valid distance listed on the IR Sensor (10-80cm)
  if (10 < actual_dist || actual_dist > 80)
  {
    Serial.println("Out of range");
  }
  else
  {
    // The range -150 to 150 is aribitrary for now (we could get different values in reality)
    // I'm mapping it to 70-110 degrees so that the servo doesn't turn a lot and thus overcompensate
    long turn = map(output, -200, 200, 60, 120);
    myservo.write(turn);
  }
}

// Implements the actual PID controller with the proportional, integral, and derivative terms
double pid_controller(double error, double dt){
  // Declare integral as static so that it may
  // change on next iterations
  static double integral;
  // Proportional term
  P = kP * error;
  // Integral term
  integral += error * dt;
  I = kI * integral;
  // Derivative term
  D = kD * (error - prev_error)/dt;
  prev_error = error;

  PID = P + I + D;
  return PID;

}

// This function first samples 10 analog reads and takes the average of them
// From the average, it finds the distance using the formula from the data sheet
float find_dist(int n){
  float sum = 0.0;
  for (int i = 0; i < n; i++){
    sum += analogRead(IR_PIN);
  }
  float ADC_val = sum / n;
  // Convert ADC val to voltage
  float voltage = ADC_val * (5.0/1023.0);
  // turn ADC value into a distance
  float dist = 27.86 * pow(voltage, -1.15);

  return dist;
}
