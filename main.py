from PIL import Image
import numpy as np
from mido import MidiFile

# Midi
mid = MidiFile('logic.mid')


# Image
w, h = 1920, 1080
data = np.zeros((h, w, 3), dtype=np.uint8)
data[0:256, 0:256] = [255, 127, 0] # red patch in upper left
img = Image.fromarray(data, 'RGB')
img.save('my.png')
