import pyaudio
import threading  # For handling threads
import queue  # For creating and managing queues
from opentelemetry import context as context_api
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()

class AudioPlayer:
    """
    A class to handle audio playback using PyAudio.
    """
    def __init__(self, parent_context=None):
        self.audio_queue = queue.Queue()  # Queue to store audio chunks
        self.playback_complete = threading.Event()  # Event to signal playback completion
        self.audio_added = threading.Event()  # Event to signal that audio has been added to the queue
        self.audio_size_in_bytes = 0
        self.parent_context = parent_context  # Store the parent context

        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=8000,
            output=True
        )

        # Start audio playback thread
        self.audio_thread = threading.Thread(target=self.play_audio)
        self.audio_thread.start()

    def play_audio(self):
        is_first_chunk = True
        """
        Method to play audio chunks from the queue.
        """
        # Activate the parent context in this thread
        token = context_api.attach(self.parent_context) if self.parent_context else None

        while not self.playback_complete.is_set(): #this is like While True
            try:
                audio_chunk = self.audio_queue.get(timeout=0.1)
                self.audio_size_in_bytes += len(audio_chunk)
                if is_first_chunk:
                    console_logger.info("Audio playback started.")
                    is_first_chunk = False
                self.stream.write(audio_chunk)
            except queue.Empty:
                if self.audio_added.is_set() and self.audio_queue.empty():
                    # If all audio has been added and queue is empty, we're done
                    break
                continue

        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        console_logger.info("Audio playback completed.")

        # Detach the context when done
        if token:
            context_api.detach(token)

    def add_audio(self, audio_data):
        """
        Method to add audio data to the queue.
        """
        for chunk in audio_data:
            self.audio_queue.put(chunk)
        

    def wait_for_completion(self):
        """
        Method to wait for the audio playback thread to complete.
        """
        self.audio_thread.join()
        #print(f'total audio size: {self.audio_size_in_bytes} bytes')

    def add_audio_complete(self):
        """
        Method to signal that audio has been added
        """
        self.audio_added.set()  # Signal that all audio has been added