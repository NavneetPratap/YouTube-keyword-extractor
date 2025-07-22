import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pytube import YouTube
import whisper
from rake_nltk import Rake
import tempfile
import os
import re

class YouTubeKeywordApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Keyword Extractor")
        self.geometry("800x800")                  # lowercase ‘x’

        # URL entry
        self.url_label = tk.Label(self, text="Enter the video URL:")
        self.url_label.pack(pady=10)
        self.url_entry = tk.Entry(self, width=50)
        self.url_entry.pack(pady=5)
        self.process_button = tk.Button(
            self, text="Process video", command=self.process_video
        )
        self.process_button.pack(pady=10)

        # Hashtag filter
        self.hashtag_label = tk.Label(self, text="Filter keywords by hashtag:")
        self.hashtag_label.pack(pady=10)          # corrected typo
        self.hashtag_combo = ttk.Combobox(
            self, values=["ALL"], state="readonly"
        )
        self.hashtag_combo.current(0)
        self.hashtag_combo.bind("<<ComboboxSelected>>", self.filter_keywords)
        self.hashtag_combo.pack(pady=5)

        # Result area
        self.result_text = scrolledtext.ScrolledText(self, width=70, height=20)
        self.result_text.pack(pady=10)

        # internal state
        self.all_keywords = []
        self.hashtags = []                        # <-- initialize empty list

    def process_video(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return

        # Load video metadata
        try:
            yt = YouTube(url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load YouTube video: {e}")
            return

        # Extract hashtags from description
        description = yt.description or ""
        self.hashtags = self.extract_hashtags(description)
        hashtag_values = ["ALL"] + self.hashtags
        self.hashtag_combo['values'] = hashtag_values
        self.hashtag_combo.current(0)

        # Download audio to temp file
        audio_stream = yt.streams.filter(only_audio=True).first()
        tf = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_audio_path = tf.name
        tf.close()
        try:
            audio_stream.download(filename=temp_audio_path)
        except Exception as e:
            messagebox.showerror("Error", f"Downloading audio failed: {e}")
            return

        # Transcribe
        try:
            model = whisper.load_model("base")
            result = model.transcribe(temp_audio_path)
            transcript = result["text"]
        except Exception as e:
            messagebox.showerror("Error", f"Transcription failed: {e}")
            os.remove(temp_audio_path)
            return

        os.remove(temp_audio_path)

        # Extract keywords
        rake = Rake()
        rake.extract_keywords_from_text(transcript)
        self.all_keywords = rake.get_ranked_phrases()

        # Show them
        self.display_keywords(self.all_keywords)

    def extract_hashtags(self, text):
        """
        Use regex to pull #tags from description and dedupe them.
        """
        raw = re.findall(r"#(\w+)", text)
        seen, unique = set(), []
        for tag in raw:
            low = tag.lower()
            if low not in seen:
                seen.add(low)
                unique.append(tag)
        return unique

    def display_keywords(self, keywords):
        """
        Dump the list of keywords into the scrolled text widget.
        """
        self.result_text.delete("1.0", tk.END)
        for kw in keywords:
            self.result_text.insert(tk.END, kw + "\n")

    def filter_keywords(self, event=None):
        """
        If a hashtag is selected, only show keywords containing it.
        """
        sel = self.hashtag_combo.get()
        if sel == "ALL":
            filtered = self.all_keywords
        else:
            term = sel.lower()
            filtered = [kw for kw in self.all_keywords if term in kw.lower()]
        self.display_keywords(filtered)


if __name__ == "__main__":
    app = YouTubeKeywordApp()
    app.mainloop()
