from umqttsimple import MQTTClient
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD
import machine
import sys
import time
import ubinascii
import utime
import _thread
import ntptime


#if needed, overwrite default time server
ntptime.host = "0.uk.pool.ntp.org"


firmware_url = "https://raw.githubusercontent.com/giz1007/phyto/main/"

# MQTT Configuration
MQTT_BROKER = '192.168.10.52'
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
MQTT_TOPIC_DURATION = "phyto_box/duration"
MQTT_TOPIC_LOGS = "phyto_box/logs"
MQTT_TOPIC_SPEED = "phyto_box/speed"
MQTT_TOPIC_INTERVAL = "phyto_box/interval"
MQTT_TOPIC_UPDATE = "phyto_box/update"  # New topic for individual mixing requests

# Define the maximum allowed duration for the stirrer
MAX_STIRRER_DURATION = 10  # 2 minutes in seconds

# Define the default time interval for stirrer operation
DEFAULT_STIRRER_OPERATION_INTERVAL = 20 # * 60 * 60  3 hours in seconds move the #
current_interval = DEFAULT_STIRRER_OPERATION_INTERVAL

# Define the list of stirrer names
STIRRER_NAMES = ["stirrer1", "stirrer2", "stirrer3","stirrer4"]

# Placeholder for stirrer pin configuration
DOSING_STIRRERS = {
    "stirrer1": {"pin": 25},  # Replace 1 with the actual pin number for stirrer1
    "stirrer2": {"pin": 18},  # Replace 5 with the actual pin number for stirrer2
    "stirrer3": {"pin": 27},  # Replace 6 with the actual pin number for stirrer3
    "stirrer4": {"pin": 32},  # Replace 6 with the actual pin number for stirrer3

}


# Placeholder for stirrer speed configuration (adjust as needed)
STIRRER_SPEEDS = {
    "stirrer1": {"constant_speed": 70, "acceleration": 30, "deceleration": 10},
    "stirrer2": {"constant_speed": 40, "acceleration": 15, "deceleration": 10},
    "stirrer3": {"constant_speed": 65, "acceleration": 30, "deceleration": 10},
    "stirrer4": {"constant_speed": 60, "acceleration": 30, "deceleration": 10},
}

# Global variables for dynamic configuration
stirrer_operation_intervals = {stirrer_name: DEFAULT_STIRRER_OPERATION_INTERVAL for stirrer_name in STIRRER_NAMES}


#read and write a request to update the main file from the system.
def read_update():
    try:
        with open(f"update.txt", "r") as file:
            return int(file.read())
    except OSError:
        return None  # Return None if file doesn't exist

def write_update(update):
    try:
        with open(f"update.txt", "w") as file:
            file.write(str(update))
    except OSError:
        print(f"Failed to write speed for {stirrer_name} to file.")

# Function to read stirrer interval from file
def read_stirrer_interval():
    try:
        with open("stirrer_interval.txt", "r") as file:
            return int(file.read())
    except OSError:
        # If the file doesn't exist, return the default interval
        print(f"Failed to read interval from file:")
        return DEFAULT_STIRRER_OPERATION_INTERVAL

# Function to write stirrer interval to file
def write_stirrer_interval(interval):
    try:
        with open("stirrer_interval.txt", "w") as file:
            file.write(str(interval))
        
    except OSError:
        print(f"Failed to write interval to file:")

# Function to publish stirrer interval via MQTT
def publish_interval(interval):
    mqtt_client.publish(MQTT_TOPIC_INTERVAL, str(interval))
    log_message = f"Published interval: {interval} seconds."
    publish_log(log_message)


# Function to read stirrer duration from file
def read_stirrer_duration():
    try:
        with open("stirrer_duration.txt", "r") as file:
            return int(file.read())
    except OSError:
        # If the file doesn't exist, return the default duration
        return MAX_STIRRER_DURATION

# Function to write stirrer duration to file
def write_stirrer_duration(duration):
    try:
        with open("stirrer_duration.txt", "w") as file:
            file.write(str(duration))
    except OSError:
        print(f"Failed to write duration for {stirrer_name} to file:")
        
# Function to publish stirrer interval via MQTT
def publish_duration(duration):
    mqtt_client.publish(MQTT_TOPIC_duration, str(duration))
    log_message = f"Published duration: {duration} seconds."
    publish_log(log_message)        


def read_speed(stirrer_name):
    try:
        with open(f"{stirrer_name}_speed.txt", "r") as file:
            return int(file.read())
    except OSError:
        return None  # Return None if file doesn't exist

def write_speed(stirrer_name, speed):
    try:
        with open(f"{stirrer_name}_speed.txt", "w") as file:
            file.write(str(speed))
    except OSError:
        print(f"Failed to write speed for {stirrer_name} to file.")

def read_acceleration(stirrer_name):
    try:
        with open(f"{stirrer_name}_acceleration.txt", "r") as file:
            return int(file.read())
    except OSError:
        return None

def write_acceleration(stirrer_name, acceleration):
    try:
        with open(f"{stirrer_name}_acceleration.txt", "w") as file:
            file.write(str(acceleration))
    except OSError:
        print(f"Failed to write acceleration for {stirrer_name} to file.")

def read_deceleration(stirrer_name):
    try:
        with open(f"{stirrer_name}_deceleration.txt", "r") as file:
            return int(file.read())
    except OSError:
        return None

def write_deceleration(stirrer_name, deceleration):
    try:
        with open(f"{stirrer_name}_deceleration.txt", "w") as file:
            file.write(str(deceleration))
    except OSError:
        print(f"Failed to write deceleration for {stirrer_name} to file.")

# Function to publish log messages via MQTT
def publish_log(message):
    mqtt_client.publish(MQTT_TOPIC_LOGS, message)
    print(f"Published log message: {message}")

# Function to publish stirrer speed via MQTT
def publish_speed(stirrer_name, speed, acceleration, deceleration):
    speed_msg = f"{speed},{acceleration},{deceleration}"
    mqtt_client.publish(f"{MQTT_TOPIC_SPEED}/{stirrer_name}", speed_msg)
    log_message = f"Published {stirrer_name} speed: {speed}, acceleration: {acceleration}, deceleration: {deceleration}."
    publish_log(log_message)



# Function to publish mix request via MQTT
def publish_mix_request(stirrer_name, duration):
    mqtt_client.publish(f"{MQTT_TOPIC_MIX}/{stirrer_name}", str(duration))
    log_message = f"Published {stirrer_name} mix request: {duration} seconds."
    publish_log(log_message)

# Function to monitor the stirrer's duration
def stirrer_monitor(stirrer_name, start_time):
    while True:
        current_time = utime.time()
        elapsed_time = current_time - start_time

        if elapsed_time > read_stirrer_duration():
            log_message = f"Exceeded maximum duration. Stopping stirrer."
            publish_log(log_message)

            # Turn off the stirrer
            stirrer_pin = machine.Pin(DOSING_STIRRERS[stirrer_name]["pin"], machine.Pin.OUT)
            pwm = machine.PWM(stirrer_pin)
            pwm.duty(0)
            pwm.deinit()
            stirrer_pin_off = machine.Pin(DOSING_STIRRERS[stirrer_name]["pin"], machine.Pin.OUT)            
            stirrer_pin_off.value(0)
            break

        utime.sleep_us(int(500000))  # Adjust the sleep duration as needed

# Function to control stirrer acceleration
def accelerate_stirrer(pwm, acceleration):
    for step in range(3):
        pwm.duty(int((step + 1) * acceleration * 200 / 100))
        utime.sleep_us(int(500000))
        print("Accelerating stirrer: Step", step + 1)

# Function to maintain constant speed of stirrer
def maintain_constant_speed(pwm, constant_speed, duration):
    pwm.duty(int(constant_speed * 200 / 100))
    print("Stirrer at constant speed")
    utime.sleep_us(int(duration * 1000000))
    print("Stirrer maintaining speed for", duration, "seconds")

# Function to control stirrer deceleration
def decelerate_stirrer(pwm, deceleration):
    for step in range(3):
        pwm.duty(int((3 - step) * deceleration * 200 / 100))
        utime.sleep_us(int(500000))
        print("Decelerating stirrer: Step", step + 1)

# Function to control stirrers every configured interval for configured duration
def control_stirrers():
    print("Checking interval sequence")
    for stirrer_name in STIRRER_NAMES:
        try:
            log_message = f"Turning {stirrer_name} on for {read_stirrer_duration()} seconds..."
            publish_log(log_message)

            start_time = utime.time()

            stirrer_pin = machine.Pin(DOSING_STIRRERS[stirrer_name]["pin"], machine.Pin.OUT)
            pwm = machine.PWM(stirrer_pin)
            pwm.freq(1000)

            acceleration = read_acceleration(stirrer_name)
            constant_speed = read_speed(stirrer_name)  # Read speed from file
            deceleration = read_deceleration(stirrer_name)
            
            # If reading fails, use default values from STIRRER_SPEEDS dictionary
            if constant_speed is None:
                constant_speed = STIRRER_SPEEDS[stirrer_name]["constant_speed"]
            if acceleration is None:
                acceleration = STIRRER_SPEEDS[stirrer_name]["acceleration"]
            if deceleration is None:
                deceleration = STIRRER_SPEEDS[stirrer_name]["deceleration"]
            
            # Acceleration phase
            accelerate_stirrer(pwm, acceleration)

            # Constant speed phase
            maintain_constant_speed(pwm, constant_speed, read_stirrer_duration())

            # Deceleration phase
            decelerate_stirrer(pwm, deceleration)

            # Turn off the stirrer
            pwm.duty(0)
            pwm.deinit()

            log_message = f"Turning {stirrer_name} off."
            publish_log(log_message)

            # Start the stirrer monitor without threading
            stirrer_monitor(stirrer_name, start_time)
            stirrer_pin_off = machine.Pin(DOSING_STIRRERS[stirrer_name]["pin"], machine.Pin.OUT)            
            stirrer_pin_off.value(0)

        except Exception as e:
            log_message = f"Failed to control {stirrer_name}: {e}"
            publish_log(log_message)

    # Wait for the next operation interval for each stirrer
    utime.sleep(read_stirrer_interval())
   

def mqtt_callback(topic, msg):
    print(f"Received message: {msg} on topic: {topic}")
    global stirrer_operation_intervals

    try:
        # Update interval
        if topic.endswith(b"/interval"):
            interval = int(msg.decode('utf-8'))
            write_stirrer_interval(interval)  # Save interval to file
            log_message = f"Updated interval to {interval} seconds."
            #publish_interval(interval)  # Publish updated interval
            print(log_message)  # Debugging

        # Update duration
        elif topic.endswith(b"/duration"):
            duration = int(msg.decode('utf-8'))
            write_stirrer_duration(duration)
            log_message = f"Updated duration to {duration} seconds."
            #publish_log(log_message)
            print(log_message)  # Debugging
        
        elif topic.endswith(b"/update"):
            log_message = f"updatemain_request_received."
            # the update here is 1 
            interval = int(msg.decode('utf-8'))
            print(log_message)  # Debugging
            write_update(interval)

        else:
            stirrer_name, parameter = topic.split(b"/")[1:]  # Extract stirrer name and parameter
            stirrer_name = stirrer_name.decode('utf-8')
            parameter = parameter.decode('utf-8')
            print(f"The stirrer_name being noted is {stirrer_name}")  # Debugging
            if stirrer_name in STIRRER_NAMES:
                # Update speed
                if parameter == "speed":
                    speed = int(msg)
                    write_speed(stirrer_name, speed)  # Save speed to file
                    log_message = f"Updated {stirrer_name} speed to {speed}."
                    #publish_speed(stirrer_name, speed)  # Publish updated speed
                    print(log_message)  # Debugging

                # Update acceleration
                elif parameter == "acceleration":
                    acceleration = int(msg)
                    write_acceleration(stirrer_name, acceleration)  # Save acceleration to file
                    log_message = f"Updated {stirrer_name} acceleration to {acceleration}."
                   #publish_acceleration(stirrer_name, acceleration)  # Publish updated acceleration
                    print(log_message)  # Debugging

                # Update deceleration
                elif parameter == "deceleration":
                    deceleration = int(msg)
                    write_deceleration(stirrer_name, deceleration)  # Save deceleration to file
                    log_message = f"Updated {stirrer_name} deceleration to {deceleration}."
                   # publish_deceleration(stirrer_name, deceleration)  # Publish updated deceleration
                    print(log_message)  # Debugging

                elif parameter == "mix":
                    mix_duration = int(msg)
                   # publish_mix_request(stirrer_name, mix_duration)
                    print(f"Published mix request for {stirrer_name}: {mix_duration} seconds")  # Debugging

            else:
                log_message = f"Ignored message for unknown stirrer: {stirrer_name}"
                #publish_log(log_message)
                print(log_message)  # Debugging

    except Exception as e:
        log_message = f"Failed to process control message: {e}"
        #publish_log(log_message)
        print(log_message)  # Debugging

# MQTT client setup
mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
mqtt_client.set_callback(mqtt_callback)
mqtt_client.connect()
print("Connected to MQTT broker")

mqtt_client.subscribe(b"{}/#".format(MQTT_TOPIC_DURATION))
mqtt_client.subscribe(b"{}/#".format(MQTT_TOPIC_SPEED))
mqtt_client.subscribe(b"{}/#".format(MQTT_TOPIC_INTERVAL))
mqtt_client.subscribe(b"{}/#".format(MQTT_TOPIC_UPDATE)) 

# Main loop to handle MQTT messages and stirrer control
# Define a function to be run in a thread for handling MQTT messages
def mqtt_thread():
    while True:
        mqtt_client.check_msg()
        time.sleep(1)

# Start the MQTT thread
_thread.start_new_thread(mqtt_thread, ())

# Main loop to control stirrers
try:

    #ntptime.settime()
    print("Local time after synchronization：%s" %str(time.localtime()))
    while True:           
        control_stirrers()
        time.sleep(1)
        update_triggered = read_update()
        print({update_triggered})
        if update_triggered == 1:
            write_update("0")
            ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "main.py")
            ota_updater.download_and_install_update_if_available()
        
except Exception as e:
    # "should" never get here.  
    # Save exception to a file and force a hard reset
    emsg = 'Unexpected Exception {} {}\n'.format(type(e).__name__, e)
    print(emsg)
    with open('exception.txt', mode='at', encoding='utf-8') as f:
        f.write(emsg)
    machine.reset()
