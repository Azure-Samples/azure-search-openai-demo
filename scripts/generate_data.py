from utils.whisper import transcribe
from utils.download_yt import download_video
from utils.convert_yt import mp4_to_mp3

if __name__ == '__main__':
    with open('data/links/huberman.txt', 'r') as f:
        for link in f.readlines():
            video_processed_path = download_video(link)
            # audio_processed_path = video_processed_path.replace('video', 'audio').replace('.mp4', '.mp3')
            # mp4_to_mp3(video_processed_path, audio_processed_path)
            transcribed = transcribe(video_processed_path)
            if transcribed:
                print(f"Successfully transcribed {video_processed_path}")
            else:
                print(f"Unable to transcribe {video_processed_path}")
        f.close()
