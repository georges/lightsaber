import time
import board
import neopixel
import audioio
import busio
import adafruit_lis3dh
import microcontroller
import math
import pulseio
from digitalio import DigitalInOut, Direction, Pull
import analogio

from blade import Blade
from animated_blade import AnimatedBlade
from xmas_blade import XmasBlade

led = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1, auto_write=False)
led[0] = (0, 0, 255)
led.show()

switch_led = pulseio.PWMOut(board.D4)
 
switch = DigitalInOut(board.D9)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

power = DigitalInOut(board.D10)
power.direction = Direction.OUTPUT
power.value = False

vbat_voltage_pin = analogio.AnalogIn(board.VOLTAGE_MONITOR)

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 250
SWING_THRESHOLD = 125
IDLE_THRESHOLD = 110

NUM_PIXELS = 30                        # NeoPixel strip length (in pixels)
NVM_BLADE_INDEX = 0

strip = neopixel.NeoPixel(board.D5, NUM_PIXELS, brightness=1, auto_write=False)
audio = audioio.AudioOut(board.A0)     # Speaker

time.sleep(0.1)

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2
    
def play_wav(name, loop=False):
    try:
        wave_file = open('/' + name + '.wav', 'rb')
        wave = audioio.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except:
        return


def wake_up():
    global awake, setup, switch_led, power
    awake = True
    setup = False
    switch_led.duty_cycle = 0xffff
    power.value = True
    blade.off()
    
def sleep():
    global awake, setup, switch_led, power
    blade.off()
    audio.stop()
    switch_led.duty_cycle = 0x0000
    time.sleep(0.5)
    power.value = False
    awake = False
    setup = False

def settings():
    global awake, setup, switch_led, power
    setup = True
    awake = False
    power.value = True
    blade.off()

def blink_switch_led(count=1):
    global switch_led
    for i in range(count):
        switch_led.duty_cycle = 0xffff
        time.sleep(0.2)
        switch_led.duty_cycle = 0x0000
        time.sleep(0.1)
    
def swap_blade():
    global blade

    i = blades.index(blade)
    if i ==len(blades)-1:
        i = 0
    else:
        i = i+1
    blade = blades[i]
    microcontroller.nvm[NVM_BLADE_INDEX] = i

awake = False
setup = False

purple_blade = Blade(Blade.hsv_to_rgb(5/6, 1.0, 1.0), NUM_PIXELS, strip, audio)
jedi_blade = Blade((0, 100, 255), NUM_PIXELS, strip, audio)
sith_blade = Blade((255, 0, 0), NUM_PIXELS, strip, audio)
yoda_blade = Blade(Blade.hsv_to_rgb(2/6, 1.0, 1.0), NUM_PIXELS, strip, audio)
unicorn = AnimatedBlade(NUM_PIXELS, strip, audio)
xmas_blade = XmasBlade(NUM_PIXELS, strip, audio)

blades = (purple_blade, jedi_blade, sith_blade, yoda_blade, unicorn, xmas_blade)

blade = blades[microcontroller.nvm[NVM_BLADE_INDEX]]

blade.off()

breath_angle = 0
last_breath_at = time.monotonic()
low_battery_angle = 0

while True:

    # Button pressed
    if not switch.value:
        last_motion_at = time.monotonic()
        switched_pressed_duration = 0
        switch_pressed_at = time.monotonic()
        time.sleep(0.1)

        # Detect long press for setup mode
        while not switch.value:
            switched_pressed_duration = time.monotonic() - switch_pressed_at
            if switched_pressed_duration >= 2.0:
                break
            time.sleep(0.2)            

        if switched_pressed_duration >= 2.0 and not awake:
            if not setup:
                settings()
                play_wav('settings')
                blink_switch_led(4)
                blade.show_mode()
            else:
                play_wav('settings')
                blink_switch_led(4)
                sleep()
        elif setup:
            swap_blade()
            play_wav('chime')
            blade.show_mode()
        elif awake:
            blade.power_down()
            sleep()
        else:
            wake_up()
            blade.power_up()
        
    # Motion detection
    if awake or setup:
        x, y, z = accel.acceleration
        accel_squared = z * z + x * x
        
        if accel_squared > IDLE_THRESHOLD:
            last_motion_at = time.monotonic()
            
        if (time.monotonic() - last_motion_at) > 90.0:
            blink_switch_led(8)
            if awake:
                blade.power_down()
            sleep()
            
    # Action loop
    if awake and not setup:
        if accel_squared > HIT_THRESHOLD:
            blade.hit()
        elif accel_squared > SWING_THRESHOLD:
            blade.swing()
        
        blade.animate()
        
    # Breathe LED
    if not awake and not setup:                
        if (time.monotonic() - last_breath_at) > 0.012:
            voltage = get_voltage(vbat_voltage_pin)
            if voltage < 3.65:
                # Fast blink for low battery
                breath_angle += 8
            else:                    
                switch_led.duty_cycle = int((math.sin(math.radians(breath_angle))+1) * 0x1fff)
                last_breath_at = time.monotonic()
                breath_angle += 1
                if breath_angle > 359:
                    breath_angle = 0