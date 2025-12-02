from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import subprocess
import json
import os
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
import time
import sys
import re

app = Flask(__name__)
app.config["MEDIA_FOLDER"] = "media"
app.config["DB_FILE"] = "db.json"

Path(app.config["MEDIA_FOLDER"]).mkdir(exist_ok=True)

# Store download progress globally
download_progress = {}


def load_db():
    if os.path.exists(app.config["DB_FILE"]):
        with open(app.config["DB_FILE"], "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_db(data):
    with open(app.config["DB_FILE"], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    filename = re.sub(r"\s+", " ", filename)
    return filename[:200]  # Limit filename length


def get_file_size(filepath):
    """Get file size in human readable format"""
    try:
        size = os.path.getsize(filepath)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    except:
        return "Unknown"


def compress_video(input_file, output_file, crf=23, preset="medium"):
    """
    Compress video using H.264 with lossless audio
    CRF: 18-28 (18=nearly lossless, 23=default, 28=lower quality)
    """
    try:
        print(f"[ClipShr] Compressing: {os.path.basename(input_file)}")

        # Get video codec info
        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_file,
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_codec = result.stdout.strip()

        # Compression command with high quality settings
        cmd = [
            "ffmpeg",
            "-i",
            input_file,
            "-c:v",
            "libx264",  # H.264 codec
            "-crf",
            str(crf),  # Quality (lower = better)
            "-preset",
            preset,  # Encoding speed vs compression
            "-c:a",
            "aac",  # Audio codec
            "-b:a",
            "192k",  # Audio bitrate
            "-movflags",
            "+faststart",  # Enable streaming
            "-y",
            output_file,
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        # Check compression results
        original_size = os.path.getsize(input_file)
        compressed_size = os.path.getsize(output_file)
        reduction = ((original_size - compressed_size) / original_size) * 100

        print(f"[ClipShr] ✓ Compressed: {reduction:.1f}% reduction")
        print(f"[ClipShr]   Original: {get_file_size(input_file)}")
        print(f"[ClipShr]   Compressed: {get_file_size(output_file)}")

        return True
    except Exception as e:
        print(f"[ClipShr] Compression error: {str(e)}", file=sys.stderr)
        return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        url = request.json.get("url")
        if not url:
            return jsonify({"error": "URL is required"}), 400

        # Enhanced yt-dlp options
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": False,
            "socket_timeout": 30,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []
            seen_combinations = set()

            # Get all formats
            all_formats = info.get("formats", [])

            # Separate video and audio formats
            video_formats = [
                f for f in all_formats if f.get("vcodec") != "none" and f.get("height")
            ]

            audio_formats = [
                f
                for f in all_formats
                if f.get("acodec") != "none" and f.get("vcodec") == "none"
            ]

            # Get best audio format ID
            best_audio = None
            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get("abr", 0) or 0)

            # Sort video formats by height
            video_formats.sort(key=lambda x: x.get("height", 0), reverse=True)

            for f in video_formats:
                height = f.get("height")
                fps = f.get("fps", 30)
                vcodec = f.get("vcodec", "unknown")
                ext = f.get("ext", "mp4")

                # Create unique identifier
                format_key = f"{height}_{fps}"

                if height and format_key not in seen_combinations:
                    seen_combinations.add(format_key)

                    # Determine actual codec
                    codec_name = "H.264"
                    if "vp09" in vcodec or "vp9" in vcodec:
                        codec_name = "VP9"
                    elif "av01" in vcodec:
                        codec_name = "AV1"
                    elif "avc" in vcodec:
                        codec_name = "H.264"

                    # Build format string
                    format_id = f.get("format_id")
                    if best_audio:
                        format_string = f"{format_id}+{best_audio.get('format_id')}"
                    else:
                        format_string = format_id

                    # Get filesize estimate
                    filesize = f.get("filesize") or f.get("filesize_approx")
                    if filesize:
                        filesize_str = get_file_size_from_bytes(filesize)
                    else:
                        filesize_str = "Unknown"

                    formats.append(
                        {
                            "format_id": format_string,
                            "ext": ext,
                            "resolution": f"{height}p",
                            "fps": fps,
                            "filesize": filesize_str,
                            "filesize_bytes": filesize,
                            "type": "video",
                            "codec": codec_name,
                            "vcodec": vcodec[:20],  # Truncate for display
                        }
                    )

            # Add audio-only option
            if best_audio:
                filesize = best_audio.get("filesize") or best_audio.get(
                    "filesize_approx"
                )
                formats.append(
                    {
                        "format_id": best_audio.get("format_id"),
                        "ext": "mp3",
                        "resolution": "Audio Only",
                        "filesize": (
                            get_file_size_from_bytes(filesize)
                            if filesize
                            else "Unknown"
                        ),
                        "filesize_bytes": filesize,
                        "type": "audio",
                        "codec": best_audio.get("acodec", "unknown")[:20],
                    }
                )

            # Fallback if no formats found
            if not formats:
                formats.append(
                    {
                        "format_id": "best",
                        "ext": "mp4",
                        "resolution": "Best Available",
                        "filesize": "Unknown",
                        "filesize_bytes": None,
                        "type": "video",
                        "codec": "Unknown",
                    }
                )

            return jsonify(
                {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "formats": formats,
                }
            )

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Unsupported URL" in error_msg:
            return jsonify({"error": "Unsupported URL or video not available"}), 400
        elif "Video unavailable" in error_msg:
            return jsonify({"error": "Video is unavailable or private"}), 400
        else:
            return jsonify({"error": f"Download error: {error_msg}"}), 400
    except Exception as e:
        print(f"[ClipShr] Analysis Error: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 400


def get_file_size_from_bytes(bytes_size):
    """Convert bytes to human readable format"""
    if not bytes_size:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


@app.route("/download", methods=["POST"])
def download():
    download_id = None
    try:
        data = request.json
        url = data.get("url")
        format_id = data.get("format_id")
        trim_start = data.get("trim_start")
        trim_end = data.get("trim_end")
        convert_to = data.get("convert_to")
        extract_audio = data.get("extract_audio")
        compress = data.get("compress", True)  # Auto-compress by default

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_id = timestamp

        # Initialize progress
        download_progress[download_id] = {
            "status": "starting",
            "percent": 0,
            "speed": "0 KB/s",
            "eta": "calculating...",
        }

        print(f"\n[ClipShr] Download started with ID: {download_id}")

        def progress_hook(d):
            try:
                if d["status"] == "downloading":
                    downloaded = d.get("downloaded_bytes", 0)
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                    if total > 0:
                        percent = (downloaded / total) * 100
                    else:
                        percent = 0

                    speed = d.get("speed")
                    if speed:
                        speed_str = (
                            f"{speed / 1024:.2f} KB/s"
                            if speed < 1024 * 1024
                            else f"{speed / (1024 * 1024):.2f} MB/s"
                        )
                    else:
                        speed_str = "0 KB/s"

                    eta = d.get("eta", 0)
                    eta_str = f"{eta}s" if eta else "Unknown"

                    download_progress[download_id] = {
                        "status": "downloading",
                        "percent": round(percent, 1),
                        "speed": speed_str,
                        "eta": eta_str,
                        "downloaded": get_file_size_from_bytes(downloaded),
                        "total": get_file_size_from_bytes(total),
                    }

                elif d["status"] == "finished":
                    download_progress[download_id] = {
                        "status": "processing",
                        "percent": 100,
                        "speed": "Complete",
                        "eta": "Processing...",
                    }
                    print(f"\n[ClipShr] Download finished, processing...")
            except Exception as e:
                print(f"\n[ClipShr] Progress hook error: {str(e)}", file=sys.stderr)

        # Prepare output template with sanitized filename
        output_template = os.path.join(
            app.config["MEDIA_FOLDER"], f"{timestamp}_%(title)s.%(ext)s"
        )

        # Determine format string
        if extract_audio:
            format_string = "bestaudio/best"
        elif format_id and format_id != "best":
            format_string = format_id
        else:
            format_string = "bestvideo+bestaudio/best"

        # Enhanced yt-dlp options
        ydl_opts = {
            "format": format_string,
            "outtmpl": output_template,
            "quiet": False,
            "no_warnings": False,
            "ignoreerrors": False,
            "progress_hooks": [progress_hook],
            "merge_output_format": "mp4",
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
            "postprocessors": [],
        }

        # Add audio extraction if needed
        if extract_audio:
            ydl_opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            )

        print(f"[ClipShr] Format: {format_string}")

        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_filename = ydl.prepare_filename(info)

        # Handle filename based on whether audio was extracted
        if extract_audio:
            filename = base_filename.rsplit(".", 1)[0] + ".mp3"
        else:
            filename = base_filename

        print(f"\n[ClipShr] Downloaded: {filename}")

        final_file = filename
        file_type = "audio" if extract_audio else "video"

        # Post-processing
        if trim_start or trim_end or convert_to or (compress and not extract_audio):
            download_progress[download_id]["status"] = "post-processing"
            download_progress[download_id]["eta"] = "Post-processing..."
            print(f"[ClipShr] Post-processing...")

            base, ext = os.path.splitext(filename)
            temp_file = filename

            # Trimming
            if trim_start or trim_end:
                trim_output = f"{base}_trimmed{ext}"
                cmd = ["ffmpeg", "-i", temp_file]

                if trim_start:
                    cmd.extend(["-ss", str(trim_start)])
                if trim_end:
                    cmd.extend(["-to", str(trim_end)])

                cmd.extend(["-c", "copy", "-avoid_negative_ts", "1", "-y", trim_output])

                print(f"[ClipShr] Trimming...")
                subprocess.run(cmd, capture_output=True, check=True)

                if os.path.exists(temp_file):
                    os.remove(temp_file)
                temp_file = trim_output

            # Conversion or Compression
            if convert_to:
                final_file = f"{base}.{convert_to}"
                print(f"[ClipShr] Converting to {convert_to}...")
                subprocess.run(
                    ["ffmpeg", "-i", temp_file, "-y", final_file],
                    capture_output=True,
                    check=True,
                )
                if os.path.exists(temp_file) and temp_file != filename:
                    os.remove(temp_file)

            elif compress and not extract_audio:
                # Compress video
                compressed_file = f"{base}_compressed{ext}"
                if compress_video(temp_file, compressed_file, crf=23, preset="medium"):
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    final_file = compressed_file
                else:
                    final_file = temp_file
            else:
                final_file = temp_file

        # Auto-compress if no other processing was done
        elif compress and not extract_audio and os.path.exists(filename):
            download_progress[download_id]["status"] = "compressing"
            download_progress[download_id]["eta"] = "Compressing..."

            base, ext = os.path.splitext(filename)
            compressed_file = f"{base}_compressed{ext}"

            if compress_video(filename, compressed_file, crf=23, preset="medium"):
                os.remove(filename)
                final_file = compressed_file
            else:
                final_file = filename

        print(f"[ClipShr] ✓ Complete: {os.path.basename(final_file)}")
        print(f"[ClipShr]   Size: {get_file_size(final_file)}\n")

        download_progress[download_id]["status"] = "complete"
        download_progress[download_id]["percent"] = 100
        download_progress[download_id]["eta"] = "Done"

        # Save to database
        db = load_db()
        db.append(
            {
                "url": url,
                "filename": os.path.basename(final_file),
                "type": file_type,
                "format": format_id,
                "timestamp": timestamp,
                "size": get_file_size(final_file),
            }
        )
        save_db(db)

        return jsonify(
            {
                "success": True,
                "filename": os.path.basename(final_file),
                "path": final_file,
                "download_id": download_id,
                "size": get_file_size(final_file),
            }
        )

    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
        print(f"[ClipShr] ✗ {error_msg}", file=sys.stderr)

        if download_id and download_id in download_progress:
            download_progress[download_id]["status"] = "error"

        return jsonify({"error": error_msg}), 400

    except Exception as e:
        print(f"[ClipShr] ✗ Error: {str(e)}", file=sys.stderr)
        import traceback

        traceback.print_exc()

        if download_id and download_id in download_progress:
            download_progress[download_id]["status"] = "error"

        return jsonify({"error": str(e)}), 400


@app.route("/progress/<download_id>")
def progress(download_id):
    """Get download progress"""
    if download_id in download_progress:
        return jsonify(download_progress[download_id])
    return jsonify({"status": "unknown", "percent": 0, "speed": "-", "eta": "-"})


@app.route("/history")
def history():
    return jsonify(load_db())


@app.route("/delete", methods=["POST"])
def delete_file():
    try:
        filename = request.json.get("filename")
        if not filename:
            return jsonify({"error": "Filename is required"}), 400

        # Security: prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return jsonify({"error": "Invalid filename"}), 400

        file_path = os.path.join(app.config["MEDIA_FOLDER"], filename)

        # Delete the file
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[ClipShr] Deleted file: {filename}")

        # Update database
        db = load_db()
        db = [item for item in db if item.get("filename") != filename]
        save_db(db)

        return jsonify({"success": True, "message": "File deleted"})
    except Exception as e:
        print(f"[ClipShr] Delete error: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 400


@app.route("/clear-history", methods=["POST"])
def clear_history():
    try:
        db = load_db()

        # Delete all files
        deleted_count = 0
        for item in db:
            filename = item.get("filename")
            if filename:
                file_path = os.path.join(app.config["MEDIA_FOLDER"], filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1

        # Clear database
        save_db([])

        print(f"[ClipShr] Cleared history ({deleted_count} files deleted)")

        return jsonify(
            {
                "success": True,
                "message": f"History cleared, {deleted_count} files deleted",
            }
        )
    except Exception as e:
        print(f"[ClipShr] Clear history error: {str(e)}", file=sys.stderr)
        return jsonify({"error": str(e)}), 400


@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory(app.config["MEDIA_FOLDER"], filename)


def open_browser(port):
    webbrowser.open(f"http://localhost:{port}")


def is_port_available(port):
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except:
        return False


def find_free_port():
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


if __name__ == "__main__":
    if is_port_available(5000):
        port = 5000
    else:
        port = find_free_port()
        print(f"\n⚠️  Port 5000 is blocked/in use. Using port {port} instead.")
        print(f"🌐 Opening browser at http://localhost:{port}\n")

    threading.Timer(1.5, lambda: open_browser(port)).start()
    app.run(debug=False, port=port, host="127.0.0.1", threaded=True)
