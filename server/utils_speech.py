import azure.cognitiveservices.speech as speechsdk  
import base64  
import tempfile  
import gc
import os
import threading  # For handling threads
import queue  # For creating and managing queues
from opentelemetry import context as context_api
from server import utils_logger
console_logger, console_tracer = utils_logger.get_logger_tracer()

# Initialize Speech SDK configuration  
speech_config = speechsdk.SpeechConfig(  
    subscription=os.getenv("AZURE_TTS_API_KEY", ""),  
    region=os.getenv("AZURE_TTS_REGION", "")
) 

language_config_list = region=os.getenv("AUTO_DETECT_SOURCE_LANGUAGE_CONFIG", "en-IN").split(",")
console_logger.info(f"Language config list: {language_config_list}")
auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=language_config_list)

def base64_to_audio_file(base64_string: str, file_extension: str = ".wav") -> str:  
    """  
    Decode a Base64-encoded string and save it as a temporary audio file.  
  
    Args:  
        base64_string (str): The Base64-encoded audio data.  
        file_extension (str, optional): The file extension for the temporary audio file.  
                                        Defaults to ".wav".  
  
    Returns:  
        str: The file path to the temporary audio file.  
    """  
    audio_bytes = base64.b64decode(base64_string)  
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:  
        tmp_file.write(audio_bytes)  
        temp_file_path = tmp_file.name  
    return temp_file_path  

@console_tracer.start_as_current_span("speech_to_text_from_base64")
def speech_to_text_from_base64(base64_audio: str) -> str:  
    """  
    Convert a Base64-encoded audio string to text using Azure Speech-to-Text services.  
  
    This function performs the following steps:  
    1. Decodes the Base64 string to an audio file.  
    2. Configures Azure Speech SDK with the necessary credentials.  
    3. Recognizes speech from the audio file.  
    4. Cleans up temporary resources.  
  
    Args:  
        base64_audio (str): The Base64-encoded audio data.  
  
    Returns:  
        str: The recognized text from the audio. Returns an empty string if recognition fails.  
    """  
      
    # Convert Base64 string to a temporary audio file  
    audio_file_path = base64_to_audio_file(base64_audio)  
      
    try:  
        # Set up the audio configuration  
        audio_config = speechsdk.AudioConfig(filename=audio_file_path)  
          
        # Initialize the speech recognizer  
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, 
                                                       audio_config=audio_config,
                                                       auto_detect_source_language_config=auto_detect_source_language_config)  
          
        console_logger.info("Recognizing speech...")  
        result = speech_recognizer.recognize_once()  
          
        # Check the result  
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:  
            console_logger.info(f"Recognized Text: {result.text}")  
            return result.text  
          
        elif result.reason == speechsdk.ResultReason.NoMatch:  
            console_logger.warning("No speech could be recognized.")  
          
        elif result.reason == speechsdk.ResultReason.Canceled:  
            cancellation = result.cancellation_details  
            console_logger.error(f"Speech Recognition canceled: {cancellation.reason}")  
            if cancellation.reason == speechsdk.CancellationReason.Error:  
                console_logger.error(f"Error details: {cancellation.error_details}")  
              
    except Exception as e:  
        console_logger.exception("An error occurred during speech recognition.")  
      
    finally:  
        # Clean up resources  
        del speech_recognizer  
        gc.collect()  
        if os.path.exists(audio_file_path):  
            os.remove(audio_file_path)  
      
    return ""  

class StreamingSTT:
    """
    A class to convert streamin audio to text using Azure Speech-to-Text services.
    """
    def __init__(self, parent_context=None):
        self.parent_context = parent_context  # Store the parent context
        self.audio_queue = queue.Queue()  # Queue to store audio chunks
        self.stt_complete = threading.Event()  # Event to signal transcription is complete
        self.audio_added = threading.Event()  # Event to signal that all the audio chunks are added to the queue
        self.recognition_done = threading.Event()  # Event to signal that speech recognition is done
        self.audio_size_in_bytes = 0
        self.tts_recognition= None
        
        # setup the audio stream
        self.stream = speechsdk.audio.PushAudioInputStream()
        self.text = ""  # Initialize text to empty string

        audio_config = speechsdk.audio.AudioConfig(stream=self.stream)

        # instantiate the speech recognizer with push stream input
        self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, 
                                                            audio_config=audio_config,
                                                             auto_detect_source_language_config=speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=language_config_list))  

         # start push stream writer thread
        self.push_stream_writer_thread = threading.Thread(target=self.push_stream_writer)
        self.push_stream_writer_thread.start()
        console_logger.info("StreamingSTT.__init__ complete")
        
    def create_stream(self):
         # Connect callbacks to the events fired by the speech recognizer
        def session_stopped_cb(evt):
            """callback that signals to stop continuous recognition upon receiving an event `evt`"""
            console_logger.info('StreamingSTT - SESSION STOPPED: {}'.format(evt))
            self.recognition_done.set()
        
        def text_recognized_cb(evt):
            """callback that signals to stop continuous recognition upon receiving an event `evt`"""
            console_logger.info('StreamingSTT - TEXT RECOGNIZED: {}'.format(evt))
            self.tts_recognition.end()
            self.text += evt.result.text

        def text_recognition_started_cb(evt):
            """callback that signals to stop continuous recognition upon receiving an event `evt`"""
            console_logger.info('StreamingSTT - TEXT RECOGNITION STARTED: {}'.format(evt))
            self.tts_recognition = console_tracer.start_span("tts_recognition")


        self.speech_recognizer.recognizing.connect(lambda evt: console_logger.info('StreamingSTT - recognizing: {}'.format(evt)))
        self.speech_recognizer.recognized.connect(text_recognized_cb)
        self.speech_recognizer.session_started.connect(text_recognition_started_cb)
        self.speech_recognizer.session_stopped.connect(session_stopped_cb)
        # self.speech_recognizer.canceled.connect(lambda evt: console_logger.info('StreamingSTT - CANCELED {}'.format(evt)))

        # start continuous speech recognition
        self.speech_recognizer.start_continuous_recognition()
        console_logger.info("StreamingSTT - create_stream complete")
    
    def push_stream_writer(self):
        """
        Method to play audio chunks from the queue.
        """
        # Activate the parent context in this thread
        token = context_api.attach(self.parent_context) if self.parent_context else None

        with console_tracer.start_as_current_span("push_stream_writer") as span:
            while not self.stt_complete.is_set(): #this is like While True
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    #console_logger.info(f"StreamingSTT - Writing to stream Audio chunk size: {len(audio_chunk)} bytes")
                    self.audio_size_in_bytes += len(audio_chunk)
                    self.stream.write(audio_chunk)
                except queue.Empty:
                    if self.audio_added.is_set() and self.audio_queue.empty():
                        # If all audio has been added and queue is empty, we're done
                        break
                    continue

            self.stream.close()
            console_logger.info("StreamingSTT push_stream_writer completed.")

            # Detach the context when done
            if token:
                context_api.detach(token)

    def add_audio(self, audio_data):
        """
        Method to add audio data to the queue.
        """
        for chunk in audio_data:
            #console_logger.info(f"StreamingSTT - Adding Audio chunk size: {len(chunk)} bytes to queue")
            self.audio_queue.put(chunk)
        
    def add_audio_complete(self):
        """
        Method to signal that audio has been added
        """
        self.audio_added.set()  # Signal that all audio has been added

    def wait_for_completion(self):
        """
        Method to wait for the audio playback thread to complete.
        """
         # wait until all input processed
        self.recognition_done.wait()

        # stop recognition and clean up
        self.speech_recognizer.stop_continuous_recognition()
        self.push_stream_writer_thread.join()
        console_logger.info(f"StreamingSTT - wait_for_completion completed.")

    def get_text(self):
        return self.text  # Return the recognized text

