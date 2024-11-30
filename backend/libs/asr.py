import os
import time
import torch
import whisper
import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks


if __name__ == "__main__":
    asr_model = whisper.load_model("turbo")
    chunk_length_ms  = 120 * 1000 # pydub calculates in millisec
    
    # split audio into chunks
    audio_path = r"C:\Users\mtseng\Desktop\TAMU\CSCE-689-PROGRAMMING-LLMs\project\YouClipAI\backend\downloads\audio\Austin Reaves Playing Streetball in the NBA.wav"
    audio = AudioSegment.from_file(audio_path)

    chunks = make_chunks(audio, chunk_length_ms)
    out_dir = "./tmps/tmp{}".format(int(time.time()))
    os.makedirs(out_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    progress_step = int(100 / len(chunks))
    current_progress = 0
    for i, chunk in enumerate(chunks):
        # Save the chunk to disk
        chunk_name = os.path.join(out_dir, f"chunk{i}.wav")
        chunk.export(chunk_name, format="wav")
        
        # Transcribe with Whisper
        start_time = time.time()
        result = asr_model.transcribe(chunk_name)
        print(f"Transcription for chunk {i}:\n{result['text']}\n, time-elapsed: {time.time() - start_time:.2f}s")   
        current_progress += progress_step
        print(f"Progress: {current_progress}%")
