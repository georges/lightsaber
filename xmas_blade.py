import time
import math
import random
import gc
from animated_blade import AnimatedBlade
from blade import Blade
from neopixel_write import neopixel_write

FRAMES = 20

class XmasBlade(AnimatedBlade):
    
    def __init__(self, nb_pixels, strip, audio):
        AnimatedBlade.__init__(self, nb_pixels, strip, audio)

        self.color_idle = bytearray(nb_pixels * strip.bpp)
        self.color_swing = [bytearray(nb_pixels * strip.bpp) for i in range(FRAMES)]
        self.color_hit = [bytearray(nb_pixels * strip.bpp) for i in range(FRAMES)]

        self.audio_path = 'xmas_sounds'
        
        self.previous_frame = -1

        index = 0
        sequence = 0
        for pixel in range(nb_pixels):
            if sequence <= 2:
                self.color_idle[index + strip.order[0]] = int(255 / 3)
                self.color_idle[index + strip.order[1]] = 0
                self.color_idle[index + strip.order[2]] = 0
            else:
                self.color_idle[index + strip.order[0]] = int(255 / 3)
                self.color_idle[index + strip.order[1]] = int(255 / 3)
                self.color_idle[index + strip.order[2]] = int(255 / 3)
            sequence += 1            
            if sequence > 5:
                sequence = 0
            index += 3


        for frame in range(FRAMES):
            index = 0
            for pixel in range(nb_pixels):                
                offset = (frame * 3) + index

                if offset / 3 > nb_pixels-1:
                    offset = offset % (nb_pixels * 3)

                self.color_hit[frame][index + strip.order[0]] = self.color_idle[index + strip.order[0]] * 3
                self.color_hit[frame][index + strip.order[1]] = self.color_idle[index + strip.order[1]] * 3
                self.color_hit[frame][index + strip.order[2]] = self.color_idle[index + strip.order[2]] * 3

                self.color_swing[frame][index + strip.order[0]] = self.color_idle[offset + strip.order[0]]
                self.color_swing[frame][index + strip.order[1]] = self.color_idle[offset + strip.order[1]]
                self.color_swing[frame][index + strip.order[2]] = self.color_idle[offset + strip.order[2]]
                
                index += 3
    
    def power_up(self):
        self.power_animation('on', 3.5, False)
        self.state = 'idle'
        self.play_wav('idle', loop=True)