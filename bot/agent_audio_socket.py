# python -m bot.agent_audio_socket

from pynput import keyboard
import threading
import pyaudio
from playsound import playsound
from bot import agent_proxy

import asyncio

playsound("audio\\model_loaded.wav")

stop_recording=False
is_recording=False
stop_playback = False
pykeyboard= keyboard.Controller()

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
    global stop_recording
    global is_recording

     # Set up an event loop for the async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    proxy = agent_proxy.get_agent_sroxy_sockets(device_id = "864068071000005")

    is_recording=True
    chunk = 1024  # Record in chunks of 5000 samples = 2Kb
    sample_format = pyaudio.paInt16  # 16 bits per sample
    channels = 1
    fs = 16000  # Record at 44100 samples per second
    p = pyaudio.PyAudio()  # Create an interface to PortAudio
    stream = p.open(format=sample_format,
                channels=channels,
                rate=fs,
                frames_per_buffer=chunk,
                input=True)

    frames = []  # Initialize array to store frames

    playsound("audio\\on.wav")
    print("Start recording...\n")

    while stop_recording==False:
        data = stream.read(chunk)
        loop.run_until_complete(proxy.add_audio([data]))
        frames.append(data)

    loop.run_until_complete(proxy.add_audio_complete())
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    # Terminate the PortAudio interface
    p.terminate()
    playsound("audio\\off.wav")
    print('Finished recording')

    stop_recording=False
    is_recording=False

    # Generate the audio response
    loop.run_until_complete(proxy.generate_audio_response())
    loop.close()
    print("---------------------------------------------------------------------------------------------------------------------")
    print("ready - start recording with F2 ...\n")

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
print("---------------------------------------------------------------------------------------------------------------------")
print("ready - start recording with F2 ...\n")
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()