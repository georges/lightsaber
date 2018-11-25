import time
import audioio
import math
import gc

class Blade:  
    def __init__(self, color, nb_pixels, strip, audio):
        self.nb_pixels = nb_pixels
        self.strip = strip
        self.audio = audio

        self.color_idle = (int(color[0] / 3), int(color[1] / 3), int(color[2] / 3))
        self.color_swing = color
        self.color_hit = (255, 255, 255)
        
        self.audio_path = 'light_saber_sounds'
        
        self.state = 'off'
        
    def hsv_to_rgb(hue, saturation, value):
        """
        Convert HSV color (hue, saturation, value) to RGB (red, green, blue)
        @param hue:        0=Red, 1/6=Yellow, 2/6=Green, 3/6=Cyan, 4/6=Blue, etc.
        @param saturation: 0.0=Monochrome to 1.0=Fully saturated
        @param value:      0.0=Black to 1.0=Max brightness
        @returns: red, green, blue eacn in range 0 to 255
        """
        hue = hue * 6.0       # Hue circle = 0.0 to 6.0
        sxt = math.floor(hue) # Sextant index is next-lower integer of hue
        frac = hue - sxt      # Fraction-within-sextant is 0.0 to <1.0
        sxt = int(sxt) % 6    # mod6 the sextant so it's always 0 to 5

        if sxt == 0: # Red to <yellow
            red, green, blue = 1.0, frac, 0.0
        elif sxt == 1: # Yellow to <green
            red, green, blue = 1.0 - frac, 1.0, 0.0
        elif sxt == 2: # Green to <cyan
            red, green, blue = 0.0, 1.0, frac
        elif sxt == 3: # Cyan to <blue
            red, green, blue = 0.0, 1.0 - frac, 1.0
        elif sxt == 4: # Blue to <magenta
            red, green, blue = frac, 0.0, 1.0
        else: # Magenta to <red
            red, green, blue = 1.0, 0.0, 1.0 - frac

        invsat = 1.0 - saturation # Inverse-of-saturation

        red = int(((red * saturation) + invsat) * value * 255.0 + 0.5)
        green = int(((green * saturation) + invsat) * value * 255.0 + 0.5)
        blue = int(((blue * saturation) + invsat) * value * 255.0 + 0.5)

        return red, green, blue

    def play_wav(self, name, loop=False):
        """
        Play a WAV file in the 'sounds' directory.
        @param name: partial file name string, complete name will be built around
                     this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
        @param loop: if True, sound will repeat indefinitely (until interrupted
                     by another sound).
        """
        try:
            wave_file = open(self.audio_path + '/' + name + '.wav', 'rb')
            wave = audioio.WaveFile(wave_file)
            self.audio.play(wave, loop=loop)
        except:
            return

    def power_up(self):
        self.power_animation('on', 1.7, False)
        self.state = 'idle'
        self.play_wav('idle', loop=True)

    def power_down(self):
        self.power_animation('off', 1.15, True)
        self.state = 'off'
        
    def off(self):
        self.strip.fill(0)
        self.strip.show()
        
    def show_mode(self):
        self.strip.fill(self.color_idle)
        self.strip.show()

    def hit(self):
        self.triggered = time.monotonic()
        self.play_wav('hit')
        self.color_active = self.color_hit
        self.state = 'hit'

    def swing(self):
        if self.state == 'idle':
            self.triggered = time.monotonic()
            self.play_wav('swing')
            self.color_active = self.color_swing
            self.state = 'swing'
        
    def animate(self):
        if self.state == 'swing' or self.state == 'hit':
            if self.audio.playing:
                blend = time.monotonic() - self.triggered
                if self.state == 'swing':
                    blend = abs(0.5 - blend) * 2.0
                self.strip.fill(self.mix(self.color_active, self.color_idle, blend))
                self.strip.show()
            else:
                self.play_wav('idle', loop=True)
                self.strip.fill(self.color_idle)
                self.strip.show()
                self.state = 'idle'

    def mix(self, color_1, color_2, weight_2):
        """
        Blend between two colors with a given ratio.
        @param color_1:  first color, as an (r,g,b) tuple
        @param color_2:  second color, as an (r,g,b) tuple
        @param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
        @return: (r,g,b) tuple, blended color
        """
        if weight_2 < 0.0:
            weight_2 = 0.0
        elif weight_2 > 1.0:
            weight_2 = 1.0
        weight_1 = 1.0 - weight_2
        return (int(color_1[0] * weight_1 + color_2[0] * weight_2),
                int(color_1[1] * weight_1 + color_2[1] * weight_2),
                int(color_1[2] * weight_1 + color_2[2] * weight_2))

    def power_animation(self, sound, duration, reverse):
        """
        Animate NeoPixels with accompanying sound effect for power on / off.
        @param sound:    sound name (similar format to play_wav() above)
        @param duration: estimated duration of sound, in seconds (>0.0)
        @param reverse:  if True, do power-off effect (reverses animation)
        """
        if reverse:
            prev = self.nb_pixels
        else:
            prev = 0
        gc.collect()
        start_time = time.monotonic()
        self.play_wav(sound)
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > duration:
                break                  
            fraction = elapsed / duration            # Animation time, 0.0 to 1.0
            if reverse:
                fraction = 1.0 - fraction            # 1.0 to 0.0 if reverse
            fraction = math.pow(fraction, 0.5)       # Apply nonlinear curve
            threshold = int(self.nb_pixels * fraction + 0.5)
            num = threshold - prev
            if num != 0:
                if reverse:
                    self.strip[threshold:prev] = [0] * -num
                else:
                    self.strip[prev:threshold] = [self.color_idle] * num
                self.strip.show()
                # NeoPixel writes throw off time.monotonic() ever so slightly
                # because interrupts are disabled during the transfer.
                # We can compensate somewhat by adjusting the start time
                # back by 30 microseconds per pixel.
                start_time -= self.nb_pixels * 0.00003
                prev = threshold

        if reverse:
            self.strip.fill(0)                            # At end, ensure strip is off
        else:
            self.strip.fill(self.color_idle)                   # or all pixels set on
        self.strip.show()
        while self.audio.playing:                         # Wait until audio done
            pass