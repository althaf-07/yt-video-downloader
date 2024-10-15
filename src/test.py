import os
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from pytubefix import YouTube, Playlist

class DownloaderApp(App):
    def build(self):
        self.title = "YouTube Downloader"

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # URL input field
        self.url_input = TextInput(hint_text='Enter YouTube video/playlist URL', multiline=False)
        layout.add_widget(self.url_input)

        # Resolution selection using Spinner
        self.resolution_spinner = Spinner(
            text='Select Resolution',
            values=('144', '240', '360', '480', '720', '1080'),
            size_hint=(None, None),
            size=(150, 44),
        )
        layout.add_widget(self.resolution_spinner)

        # Download path selection button
        self.download_path_button = Button(text="Select Download Path")
        self.download_path_button.bind(on_press=self.open_filechooser)
        layout.add_widget(self.download_path_button)

        # Download button
        self.download_button = Button(text="Download")
        self.download_button.bind(on_press=self.download_video)
        layout.add_widget(self.download_button)

        # Pause/Resume button
        self.pause_resume_button = Button(text="Pause")
        self.pause_resume_button.bind(on_press=self.pause_resume_download)
        layout.add_widget(self.pause_resume_button)

        # Message label
        self.message_label = Label(size_hint_y=None, height=44)
        layout.add_widget(self.message_label)

        # Progress bar
        self.progress_bar = ProgressBar(max=100)
        layout.add_widget(self.progress_bar)

        # Initialize state variables
        self.paused = False
        self.current_video = None
        self.download_path = None
        self.progress_function = None

        return layout

    def open_filechooser(self, instance):
        """Open a file chooser to select download path."""
        filechooser = FileChooserIconView(path=os.path.expanduser("~"))
        popup_layout = BoxLayout(orientation='vertical')
        popup_layout.add_widget(filechooser)

        # Add a button to confirm selection
        select_button = Button(text="Select Folder", size_hint=(1, 0.1))
        select_button.bind(on_press=lambda x: self.select_path(filechooser, popup))
        popup_layout.add_widget(select_button)

        popup = Popup(title='Choose Download Folder', content=popup_layout, size_hint=(0.9, 0.9))
        popup.open()

    def select_path(self, filechooser, popup):
        """Set the chosen download path."""
        self.download_path = filechooser.path
        self.download_path_button.text = f"Download Folder: {self.download_path}"
        popup.dismiss()

    def download_video(self, instance):
        """Start the download process."""
        url = self.url_input.text
        resolution = self.resolution_spinner.text
        download_path = getattr(self, 'download_path', None)

        if not url:
            self.message_label.text = "Please enter a valid URL."
            return

        if resolution == 'Select Resolution':
            self.message_label.text = "Please select a resolution."
            return

        if not download_path:
            self.message_label.text = "Please choose a download folder."
            return

        # Initialize paused state
        self.paused = False

        # Determine if it's a video or a playlist
        if "playlist" in url:
            self.message_label.text = "Starting playlist download..."
            self.playlist_downloader(url, resolution, download_path)
        else:
            self.message_label.text = "Starting video download..."
            self.video_downloader(url, resolution, download_path)

    def video_downloader(self, url: str, resolution: str, download_path: str):
        """Download a single YouTube video."""
        try:
            self.current_video = YouTube(url, on_progress_callback=self.on_progress)
            stream = self.get_video_stream(self.current_video, resolution)

            if not stream:
                self.message_label.text = f"Resolution {resolution} not available. Downloading highest resolution."
                stream = self.current_video.streams.get_highest_resolution()

            self.message_label.text = f"Downloading: {self.current_video.title}"

            # Start download with a callback for pausing
            self.download_in_chunks(stream, download_path)

        except Exception as e:
            self.message_label.text = f"Error while downloading video: {str(e)}"

    def playlist_downloader(self, url: str, resolution: str, download_path: str):
        """Download all videos from a playlist."""
        try:
            playlist = Playlist(url)
            total_videos = len(playlist.video_urls)

            playlist_folder = os.path.join(download_path, playlist.title.replace(" ", "_"))
            os.makedirs(playlist_folder, exist_ok=True)

            for i, video_url in enumerate(playlist.video_urls, start=1):
                try:
                    video = YouTube(video_url)
                    stream = self.get_video_stream(video, resolution)

                    if not stream:
                        self.message_label.text = f"Resolution {resolution} not available for {video.title}. Downloading highest resolution."
                        stream = video.streams.get_highest_resolution()

                    self.message_label.text = f"Downloading {i}/{total_videos}: {video.title}"
                    self.download_in_chunks(stream, playlist_folder)

                except Exception as e:
                    self.message_label.text = f"Error downloading {video.title}: {str(e)}"

            self.message_label.text = "Playlist download completed."

        except Exception as e:
            self.message_label.text = f"Error while downloading playlist: {str(e)}"

    def get_video_stream(self, video: YouTube, resolution: str):
        """Get the video stream in the desired resolution."""
        stream = video.streams.filter(res=resolution, progressive=True).first()
        return stream

    def download_in_chunks(self, stream, output_path):
        """Download video in chunks, allowing for pause and resume."""
        file_size = stream.filesize
        self.progress_bar.value = 0  # Reset the progress bar
        self.message_label.text = "Download starting..."

        def download_callback(chunk):
            self.on_progress(stream, chunk, stream.filesize - len(chunk))
        
        # Using a generator to simulate chunked download
        self.progress_function = stream.download(output_path=output_path, skip_existing=True, on_progress=download_callback)

    def on_progress(self, stream, chunk, bytes_remaining):
        """Callback for updating progress during download."""
        downloaded = stream.filesize - bytes_remaining
        progress_percent = (downloaded / stream.filesize) * 100
        self.progress_bar.value = progress_percent  # Update progress bar
        self.message_label.text = f"Download progress: {progress_percent:.2f}%"
        if self.paused:
            # Pausing the download
            self.message_label.text = "Download paused."

    def pause_resume_download(self, instance):
        """Pause or resume the download process."""
        if self.paused:
            self.paused = False
            self.pause_resume_button.text = "Pause"
            self.message_label.text = "Resuming download..."
            # Restart download from where it was paused
            self.download_in_chunks(self.current_video.streams.filter(progressive=True).first(), self.download_path)
        else:
            self.paused = True
            self.pause_resume_button.text = "Resume"
            self.message_label.text = "Download paused."

if __name__ == "__main__":
    DownloaderApp().run()