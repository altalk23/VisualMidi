from PIL import Image
import numpy as np
from mido import MidiFile

# Midi
trackcount, maxnote = 3, 8
data = np.zeros((trackcount, maxnote, 4), dtype=np.uint32)
idx = [0,0,0]
time = 0
cont = np.full((128), -1, dtype=np.int32)

mid = MidiFile('logic.mid')
for trackidx, track in enumerate(mid.tracks):
    print('Track {}: {}'.format(trackidx, track.name))
    # using note on note off for now
    time = 0
    for msg in track:
        if not msg.is_meta: print(msg)
        print('')
        time += msg.time

        if msg.type == 'note_on':
            data[trackidx][idx[trackidx]] = [time, msg.note, msg.velocity, 0]
            cont[msg.note] = trackidx
            idx[trackidx] += 1
            pass

        elif msg.type == 'note_off':
            data[trackidx][cont[msg.note]][3] = time
            cont[msg.note] = -1
            pass

print(data)

# Image
'''
w, h = 1920, 1080
data = np.zeros((h, w, 3), dtype=np.uint8)
data[0:256, 0:256] = [255, 127, 0] # red patch in upper left
img = Image.fromarray(data, 'RGB')
img.save('my.png')
'''
