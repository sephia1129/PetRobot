
import time
import threading
from dataclasses import dataclass
from flask import Flask, jsonify, request, send_from_directory
 
app = Flask(__name__, static_folder="../frontend", static_url_path="")
 
# Check if running on Raspberry Pi
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    ON_PI = False


@dataclass
class Motors:

    name: str
    AIN1: int
    AIN2: int
    PWM: int
    STBY: int
    PWM_freq: int = 1000
    duty_cycle: int = 0

    def Setup(self):
        GPIOs = [self.AIN1, self.AIN2, self.PWM, self.STBY]
        for pin in GPIOs:
            GPIO.setup(pin, GPIO.OUT) #Make every pin an output

        GPIO.output(self.STBY, GPIO.HIGH) # Enable the driver chip
        self.pwm = GPIO.PWM(self.PWM, self.PWM_freq)
        self.pwm.start(self.duty_cycle) # Set duty cycle to 0 (off)

    #def Check(self):
    #    GPIOs = [self.AIN1, self.AIN2, self.PWM, self.STBY]
    #    for pin in GPIOs:
    #        return f"Pin {pin}: {GPIO.input(pin)}"

    def Forward(self, speed):
        if 0 <= speed <= 100:
            GPIO.output(self.AIN1, GPIO.HIGH)
            GPIO.output(self.AIN2, GPIO.LOW)
            self.pwm.ChangeDutyCycle(speed)
        else:
            raise ValueError("Speed must be between 0 and 100")

    def Backward(self, speed):
        if 0 <= speed <= 100:
            GPIO.output(self.AIN1, GPIO.LOW)
            GPIO.output(self.AIN2, GPIO.HIGH)
            self.pwm.ChangeDutyCycle(speed)
        else:
            raise ValueError("Speed must be between 0 and 100")

    def Stop(self):
        GPIO.output(self.AIN1, GPIO.LOW)
        GPIO.output(self.AIN2, GPIO.LOW)
        self.pwm.ChangeDutyCycle(0)

# Define global variables for the motors - further initialization will be done in the SetupMotors function
left_motors: "Motors | None" = None
right_motors: "Motors | None" = None

# Define a lock for thread-safe access to the robot state - Mulple threads may try to access the robot state at the same time, so we use a lock to prevent race conditions.
state_lock = threading.Lock()

# Define the default robot state
robot_state = {
    "connected": True,
    "name": "MiniCloud",
    "battery_percent": 87,
    "moving": False,
    "last_action": None,
}

def setup_motors():
    global left_motors, right_motors
    if not ON_PI:
        print("Not running on Raspberry Pi. GPIO setup skipped.")
        return
    GPIO.setmode(GPIO.BCM)
    left_motors = Motors("leftMotors", 17, 27, 12, 5)
    right_motors = Motors("rightMotors", 23, 24, 13, 6)
    left_motors.Setup()
    right_motors.Setup()


def _apply(motor: "Motors", value: float):
    """value is -1..1 (from drive()); convert to your Forward/Backward(0-100)."""
    speed = abs(value) * 100
    # 0.02 chosen for deadzone to prevent jittering when the joystick is near the center
    if value > 0.02:
        motor.Forward(speed)
    elif value < -0.02:
        motor.Backward(speed)
    else:
        motor.Stop()

def drive(x: float, y: float):
    """
    x, y are each in [-1, 1] from the joystick.
    y > 0 = forward, x > 0 = right. Convert to left/right wheel speeds
    (simple arcade-drive mixing) and send to your motor driver here.
    """
    left = max(-1.0, min(1.0, y + x))
    right = max(-1.0, min(1.0, y - x))
 
    with state_lock:
        robot_state["moving"] = abs(x) > 0.05 or abs(y) > 0.05
 
    if not ON_PI:
        print(f"[mock] drive left={left:+.2f} right={right:+.2f}")
        return
 
    _apply(left_motors, left)
    _apply(right_motors, right)

def stop():
    with state_lock:
        robot_state["moving"] = False
    if not ON_PI:
        print("[mock] stop")
        return
    left_motors.Stop()
    right_motors.Stop()

def do_action(name: str):
    """Canned behaviors triggered by the action buttons."""
    with state_lock:
        robot_state["last_action"] = name
    if not ON_PI:
        print(f"[mock] action: {name}")
        return
    # TODO: wire these up to servos / sound / LEDs, e.g.:
    # if name == "sit": ...
    # if name == "speak": ...
    # if name == "dance": ...


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route("/api/status")
def status():
    with state_lock:
        return jsonify(robot_state)
 
 
@app.route("/api/move", methods=["POST"])
def move():
    data = request.get_json(force=True) or {}
    x = float(data.get("x", 0))
    y = float(data.get("y", 0))
    drive(x, y)
    return jsonify({"ok": True})
 
 
@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop()
    return jsonify({"ok": True})
 
 
@app.route("/api/action/<name>", methods=["POST"])
def action(name):
    do_action(name)
    return jsonify({"ok": True, "action": name})
 
 
# Serve the PWA itself so the whole thing is one Flask app on one port.
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")
 
 
if __name__ == "__main__":
    setup_motors()
    app.run(host="0.0.0.0", port=5000, debug=False)
 