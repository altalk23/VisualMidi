from PIL import Image
import numpy as np
from mido import MidiFile, tempo2bpm
import argparse

# Arguments

parser = argparse.ArgumentParser(description='Turn midi into visual falling notes.')
parser.add_argument('midifile', type=str, help='midi file to visualize')
parser.add_argument('-wi', '--width', type=int, default=1920, help='width of the video')
parser.add_argument('-hi', '--height', type=int, default=1080, help='height of the video')
parser.add_argument('-s', '--start', type=int, default=21, help='start note')
parser.add_argument('-e', '--end', type=int, default=108, help='end note')
parser.add_argument('-st', '--stretch', type=int, default=960000000, help='stretch constant')


args = parser.parse_args()

mid = MidiFile(args.midifile)
width, height = args.width, args.height
start, end = args.start, args.end+1
stretch = args.stretch

# Midi

trackcount, maxnote = 2, 8
data = np.zeros((trackcount, maxnote, 4), dtype=np.uint64)
cont = np.full((128), -1, dtype=np.int32)

keysignature = ''
maxtempo = 4
tempo = np.zeros((4, 2), dtype=np.uint64)



time = 0
idx = 0

# meta messages
for msg in mid.tracks[0]:
    print(msg)
    if idx == 0:
        time += msg.time
    else:
        time += msg.time * tempo[idx-1][0]

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
    tempoidx = 0

    # using note on note off for now — well logic pro exports like that
    for msg in track:
        print(msg)
        time += msg.time * tempo[tempoidx][0]
        if time >= tempo[tempoidx+1][1] and tempo[tempoidx+1][1] > 0:
            tempoidx += 1

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





# Keyboard visual
octave = np.array([1,0,1,0,1,1,0,1,0,1,0,1])
full = np.tile(octave, 11)[:128]
keyboard = full[start:end]
whitecount = np.count_nonzero(keyboard == 1)
notes = np.zeros((end-start,2), dtype=np.uint16)
idx = 0
for note in range(end-start):
    if keyboard[note] == 1: idx += 1
    whitewidth = round((width * idx) / whitecount)
    blackwidth = whitewidth / 1.5
    if keyboard[note] == 1:
        if (keyboard[note-1]) == 1:
            notes[note] = [notes[note-1][1], whitewidth]
        else:
            notes[note] = [notes[note-2][1], whitewidth]
    else:
        if (start+note)%12 == 1:
            notes[note] = [round(notes[note-1][1]-blackwidth/1.5), round(notes[note-1][1]+blackwidth/3)]
            pass
        elif (start+note)%12 == 3:
            notes[note] = [round(notes[note-1][1]-blackwidth/3), round(notes[note-1][1]+blackwidth/1.5)]
            pass
        elif (start+note)%12 == 6:
            notes[note] = [round(notes[note-1][1]-blackwidth*0.75), round(notes[note-1][1]+blackwidth*0.25)]
            pass
        elif (start+note)%12 == 8:
            notes[note] = [round(notes[note-1][1]-blackwidth*0.5), round(notes[note-1][1]+blackwidth*0.5)]
            pass
        elif (start+note)%12 == 10:
            notes[note] = [round(notes[note-1][1]-blackwidth*0.25), round(notes[note-1][1]+blackwidth*0.75)]
            pass
print(notes)


# Image
'''
data = np.zeros((height, width, 3), dtype=np.uint8)
data[0:256, 0:256] = [255, 127, 0] # red patch in upper left
img = Image.fromarray(data, 'RGB')
img.save('my.png')
'''
