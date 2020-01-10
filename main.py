from PIL import Image
import numpy as np
from mido import MidiFile, tempo2bpm

# Midi
trackcount, maxnote = 2, 8
data = np.zeros((trackcount, maxnote, 4), dtype=np.uint32)
cont = np.full((128), -1, dtype=np.int32)

keysignature = ''
maxtempo = 4
tempo = np.zeros((4, 2), dtype=np.uint32)

mid = MidiFile('logic-tempo.mid')

time = 0
idx = 0

# meta messages
for msg in mid.tracks[0]:
    print(msg)
    time += msg.time

    if msg.type == 'key_signature':
        keysignature = msg.key

    elif msg.type == 'set_tempo':
        tempo[idx] = [msg.tempo,time]
        idx += 1

# track data
for trackidx, track in enumerate(mid.tracks[1:]):
    print('Track {}: {}'.format(trackidx, track.name))
    time = 0
    idx = 0
    
    # using note on note off for now — well logic pro exports like that
    for msg in track:
        print(msg)
        time += msg.time

        if msg.type == 'note_on':
            data[trackidx][idx] = [time, msg.note, msg.velocity, 0]
            cont[msg.note] = idx
            idx += 1

        elif msg.type == 'note_off':
            data[trackidx][cont[msg.note]][3] = time
            cont[msg.note] = -1

    print('')
print(data)
print(tempo)


# Image
'''
w, h = 1920, 1080
data = np.zeros((h, w, 3), dtype=np.uint8)
data[0:256, 0:256] = [255, 127, 0] # red patch in upper left
img = Image.fromarray(data, 'RGB')
img.save('my.png')
'''
