from pytube import YouTube
import os

def download_video(link):
    yt = YouTube(link)
    print(f"Downloading: {link}")
    filename_initial = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download('data/video/')
    filename_processed = filename_initial.replace(' ', '_')
    filename_processed = filename_processed.lower()
    print(f"Renaming, from {filename_initial} to {filename_processed}")
    os.rename(filename_initial, filename_processed)
    return filename_processed