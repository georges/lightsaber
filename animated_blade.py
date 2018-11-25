import time
import math
import random
import gc
from blade import Blade
from neopixel_write import neopixel_write

FRAMES = 10

class AnimatedBlade(Blade):

    def __init__(self, nb_pixels, strip, audio):
        Blade.__init__(self, (0, 0, 0), nb_pixels, strip, audio)

        self.color_idle = bytearray(nb_pixels * strip.bpp)
        self.color_swing = [bytearray(nb_pixels * strip.bpp) for i in range(FRAMES)]
        self.color_hit = [bytearray(nb_pixels * strip.bpp) for i in range(FRAMES)]

        self.audio_path = 'rainbow_sounds'
        
        self.previous_frame = -1
        index = 0
        for pixel in range(nb_pixels):
            hue = pixel / nb_pixels
            r, g, b = Blade.hsv_to_rgb(hue, 1.0, 0.2)
            self.color_idle[index + strip.order[0]] = r
            self.color_idle[index + strip.order[1]] = g
            self.color_idle[index + strip.order[2]] = b
            for frame in range(FRAMES):
                fraction = frame / (FRAMES - 1)
                r, g, b = Blade.hsv_to_rgb(hue + fraction, fraction, 1.0 - 0.8 * fraction)
                self.color_hit[frame][index + strip.order[0]] = r
                self.color_hit[frame][index + strip.order[1]] = g
                self.color_hit[frame][index + strip.order[2]] = b
                r, g, b = Blade.hsv_to_rgb(hue + fraction, 1.0, 1.0 - 0.8 * fraction)
                self.color_swing[frame][index + strip.order[0]] = r
                self.color_swing[frame][index + strip.order[1]] = g
                self.color_swing[frame][index + strip.order[2]] = b
            index += 3

        # Go back through the hit animation and randomly set one
        # pixel per frame to white to create a sparkle effect.
        for frame in range(FRAMES):
            index = random.randint(0, nb_pixels - 1) * 3
            self.color_hit[frame][index] = 255
            self.color_hit[frame][index + 1] = 255
            self.color_hit[frame][index + 2] = 255

    def power_animation(self, sound, duration, reverse):
        """
        Animate NeoPixels with accompanying sound effect for power on / off.
        @param sound:    sound name (similar format to play_wav() above)
        @param duration: estimated duration of sound, in seconds (>0.0)
        @param reverse:  if True, do power-off effect (reverses animation)
        """
        gc.collect()
        start_time = time.monotonic()  # Save function start time
        self.play_wav(sound)
        while True:
            elapsed = time.monotonic() - start_time  # Time spent in function
            if elapsed > duration:                   # Past sound duration?
                break                                # Stop animating
            fraction = elapsed / duration            # Animation time, 0.0 to 1.0
            if reverse:
                fraction = 1.0 - fraction            # 1.0 to 0.0 if reverse
            fraction = math.pow(fraction, 0.5)       # Apply nonlinear curve
            threshold = int(self.nb_pixels * fraction + 0.5)
            idx = 0
            for pixel in range(self.nb_pixels):          # Fill NeoPixel strip
                if pixel <= threshold:
                    self.strip[pixel] = (                 # BELOW threshold,
                        self.color_idle[idx + self.strip.order[0]],  # fill pixels with
                        self.color_idle[idx + self.strip.order[1]],  # IDLE pattern
                        self.color_idle[idx + self.strip.order[2]])
                else:
                    self.strip[pixel] = 0                 # OFF pixels ABOVE threshold
                idx += 3
            self.strip.show()
            # NeoPixel writes throw off time.monotonic() ever so slightly
            # because interrupts are disabled during the transfer.
            # We can compensate somewhat by adjusting the start time
            # back by 30 microseconds per pixel.
            start_time -= self.nb_pixels * 0.00003

        if reverse:
            self.strip.fill(0)                            # At end, ensure strip is off
            self.strip.show()
        else:
            neopixel_write(self.strip.pin, self.color_idle)          # or all pixels set on
        while self.audio.playing:                         # Wait until audio done
            pass

    def animate(self):
        if self.state == 'swing' or self.state == 'hit':
            if self.audio.playing:
                blend = time.monotonic() - self.triggered
                if self.state == 'swing':
                    blend = abs(0.5 - blend) * 2.0
                if blend > 1.0:
                    blend = 1.0
                elif blend < 0.0:
                    blend = 0.0
                frame = int(blend * (FRAMES - 1) + 0.5)
                if frame != self.previous_frame:
                    neopixel_write(self.strip.pin, self.color_active[frame])
                    self.previous_frame = frame
            else:
                self.previous_frame = -1
                self.play_wav('idle', loop=True)
                neopixel_write(self.strip.pin, self.color_idle)
                self.state = 'idle'

    def show_mode(self):
        neopixel_write(self.strip.pin, self.color_idle)

    def power_up(self):
        self.power_animation('on', 2.8, False)
        self.state = 'idle'
        self.play_wav('idle', loop=True)

    def power_down(self):
        self.power_animation('off', 1.8, True)
        self.state = 'off'