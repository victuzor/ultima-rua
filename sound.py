"""Efeitos curtos sintetizados localmente; áudio é opcional."""
from array import array
import math
import random

import pygame as pg


class Sounds:
    def __init__(self):
        self.enabled = True
        self.effects = {}
        mixer = pg.mixer.get_init()
        if not mixer or mixer[1] != -16:
            self.enabled = False
            return
        rate, _, channels = mixer
        rng = random.Random(9)
        for name, duration in (("blast", 0.32), ("pickup", 0.10), ("heal", 0.18), ("hurt", 0.13)):
            samples = array("h")
            for index in range(round(rate * duration)):
                t = index / rate
                fade = (1 - t / duration) ** 2
                if name == "blast":
                    value = (rng.uniform(-1, 1) * 0.6 + math.sin(math.tau * 55 * t) * 0.4) * fade * 0.3
                elif name == "hurt":
                    value = math.sin(math.tau * 90 * t) * fade * 0.12
                else:
                    frequency = 620 if name == "pickup" else 820
                    value = math.sin(math.tau * frequency * t) * fade * 0.08
                samples.extend([round(value * 32767)] * channels)
            self.effects[name] = pg.mixer.Sound(buffer=samples)

    def play(self, name):
        if self.enabled and name in self.effects:
            self.effects[name].play()

    def toggle(self):
        if self.effects:
            self.enabled = not self.enabled
