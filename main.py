from PIL import Image
import numpy as np
from mido import MidiFile, tempo2bpm
import argparse
from heapq import heappush, heappop
import os
from cv2 import imread, VideoWriter, destroyAllWindows, VideoWriter_fourcc


# Arguments

parser = argparse.ArgumentParser(description='Turn midi into visual falling notes.')
parser.add_argument('midifile', type=str, help='midi file to visualize')
parser.add_argument('-W', '--width', type=int, default=1920, help='width of the video')
parser.add_argument('-H', '--height', type=int, default=1080, help='height of the video')
parser.add_argument('-s', '--start', type=int, default=21, help='start note')
parser.add_argument('-e', '--end', type=int, default=108, help='end note')
parser.add_argument('-K', '--keyboard-height', type=int, default=210, help='keyboard height')
parser.add_argument('-T', '--stretch', type=int, default=1, help='stretch constant')
parser.add_argument('-o', '--output', type=str, default='out.mp4', help='name of the output')
parser.add_argument('-S', '--speed', type=int, default=1, help='playback speed')


args = parser.parse_args()

mid = MidiFile(args.midifile)
width, height = args.width, args.height
start, end = args.start, args.end+1
keyboardheight = args.keyboard_height
stretch = args.stretch * 960000000
outputname = args.output
speed = args.speed * 20000000 #480000000/24 1 second constant / 24 frame per second

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
    #print(msg)
    if idx == 0:
        time += msg.time
    else:
        time += msg.time * tempo[idx-1][0]

    if msg.type == 'key_signature':
        keysignature = msg.key

    elif msg.type == 'set_tempo':
        tempo[idx] = [msg.tempo,time]
        idx += 1


maxtime = 0

# track data
for trackidx, track in enumerate(mid.tracks[1:]):
    #print('Track {}: {}'.format(trackidx, track.name))
    time = 0
    idx = 0
    tempoidx = 0

    # using note on note off for now — well logic pro exports like that
    for msg in track:
        #print(msg)
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
        maxtime = max(maxtime, time)

    #print('')
#print(data)
#print(tempo)





# Visual
octave = np.array([1,0,1,0,1,1,0,1,0,1,0,1])
keyboard = np.tile(octave, 11)[start:end]
whitecount = np.count_nonzero(keyboard == 1)
notes = np.zeros((end-start,4), dtype=np.int16)
idx = 0
blackwidth = round(width / whitecount) / 1.5
blackconstant = {
    1:(0.666666,0.333333),
    3:(0.333333,0.666666),
    6:(0.75,0.25),
    8:(0.5,0.5),
    10:(0.25,0.75)
}
for note in range(end-start):
    prevnote = notes[note-1][1]
    if keyboard[note] == 1: idx += 1
    whitewidth = round((width * idx) / whitecount)
    if keyboard[note] == 1:
        if (keyboard[note-1]) == 1:
            notes[note] = [notes[note-1][1], whitewidth, 1, note+start]
        else:
            notes[note] = [notes[note-2][1], whitewidth, 1, note+start]
    else:
        notes[note] = [
            max(round(prevnote-blackwidth*blackconstant[(start+note)%12][0]), 0),
            round(notes[note-1][1]+blackwidth*blackconstant[(start+note)%12][1]), 0, note+start
        ]
#print(notes)

def notewidth(n):
    return notes[int(n-start)][0:2]

windowheight = height-keyboardheight-2
def noteheight(s, e, curr):
    return (
        int(windowheight-max((s-curr)/speed, 0) * (windowheight * speed / stretch)),
        int(windowheight-min((e-curr)/speed, stretch/speed) * (windowheight * speed / stretch))
    )

def color(n):
    return [
        [255,127,0],
        [0,127,255],
        [255,255,255],
        [31,31,31]
    ][n]

pressed = np.full((128), -1, dtype=np.int8)

def drawkeyboard(frameimage):
    for note in notes[notes[:,2].argsort()][::-1]:
        if note[2] == 1:
            frameimage[-keyboardheight:-1, note[0]+2:note[1]-2
            ] = color(pressed[note[3]]) if pressed[note[3]] != -1 else color(-2)
        if note[2] == 0:
            frameimage[-keyboardheight:-round((3*keyboardheight)/7), note[0]+1:note[1]-1
            ] = color(pressed[note[3]]) if pressed[note[3]] != -1 else color(-1)


'''
copyimg = np.copy(keyboardimage)
img = Image.fromarray(copyimg, 'RGB')
img.save(outputname)
'''
# Notes

maxcont = 200
idx = np.zeros((trackcount, 2), dtype=np.uint32)
cont = np.full((maxcont,2), -1, dtype=np.int8)

finished = True
curr = 0
seen = []
os.system('rm -rf out ; mkdir out')

while finished:
    # add incoming notes
    for trackidx, track in enumerate(data):
        while idx[trackidx][0] < maxnote and track[idx[trackidx][0]][0] < stretch + curr :
            if track[idx[trackidx][0]][3] != 0:
                heappush(seen, (track[idx[trackidx][0]][3], track[idx[trackidx][0]][0], track[idx[trackidx][0]][1], trackidx))
            idx[trackidx][0]+=1

        while idx[trackidx][1] < maxnote and track[idx[trackidx][1]][0] < curr :
            if track[idx[trackidx][1]][3] != 0:
                pressed[track[idx[trackidx][1]][1]] = trackidx
            idx[trackidx][1]+=1
    # remove past notes
    while len(seen) > 0 and seen[0][0] < curr:
        pressed[seen[0][2]] = -1
        heappop(seen)

    # test draw
    frameimage = np.zeros((height, width, 3), dtype=np.uint8)
    drawkeyboard(frameimage)

    for s in seen:
        h = noteheight(s[1], s[0], curr)
        w = notewidth(s[2])
        frameimage[h[1]:h[0], w[0]:w[1]] = color(s[3])



    # end
    if curr > maxtime: break

    img = Image.fromarray(frameimage, 'RGB')
    img.save('out/%04d.png' % (int(curr/speed)))

    #next
    curr += speed
    print(int(curr/speed))

images = [img for img in os.listdir('out') if img.endswith(".png")]
images.sort()
video = VideoWriter(outputname, 0x7634706d, 24, (width,height))
for image in images:
    video.write(imread(os.path.join('out', image)))
destroyAllWindows()
video.release()
