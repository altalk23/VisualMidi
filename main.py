from PIL import Image
import numpy as np
from mido import MidiFile

# Midi
trackcount, maxnote = 2, 8
data = np.zeros((trackcount, maxnote, 3), dtype=np.uint32)

mid = MidiFile('logic.mid')
for i, track in enumerate(mid.tracks):
    print('Track {}: {}'.format(i, track.name))
    # using note on note off for now
    for msg in track:
        if msg.type == 'note_on':
            pass
        elif if msg.type == 'note_off':
            pass

# Image
'''
w, h = 1920, 1080
data = np.zeros((h, w, 3), dtype=np.uint8)
data[0:256, 0:256] = [255, 127, 0] # red patch in upper left
img = Image.fromarray(data, 'RGB')
img.save('my.png')
'''
