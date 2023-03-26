from moviepy.editor import AudioFileClip

def mp4_to_mp3(mp4, mp3):
    try:
        file_to_convert = AudioFileClip(mp4)
        file_to_convert.write_audiofile(mp3)
        file_to_convert.close()
    except Exception as exception:
        print(f"Error when converting {mp4} to {mp3}: \n{exception}")
        return False
    
    return True
