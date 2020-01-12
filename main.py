from PIL import Image
import numpy as np
from mido import MidiFile, tempo2bpm
import argparse
from heapq import heappush, heappop
import os
from moviepy.editor import ImageClip, concatenate, AudioFileClip, concatenate_videoclips
import yaml
from progress.bar import IncrementalBar




# Arguments

parser = argparse.ArgumentParser(description='Turn midi into visual falling notes.',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('midifile', type=str, help='midi file to visualize')
parser.add_argument('audio', type=str, help='audio file to put on')
parser.add_argument('-W', '--width', type=int, default=1920, help='width of the video')
parser.add_argument('-H', '--height', type=int, default=1080, help='height of the video')
parser.add_argument('-s', '--start', type=int, default=21, help='start note')
parser.add_argument('-e', '--end', type=int, default=108, help='end note')
parser.add_argument('-K', '--keyboard-height', type=int, default=210, help='keyboard height')
parser.add_argument('-T', '--stretch', type=int, default=1, help='stretch constant')
parser.add_argument('-o', '--output', type=str, default='out.mp4', help='name of the output')
parser.add_argument('-S', '--speed', type=int, default=1, help='playback speed')
parser.add_argument('-t', '--track-count', type=int, default=16, help='max track count')
parser.add_argument('-m', '--max-note', type=int, default=1000, help='max note count, because i am lazy to measure')
parser.add_argument('-M', '--max-tempo', type=int, default=16, help='max tempo count, because i am lazy to measure')
parser.add_argument('-f', '--fps', type=int, default=24, help='frames per second')
parser.add_argument('-c', '--config', type=str, help='config file')
parser.add_argument('-F', '--save-frames', action="store_true", help='save frames as image file — not recommended, it takes whole lot of time to write')


args = parser.parse_args()

mid = MidiFile(args.midifile)
audioname = args.audio
width, height = args.width, args.height
start, end = args.start, args.end+1
keyboardheight = args.keyboard_height
stretch = args.stretch * 960000000
outputname = args.output
fps = args.fps
speed = args.speed * (480000000 / fps) #480000000/24 1 second constant / 24 frame per second
trackcount, maxnote = args.track_count, args.max_note
maxtempo = args.max_tempo
saveframes = args.save_frames

# Config

if args.config is not None:
    # Read YAML file
    with open("data.yaml", 'r') as stream:
        config = yaml.safe_load(stream)
        colors = config['colors']
else:
    colors = [
        [255,127,0],
        [0,127,255],
        [255,0,0],
        [0,0,255],
        [255,0,255],
        [127,0,255],
        [255,0,127],
        [255,255,255],
        [31,31,31]
    ]
# Midi

data = np.zeros((trackcount, maxnote, 4), dtype=np.uint64)
cont = np.full((128), -1, dtype=np.int32)

keysignature = ''
tempo = np.zeros((maxtempo, 2), dtype=np.uint64)


'''
time = 0
# meta messages
for msg in mid.tracks[0]:
    #print(msg)
    if metaidx == 0:
        time += msg.time
    else:
        time += msg.time * tempo[idx-1][0]

    if msg.type == 'key_signature':
        keysignature = msg.key

    elif msg.type == 'set_tempo':
        tempo[metaidx] = [msg.tempo,time]
        metaidx += 1
'''

maxtime = 0

# track data
for trackidx, track in enumerate(mid.tracks):
    metaidx = 0
    time = 0
    idx = 0
    tempoidx = 0

    # musescore?
    for msg in track:


        if len(tempo) > 0:
            time += msg.time * tempo[tempoidx][0]

        if len(tempo) > 1 and time >= tempo[tempoidx+1][1] and tempo[tempoidx+1][1] > 0:
            tempoidx += 1

        if msg.is_meta:
            if msg.type == 'key_signature':
                keysignature = msg.key

            elif msg.type == 'set_tempo':
                tempo[metaidx] = [msg.tempo,time]
                metaidx += 1
        elif msg.type == 'control_change':
            pass # I don't what in earth is this
        elif msg.type == 'program_change':
            pass # Same for this
        elif msg.type == 'note_on' and msg.velocity > 0:
            data[trackidx][idx] = [time, msg.note, msg.velocity, 0]
            cont[msg.note] = idx
            idx += 1

        elif msg.type == 'note_off' or msg.velocity == 0:
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


def noteheight(s, e, curr):
    return (
        int(windowheight-max((s-curr)/speed, 0) * (windowheight * speed / stretch)),
        int(windowheight-min((e-curr)/speed, stretch/speed) * (windowheight * speed / stretch))
    )





# Notes

maxcont = 200
idx = np.zeros((trackcount, 2), dtype=np.uint32)
cont = np.full((maxcont,2), -1, dtype=np.int8)
windowheight = height-keyboardheight-2

curr = 0
seen = []

bar = IncrementalBar('Frames: ', max=int(maxtime/speed)+2, suffix='%(index)d / %(max)d', width=os.get_terminal_size()[0]-30)

pressed = np.full((128), -1, dtype=np.int8)

pressed = [[] for _ in range(128)]

clips = []

for curr in range(0, int(maxtime) + 2 * int(speed), int(speed)):
    # add incoming notes
    for trackidx, track in enumerate(data):
        while idx[trackidx][0] < maxnote and track[idx[trackidx][0]][0] < stretch + curr :
            if track[idx[trackidx][0]][3] != 0:
                heappush(seen, (track[idx[trackidx][0]][3], track[idx[trackidx][0]][0], track[idx[trackidx][0]][1], trackidx))
            idx[trackidx][0]+=1

        while idx[trackidx][1] < maxnote and track[idx[trackidx][1]][0] < curr :
            if track[idx[trackidx][1]][3] != 0:
                pressed[track[idx[trackidx][1]][1]].append(trackidx)
            idx[trackidx][1]+=1
    # remove past notes

    while len(seen) > 0 and seen[0][0] < curr:
        pressed[seen[0][2]].pop()
        heappop(seen)

    # test draw
    frameimage = np.zeros((height, width, 3), dtype=np.uint8)
    for note in notes[notes[:,2].argsort()][::-1]:
        if note[2] == 1:
            frameimage[-keyboardheight:-1, note[0]+2:note[1]-2
            ] = colors[pressed[note[3]][0]] if len(pressed[note[3]]) > 0 else colors[-2]
        if note[2] == 0:
            frameimage[-keyboardheight:-round((3*keyboardheight)/7), note[0]+1:note[1]-1
            ] = colors[pressed[note[3]][0]] if len(pressed[note[3]]) > 0 else colors[-1]


    for s in seen:
        h = (
            int(windowheight-max((s[1]-curr)/speed, 0) * (windowheight * speed / stretch)),
            int(windowheight-min((s[0]-curr)/speed, stretch/speed) * (windowheight * speed / stretch))
        )
        w = notes[int(s[2]-start)][0:2]
        frameimage[h[1]+1:h[0]-1, w[0]+1:w[1]-1] = colors[s[3]]


    if saveframes:
        img = Image.fromarray(frameimage, 'RGB')
        img.save('out/%06d.png' % (int(curr/speed)))

    clips.append(ImageClip(frameimage).set_duration(1/fps))

    bar.next()
bar.finish()


# Writing the video

video = concatenate(clips, method="compose")
audio = AudioFileClip(audioname)
video = concatenate_videoclips([video, ImageClip(frameimage).set_duration(audio.duration - video.duration)])
video = video.set_audio(audio)
video.write_videofile(outputname, fps=fps)
