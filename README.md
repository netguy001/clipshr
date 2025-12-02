# ClipShr - Video Downloader & Processor


A powerful, user-friendly web-based video downloader with advanced processing features. Download videos from multiple platforms, trim, convert, compress, and extract audio - all with a beautiful interface.

# Check out the test_images/ folder for:  

- Application UI screenshots 
- Terminal/console output examples
- Sample downloaded video from yt  

These will give you a quick preview of ClipShr

## ✨ Features

### 🎬 Video Download
- **Multi-platform support** - Download from YouTube, Vimeo, and 1000+ other sites (via yt-dlp)
- **Quality selection** - Choose from all available video qualities (360p, 720p, 1080p, 4K, etc.)
- **Format options** - Multiple codec support (H.264, VP9, AV1)
- **Audio extraction** - Download audio-only in MP3 format (192kbps)
- **Real-time progress** - Live download progress with speed and ETA tracking

### 🛠️ Processing Features
- **Video Trimming** - Cut specific sections using start/end timestamps
- **Format Conversion** - Convert to MP4, AVI, MKV, and more
- **Smart Compression** - Automatic H.264 compression with quality preservation
  - Uses CRF 23 for optimal quality/size balance
  - Maintains audio quality at 192kbps AAC
  - Typically achieves 30-60% size reduction
- **Audio Extraction** - Extract audio from videos as MP3 files

### 📊 Management
- **Download History** - Track all your downloads with timestamps
- **File Management** - View, delete, or download files directly
- **File Size Display** - See original and compressed file sizes
- **Batch Operations** - Clear entire history with one click

### 🎨 User Interface
- Clean, modern design
- Real-time video preview and metadata
- Progress indicators with detailed stats
- Responsive layout for all devices

## 🚀 Installation

### Prerequisites
- **Python 3.7+**
- **FFmpeg** (for video processing)

### Step 1: Install FFmpeg

#### Windows
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract and add to system PATH

Or use chocolatey:
```bash
choco install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

### Step 2: Install ClipShr

1. **Clone the repository**
```bash
git clone https://github.com/netguy001/clipshr.git
cd clipshr
```

2. **Install Python dependencies**
```bash
pip install flask yt-dlp
```

3. **Run the application**
```bash
python app.py
```

The application will automatically open in your default browser at `http://localhost:5000`

## 📖 Usage Guide

### Basic Download

1. **Paste Video URL**
   - Enter any supported video URL in the input field
   - Click "Analyze" to fetch video information

2. **Select Quality**
   - Choose your preferred video quality from the dropdown
   - View file size estimates for each quality
   - Select "Audio Only" for MP3 extraction

3. **Download**
   - Click "Download" to start
   - Monitor real-time progress with speed and ETA
   - Files are saved to the `media/` folder

### Advanced Features

#### Trimming Videos
1. Enable "Trim Video" checkbox
2. Enter start time (e.g., `00:30` for 30 seconds)
3. Enter end time (e.g., `02:15` for 2 minutes 15 seconds)
4. Format: `MM:SS` or `HH:MM:SS`

#### Format Conversion
1. Enable "Convert Format" checkbox
2. Select output format (MP4, AVI, MKV, MOV, WEBM)
3. Conversion happens automatically after download

#### Audio Extraction
1. Enable "Extract Audio Only" checkbox
2. Download will extract audio as high-quality MP3 (192kbps)
3. Perfect for music, podcasts, or audiobooks

#### Video Compression
- **Automatic**: Enabled by default for all video downloads
- **Quality**: Uses CRF 23 (high quality with good compression)
- **Benefits**: Reduces file size by 30-60% without visible quality loss
- **Settings**: H.264 codec, AAC audio, optimized for streaming

### Managing Downloads

#### View History
- All downloads appear in the "Download History" section
- Shows filename, format, timestamp, and file size
- Click filenames to download/play files

#### Delete Files
- Click the "Delete" button next to any file
- Removes file from disk and history

#### Clear All History
- Click "Clear All History" button
- Removes all downloaded files and history entries
- **Warning**: This action cannot be undone!

## 🔧 Configuration

### Custom Media Folder
Edit `app.py` to change the download location:
```python
app.config["MEDIA_FOLDER"] = "your/custom/path"
```

### Compression Settings
Adjust compression quality in the `compress_video()` function:
```python
# Lower CRF = better quality, larger file (18-28 recommended)
compress_video(input_file, output_file, crf=23, preset="medium")
```

**CRF Values:**
- 18: Nearly lossless (large files)
- 23: High quality (default, recommended)
- 28: Lower quality (smaller files)

**Presets:**
- `ultrafast`: Fastest, least compression
- `medium`: Balanced (default)
- `slow`: Better compression, slower encoding

### Port Configuration
The app uses port 5000 by default. If blocked, it automatically finds a free port.

## 🎯 How It Works

### Architecture
```
┌─────────────┐
│   Browser   │ ← User Interface (HTML/CSS/JS)
└──────┬──────┘
       │
┌──────▼──────┐
│   Flask     │ ← Web Server & API
└──────┬──────┘
       │
┌──────▼──────┐
│   yt-dlp    │ ← Video Download Engine
└──────┬──────┘
       │
┌──────▼──────┐
│   FFmpeg    │ ← Video/Audio Processing
└─────────────┘
```

### Download Process
1. **Analysis**: yt-dlp fetches video metadata and available formats
2. **Selection**: User chooses quality and processing options
3. **Download**: yt-dlp downloads video/audio streams
4. **Merge**: Streams are merged into single file (if needed)
5. **Process**: FFmpeg applies trimming, conversion, or compression
6. **Storage**: Final file is saved with metadata in `db.json`

### File Storage
- **Media**: Downloaded files stored in `media/` folder
- **Database**: Download history saved in `db.json`
- **Format**: `{timestamp}_{title}.{ext}`

## 🌐 Supported Platforms

ClipShr supports 1000+ websites via yt-dlp, including:

- ✅ YouTube
- ✅ Vimeo
- ✅ Dailymotion
- ✅ Facebook
- ✅ Instagram
- ✅ Twitter/X
- ✅ TikTok
- ✅ Reddit
- ✅ Twitch
- ✅ And many more...

Full list: [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## 🛡️ Security Features

- **Path traversal protection** - Prevents accessing files outside media folder
- **Filename sanitization** - Removes invalid characters from filenames
- **Input validation** - Validates URLs and format selections
- **Error handling** - Comprehensive error handling and logging

## ⚡ Performance Tips

1. **Fast Downloads**: Use H.264 formats (better compatibility)
2. **Smaller Files**: Enable compression for significant size reduction
3. **Quick Processing**: Avoid unnecessary conversions
4. **Audio Only**: Use audio extraction instead of downloading full video

## 🐛 Troubleshooting

### "FFmpeg not found"
- Ensure FFmpeg is installed and in system PATH
- Test: Run `ffmpeg -version` in terminal

### "Download failed"
- Check if video is available/public
- Try updating yt-dlp: `pip install --upgrade yt-dlp`
- Some videos may be geo-restricted

### "Port already in use"
- ClipShr will automatically find a free port
- Or manually specify port in `app.py`

### Slow downloads
- Check your internet connection
- Try selecting a lower quality
- Some sites may have rate limiting

## 📝 File Formats

### Video Formats
- **MP4** - Best compatibility (recommended)
- **MKV** - Supports multiple tracks
- **AVI** - Legacy format
- **MOV** - Apple format
- **WEBM** - Web-optimized

### Audio Format
- **MP3** - Universal audio format (192kbps AAC)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License 

## ⚠️ Legal Disclaimer

This tool is for personal use only. Users are responsible for complying with:
- Website Terms of Service
- Copyright laws in their jurisdiction
- Content licensing restrictions

Only download content you have the right to download.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video download engine
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [Flask](https://flask.palletsprojects.com/) - Web framework



⭐ Star this repo if you find it useful!