from moviepy.editor import AudioFileClip

def mp4_to_mp3(mp4, mp3):
    FILETOCONVERT = AudioFileClip(mp4)
    FILETOCONVERT.write_audiofile(mp3)
    FILETOCONVERT.close()

if __name__ == '__main__':
    VIDEO_FILE_PATH = "<>"
    AUDIO_FILE_PATH = "<>"

    mp4_to_mp3(VIDEO_FILE_PATH, AUDIO_FILE_PATH)
