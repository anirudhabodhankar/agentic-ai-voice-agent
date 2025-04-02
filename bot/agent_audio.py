# python -m bot.agent_audio

from pynput import keyboard
import time
import threading
import pyaudio
import wave
from playsound import playsound
from bot import agent_proxy

import asyncio

playsound("audio\\model_loaded.wav")

file_ready_counter=0
stop_recording=False
is_recording=False
stop_playback = False
pykeyboard= keyboard.Controller()
temp_prefix = "temp\\test"

def get_server_response():
    global file_ready_counter
    global stop_playback
    i=1
    print("ready - start recording with F2 ...\n")
    while True:
        while file_ready_counter<i:
            if stop_playback:
                return False
            time.sleep(0.01)

        audio_file = (temp_prefix + str(i) + ".wav")

        proxy = agent_proxy.AgentProxy()
        asyncio.run(proxy.generate_audio_response(device_id = "864068071000005", user_input = None, user_audio_file= audio_file))

        i=i+1

#keyboard events
pressed = set()

COMBINATIONS = [
    {
        "keys": [
            {keyboard.Key.f2},
        ],
        "command": "start record",
    },
]

#record audio
def record_speech():
    global file_ready_counter
    global stop_recording
    global is_recording

    is_recording=True
    chunk = 1024  # Record in chunks of 1024 samples
    sample_format = pyaudio.paInt16  # 16 bits per sample
    channels = 1
    fs = 24000  # Record at 44100 samples per second
    p = pyaudio.PyAudio()  # Create an interface to PortAudio
    stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True)

    frames = []  # Initialize array to store frames

    print("Start recording...\n")
    playsound("audio\\on.wav")

    while stop_recording==False:
        data = stream.read(chunk)
        frames.append(data)

    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    # Terminate the PortAudio interface
    p.terminate()
    playsound("audio\\off.wav")
    print('Finish recording')

    # Save the recorded data as a WAV file
    wf = wave.open(temp_prefix + str(file_ready_counter+1) + ".wav", 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(sample_format))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()

    stop_recording=False
    is_recording=False
    file_ready_counter=file_ready_counter+1

#transcribe speech in infinte loop
t2 = threading.Thread(target=get_server_response)
t2.start()

#hot key events
def on_press(key):
    global stop_playback
    print("key pressed: {0}".format(key))
    pressed.add(key)
    if key == keyboard.Key.esc or key == keyboard.KeyCode.from_char('q'):          
        # Stop the listener
        stop_playback = True
        return False
        

def on_release(key):
    if key == keyboard.Key.esc or key == keyboard.KeyCode.from_char('q'):        
        # Stop the listener
        return False

    global pressed
    global stop_recording
    global is_recording
    for c in COMBINATIONS:
        for keys in c["keys"]:
            if keys.issubset(pressed):
                if c["command"]=="start record" and stop_recording==False and is_recording==False:
                    t1 = threading.Thread(target=record_speech)
                    t1.start()
                else:
                    if c["command"]=="start record" and is_recording==True:
                        stop_recording=True
                pressed = set()

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()