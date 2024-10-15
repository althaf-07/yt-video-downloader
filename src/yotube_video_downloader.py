import os
from pytubefix import YouTube, Playlist

# How to get name of the playlist using pytube?
# Make a folder and save the the below videos to that folder with the playlist name
# Add functionality of calculating the size of the playlist before downloading.
# Also show the size downloaded and the remaining size
# Implement a way to select a download_path
# Flash youtube video downloader
# resolutions = ['144p', '240p', '360p', '480p', '720p', '1080p', 'Auto'] # Categorical select box 
# stream = video.streams_get_highest_resolution()
# stream.download()

def main(url: str, resolution: str, download_path):
     if url.split('/')[3].split('?')[0] == 'playlist':
          playlist_downloader(url, resolution, download_path)
     video_downloader(url, resolution, download_path)

def video_downloader(url, resolution, download_path):
     video = Youtube(url)
     video.streams.filter(res=resolution).first().download(output_path=download_path)

def playlist_downloader(url, resolution, download_path):
     playlist = Playlist(url)
     playlist_videos = playlist.videos
     total_videos = len(playlist_videos)

     print(f'Downloading playlist: {playlist.title}')
     for i, video in enumerate(playlist_videos, start=1):
          print(f'Downloading {i} / {total_videos}: {video.title}')
          video.streams.filter(res=resolution).first().download(output_path=download_path)
     print('Playlist download completed.')

if __name__ == "__main__":
     # Example usage
     url = "https://youtube.com/playlist?list=PLBlnK6fEyqRiVhbXDGLXDk_OQAeuVcp2O&feature=shared"
     resolution = "360p"
     download_path = "/mnt/Chikkoos/Downloads"
     
     main(url, resolution, download_path)