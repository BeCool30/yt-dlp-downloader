import os
import glob
import tempfile
import static_ffmpeg  # Automatically handles FFmpeg binaries without apt-get
from urllib.parse import quote, unquote
from flask import Flask, render_template, request, send_file, jsonify  # type: ignore
import yt_dlp  # type: ignore

# Initialize FFmpeg binaries automatically
static_ffmpeg.add_paths()

app = Flask(__name__)

# System temp directory works best on cloud containers like Render
DOWNLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'yt_downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


@app.route('/')
def home():
    return render_template("downloader.html")


@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    download_type = request.form.get('type')

    if not url:
        return jsonify({'success': False, 'message': 'Please provide a valid URL.'}), 400

    # Clear old files inside temp download folder
    for old_file in glob.glob(os.path.join(DOWNLOAD_FOLDER, "*")):
        try:
            os.remove(old_file)
        except Exception:
            pass

    # Save format options
    output_template = os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s')

    # Path to secret cookie file on Render
    cookie_path = 'cookies.txt'

    if download_type == 'audio':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'noplaylist': True,
            'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }
    else:
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'noplaylist': True,
            'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        actual_file_name = os.path.basename(filename)

        # Safely URL encode the filename (encodes #, spaces, special chars)
        encoded_filename = quote(actual_file_name)

        return jsonify({
            'success': True,
            'message': 'Download Complete! Starting file save...',
            'file_url': f'/get-file?path={encoded_filename}'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/get-file')
def get_file():
    # Retrieve raw path query and decode special characters
    raw_path = request.args.get('path', '')
    filename = unquote(raw_path)

    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)

    return "File not found", 404


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
