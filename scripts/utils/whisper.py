import whisper
from whisper.utils import get_writer

model = whisper.load_model('tiny')
output_dir = 'data/transcript'

def transcribe(input_path):
    file_name = input_path.split('/')[-1].split('.')[0]
    print(f"Transcribing file name: {file_name}")
    try:
        result = model.transcribe(audio=input_path)
        txt_writer = get_writer('txt', output_dir)
        txt_writer(result, input_path)
    except Exception as exception:
        print(exception)
        return False
    
    return True