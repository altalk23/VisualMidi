from PIL import Image, ImageFont, ImageDraw
import numpy as np
from mido import MidiFile, tempo2bpm
import argparse
from heapq import heappush, heappop
import os
from moviepy.editor import ImageClip, concatenate, AudioFileClip, concatenate_videoclips, VideoFileClip
import yaml
from progress.bar import IncrementalBar
from datetime import timedelta
from sys import getsizeof
from collections import Mapping, Container
from queue import Queue
from bisect import insort_left


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
parser.add_argument('-fn', '--font-name', type=str, default="Courier Prime Code.ttf", help='font file to use')
parser.add_argument('-r', '--recycle-rate', type=int, default=96, help='frame count to write')


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
fontname = args.font_name
recyclerate = args.recycle_rate

# Config

if args.config is not None:
    # Read YAML file
    with open(args.config, 'r') as stream:
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
cont = [Queue(maxsize=20) for _ in range(128)]

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
        #print(msg)
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
        elif msg.type == 'pitchwheel':
            pass # Same for this
        elif msg.type == 'note_on' and msg.velocity > 0:
            data[trackidx][idx] = [time, msg.note, msg.velocity, 0]
            cont[msg.note].put(idx)
            idx += 1

        elif msg.type == 'note_off' or msg.velocity == 0:

            data[trackidx][cont[msg.note].get()][3] = time



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



# Notes

maxcont = 200
idx = np.zeros((trackcount, 2), dtype=np.uint32)
cont = np.full((maxcont,2), -1, dtype=np.int8)
windowheight = height-keyboardheight-2

curr = 0
seen = []

bar = IncrementalBar('Frames: ', max=int(maxtime/speed)+2, suffix='%(index)d / %(max)d', width=os.get_terminal_size()[0]-30)
frameidx = 0

pressed = np.full((128), -1, dtype=np.int8)

pressed = [[] for _ in range(128)]

clips = []

if saveframes: os.system('rm -rf out > /dev/null ; mkdir out')
os.system('rm -rf mem > /dev/null ; mkdir mem')


tempoidx = 0
for curr in range(0, int(maxtime + 3 * speed), int(speed)):
    #print(pressed)
    #print('')
    frameimage = np.zeros((height, width, 3), dtype=np.uint8)
    if curr > tempo[tempoidx+1][1] and tempo[tempoidx+1][1] > 0: tempoidx += 1
    # add incoming notes
    print(seen)
    print(pressed)
    for trackidx, track in enumerate(data):
        while idx[trackidx][0] < maxnote and track[idx[trackidx][0]][0] < stretch + curr :
            if track[idx[trackidx][0]][3] != 0:
                #print("pushing {0}".format((track[idx[trackidx][0]][3], track[idx[trackidx][0]][0], track[idx[trackidx][0]][1], trackidx)))
                insort_left(seen, (track[idx[trackidx][0]][0], track[idx[trackidx][0]][3], track[idx[trackidx][0]][1], trackidx))
                #heappush(seen, (track[idx[trackidx][0]][3], track[idx[trackidx][0]][0], track[idx[trackidx][0]][1], trackidx))
            idx[trackidx][0]+=1

    pressed = [[] for _ in range(128)]
    pressedidx = 0
    for s in seen:
        if s[0] <= curr:
            pressed[s[2]].append(s[3])
        else: break
        pressedidx+=1

    # remove past notes
    for i, s in enumerate(seen):
        if s[1] <= curr:
            pressed[s[2]].pop()
    seen = [s for s in seen if s[1] > curr ]
        #seen = seen[:i] + seen[i+1:]


    # test draw
    frameimage = np.zeros((height, width, 3), dtype=np.uint8)
    for note in notes[notes[:,2].argsort()][::-1]:
        if note[2] == 1:
            frameimage[-keyboardheight:-1, note[0]+2:note[1]-2
            ] = colors[pressed[note[3]][-1]] if len(pressed[note[3]]) > 0 else colors[-2]
        if note[2] == 0:
            frameimage[-keyboardheight:-round((3*keyboardheight)/7), note[0]+1:note[1]-1
            ] = colors[pressed[note[3]][-1]] if len(pressed[note[3]]) > 0 else colors[-1]

    #print(seen)
    for s in seen:
        print(s)
        h = (
            int(windowheight-max((s[0]-curr)/speed, 0) * (windowheight * speed / stretch)),
            int(windowheight-min((s[1]-curr)/speed, stretch/speed) * (windowheight * speed / stretch))
        )
        w = notes[int(s[2]-start)][0:2]
        frameimage[h[1]+1:max(h[0]-1, 0), w[0]+1:w[1]-1] = colors[s[3]]

    img = Image.fromarray(frameimage, 'RGB')
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(fontname, 32)
    draw.text((20, windowheight - 54), "Key Signature: {0}, Tempo: {1}".format(keysignature, tempo2bpm(tempo[tempoidx][0])),(255,255,255),font=font)
    elapsed = timedelta(seconds=min(curr/speed/fps, maxtime/speed/fps))
    endtime = timedelta(seconds=maxtime/speed/fps)
    draw.text((20, 22), "{0} / {1}".format(
        '%02d:%02d:%02d.%06d' % (elapsed.seconds // 3600, (elapsed.seconds // 60) % 60, elapsed.seconds, elapsed.microseconds),
        '%02d:%02d:%02d.%06d' % (endtime.seconds // 3600, (endtime.seconds // 60) % 60, endtime.seconds, endtime.microseconds)
    ),(255,255,255),font=font)
    frameimage = np.array(img)

    if saveframes: img.save('out/%06d.png' % (int(curr/speed)))

    clips.append(ImageClip(frameimage).set_duration(1/fps))
    if frameidx % recyclerate == recyclerate - 1: #write
        video = concatenate(clips, method="compose")
        video.write_videofile('mem/%06d.mp4' % (frameidx), fps=fps, verbose=False, logger=None)
        clips = None
        del clips
        clips = []
        video = None
        del video


    if frameidx <= int(maxtime/speed):
        frameimage = None
        del frameimage

    bar.next()
    frameidx += 1


bar.finish()


# Writing the video
if (frameidx % recyclerate != 0):
    video = concatenate(clips, method="compose")
audio = AudioFileClip(audioname)
if frameidx > recyclerate:
    subvideos = [sub for sub in os.listdir('mem') if sub.endswith(".mp4")]
    subvideos.sort()
    clips = [VideoFileClip('mem/'+sub) for sub in subvideos]
    if (frameidx % recyclerate != 0):
        video = concatenate_videoclips(clips + [video])
    else:
        video = concatenate_videoclips(clips)
video = concatenate_videoclips([video, ImageClip(frameimage).set_duration(audio.duration - video.duration)])
video = video.set_audio(audio)
video.write_videofile(outputname, fps=fps)
