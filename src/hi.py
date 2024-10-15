from pytubefix import YouTube
from pytubefix import YouTube
from pytubefix.cli import on_progress

# Specify the URL of the YouTube video you want to download
video_url = 'https://youtu.be/tPEE9ZwTmy0?feature=shared'

try:
    # Create a YouTube object
    yt = YouTube(video_url, on_progress_callback = on_progress)

    # Select the highest resolution stream available
    stream = yt.streams.filter(res='144p').first()#get_by_resolution('144p')

    # Download the video to the current working directory
    stream.download()

    print(f'Download completed: {yt.title}')
except Exception as e:
    print(f'Error: {e}')
