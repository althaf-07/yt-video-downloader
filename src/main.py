import os
import threading
import time
import re
import logging
import ssl
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.utils import platform

ssl._create_default_https_context = ssl._create_unverified_context

if platform == "android":
    from android.permissions import request_permissions, Permission

from pytubefix import Playlist, YouTube

# Configure logging
logging.basicConfig(
    filename="video_downloader.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w"
)
logger = logging.getLogger(__name__)

class VideoDownloaderApp(App):
    def build(self):
        # Call the method to handle the download path
        self.path_handler()
        return VideoDownloaderLayout(download_path=self.download_path)

    def path_handler(self):
        # Set the download path based on the platform
        if platform == "android":
            self.download_path = "/storage/emulated/0/Download/Flash Youtube Downloads"
            # Request permissions for accessing external storage
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
        else:
            self.download_path = "Flash Youtube Downloads"

        # Create the directory if it doesn't exist
        os.makedirs(self.download_path, exist_ok=True)
        logger.info(f"Download path set to: {self.download_path}")


class VideoDownloaderLayout(BoxLayout):
    def __init__(self, download_path, **kwargs):  # Accept download_path as a parameter
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.download_path = download_path  # Store the download_path in an instance variable

        # URL input field
        self.url_input = TextInput(hint_text="Enter YouTube URL", multiline=False)
        self.url_input.bind(text=self.on_url_change)

        # Resolution spinner
        self.resolution_spinner = Spinner(
            text='Select Resolution',
            values=('144', '240', '360', '480', '720', '1080'),
            size_hint=(None, None),
            size=(200, 44)
        )

        # Message label
        self.message_label = Label(size_hint_y=None, height=44)

        # Download button
        self.download_button = Button(text="Download")
        self.download_button.bind(on_press=self.start_download)

        # Toggle button for pause/resume
        self.toggle_button = Button(text="Pause", disabled=True)
        self.toggle_button.bind(on_press=self.toggle_download)

        # Checkbox for numbering playlist videos
        self.numbering_checkbox = CheckBox(size_hint_y=None, height=44)
        self.numbering_checkbox_label = Label(text="Add numbering to playlist videos", size_hint_y=None, height=44)
        self.numbering_checkbox_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=44)
        self.numbering_checkbox_layout.add_widget(self.numbering_checkbox)
        self.numbering_checkbox_layout.add_widget(self.numbering_checkbox_label)

        # Hide the checkbox initially
        self.numbering_checkbox_layout.opacity = 0
        self.numbering_checkbox_layout.disabled = True

        # Add widgets to the layout
        self.add_widget(self.url_input)
        self.add_widget(self.resolution_spinner)
        self.add_widget(self.download_button)
        self.add_widget(self.toggle_button)
        self.add_widget(self.numbering_checkbox_layout)
        self.add_widget(self.message_label)

        # Download control variables
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially, it's not paused
        self._is_downloading = False
        self.current_download = None

    def on_url_change(self, instance, value):
        # Check if the URL is a playlist
        if 'playlist' in value.lower():
            # Show the numbering checkbox
            self.numbering_checkbox_layout.opacity = 1
            self.numbering_checkbox_layout.disabled = False
        else:
            # Hide the numbering checkbox
            self.numbering_checkbox_layout.opacity = 0
            self.numbering_checkbox_layout.disabled = True

        logger.debug(f"URL changed: {value}")

    def start_download(self, instance):
        url = self.url_input.text.strip()
        resolution = self.resolution_spinner.text.strip()

        if resolution == 'Select Resolution':
            self.message_label.text = "Please select a valid resolution."
            logger.warning("Download attempted without selecting a valid resolution.")
            return

        self.message_label.text = "Starting download..."
        self.download_button.disabled = True
        self.toggle_button.disabled = False
        self._is_downloading = True
        logger.info(f"Starting download: {url} at resolution {resolution}")
        threading.Thread(target=self.download, args=(url, resolution)).start()

    def download(self, url, resolution):
        # No need to call path_handler here anymore

        if 'playlist' in url:
            logger.info(f"Downloading playlist: {url}")
            self.playlist_downloader(url, resolution)
        else:
            logger.info(f"Downloading video: {url}")
            self.video_downloader(url, resolution)

        # Re-enable the download button after download ends
        self.download_button.disabled = False

    def video_downloader(self, url: str, resolution: str):
        try:
            video = YouTube(url)
            self.message_label.text = f"Video title: {video.title}"
            stream = video.streams.filter(res=resolution).first()

            if not stream:
                self.message_label.text = f"Resolution {resolution} not available for {video.title}. Downloading highest resolution."
                logger.warning(f"Resolution {resolution} not available for {video.title}.")
                stream = video.streams.get_highest_resolution()
                if not stream:
                    self.message_label.text = "No available streams for this video."
                    logger.error("No available streams found.")
                    return  # Exit the download function

            self.current_download = stream
            logger.info(f"Starting download for video: {video.title}")
            self._download_stream(stream, video.title)
        except Exception as e:
            self.message_label.text = f"Error initializing download: {str(e)}"
            logger.error(f"Error initializing download for video {url}: {str(e)}")

    def _download_stream(self, stream, title, folder=None):
        """Download the stream with pause/resume functionality."""
        hidden_filename = f".pending-{title}.mp4"  # Use .mp4 or the appropriate file extension
        self.message_label.text = f"Downloading: {title}"
        self._pause_event.clear()  # Make sure it's not paused

        # Use the playlist folder if provided; otherwise, use the main download path
        if folder:
            filepath = os.path.join(folder, hidden_filename)
        else:
            filepath = os.path.join(self.download_path, hidden_filename)

        logger.debug(f"Downloading stream to {filepath}")
        self._download_file(stream, filepath)

    def playlist_downloader(self, url: str, resolution: str):
        """Download all videos from a playlist."""
        try:
            playlist = Playlist(url)
            playlist_name = playlist.title
            sanitized_playlist_name = re.sub(r'[^\w\-_\. ]', '_', playlist_name)
            video_urls = playlist.video_urls

            # Make a folder for the playlist
            playlist_folder = os.path.join(self.download_path, sanitized_playlist_name)
            os.makedirs(playlist_folder, exist_ok=True)
            logger.info(f"Created folder for playlist: {playlist_folder}")

            for i, video_url in enumerate(video_urls, start=1):
                video = YouTube(video_url)
                stream = video.streams.filter(res=resolution).first()

                if not stream:
                    self.message_label.text = f"Resolution {resolution} not available for {video.title}. Downloading highest resolution."
                    logger.warning(f"Resolution {resolution} not available for {video.title}.")
                    stream = video.streams.get_highest_resolution()
                    if not stream:
                        self.message_label.text = f"No available streams for {video.title}."
                        logger.error(f"No available streams for {video.title}.")
                        continue

                self.current_download = stream

                # Add numbering to the title if the checkbox is checked
                title = f"{i} _ {video.title}" if self.numbering_checkbox.active else video.title
                logger.info(f"Downloading video {i}: {video.title}")

                # Pass the playlist folder to _download_stream
                self._download_stream(stream, title, playlist_folder)

            # Re-enable the download button after finishing the loop
            self.download_button.disabled = False
        except Exception as e:
            self.message_label.text = f"Error downloading playlist: {str(e)}"
            logger.error(f"Error downloading playlist {url}: {str(e)}")

    def _download_file(self, stream, filepath):
        """Handle the actual download process."""
        try:
            stream.download(output_path=os.path.dirname(filepath), filename=os.path.basename(filepath))
            original_filename = os.path.basename(filepath).replace(".pending-", "", 1)
            original_filepath = os.path.join(os.path.dirname(filepath), original_filename)
            os.rename(filepath, original_filepath)
            self.message_label.text = f"Downloaded: {original_filename}"
            logging.info(f"Downloaded: {original_filename}")
        except Exception as e:
            self.message_label.text = f"Error downloading: {str(e)}"
            logging.error(f"Error downloading file: {str(e)}")
            self.download_button.disabled = False
            return

        while self._is_downloading and self._pause_event.is_set():
            time.sleep(1)

        if self._is_downloading:
            self.message_label.text = f"Download complete: {original_filename}"
            logging.info(f"Download complete: {original_filename}")

        self.download_button.disabled = False

    def toggle_download(self, instance):
        """Pause or resume the download process."""
        if self._is_downloading:
            if self._pause_event.is_set():
                self._pause_event.clear()  # Resume
                self.toggle_button.text = "Pause"
                logger.info("Resuming download...")
            else:
                self._pause_event.set()  # Pause
                self.toggle_button.text = "Resume"
                logger.info("Pausing download...")

if __name__ == "__main__":
    VideoDownloaderApp().run()