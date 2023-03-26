from pytube import YouTube
import os

def download_video(link):
    yt = YouTube(link)
    print(f"Downloading: {link}")
    filepath_initial = (yt
                        .streams
                        .filter(progressive=True, file_extension='mp4')
                        .order_by('resolution')
                        .asc()
                        .first()
                        .download('data/video/'))
    filename_initial = filepath_initial.split('/')[-1]
    filename_processed = (filename_initial.replace(' ', '_')).lower()
    filepath_processed = '/'.join(filepath_initial.split('/')[:-1]) + f"/{filename_processed}"
    print(f"Renaming, from {filepath_initial} to {filepath_processed}")
    os.rename(filepath_initial, filepath_processed)
    return filepath_processed
