from utils.whisper import transcribe
from utils.download_yt import download_video

if __name__ == '__main__':
    with open('scripts/utils/links_videos_huberman.txt', 'r') as f:
        for link in f.readlines():
            file_processed_path = download_video(link)
            transcribed = transcribe(file_processed_path)
            if transcribed:
                print(f"Successfully transcribed {file_processed_path}")
            else:
                print(f"Unable to transcribe {file_processed_path}")
        f.close()