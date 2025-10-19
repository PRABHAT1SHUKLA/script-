from pytube import YouTube
import os

def download_video(url, output_path="./downloads", resolution="720p"):
    """Download YouTube video."""
    
    try:
        yt = YouTube(url)
        
        print(f"Title: {yt.title}")
        print(f"Duration: {yt.length}s")
        print(f"Views: {yt.views:,}")
        
        # Get stream
        stream = yt.streams.filter(
            progressive=True, 
            file_extension="mp4",
            res=resolution
        ).first()
        
        if not stream:
            print(f"Resolution {resolution} not available.")
            print("Available resolutions:")
            for s in yt.streams.filter(progressive=True, file_extension="mp4"):
                print(f"  - {s.resolution}")
            return
        
        # Download
        print(f"\nDownloading {resolution}...")
        stream.download(output_path)
        print(f"✓ Downloaded: {yt.title}")
        
    except Exception as e:
        print(f"Error: {e}")

def download_audio(url, output_path="./downloads"):
    """Download only audio from YouTube."""
    try:
        yt = YouTube(url)
        audio = yt.streams.filter(only_audio=True).first()
        
        print(f"Downloading audio: {yt.title}")
        output = audio.download(output_path)
        
        # Rename to .mp3
        base, _ = os.path.splitext(output)
        new_file = base + '.mp3'
        os.rename(output, new_file)
        
        print(f"✓ Downloaded: {new_file}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    url = input("Enter YouTube URL: ")
    choice = input("Download (v)ideo or (a)udio? ").lower()
    
    if choice == 'v':
        download_video(url)
    else:
        download_audio(url)
