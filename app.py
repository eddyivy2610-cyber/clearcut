from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from rembg import remove, new_session
import os
import zipfile
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

# Initialize the rembg session globally to save memory
model_session = new_session(model_name='u2netp')


@app.route('/')
def index():
    backend_url = request.host_url.rstrip('/')
    return render_template('index.html', backend_url=backend_url)

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route('/api-docs')
def api_docs():
    backend_url = request.host_url.rstrip('/')
    return render_template('api.html', backend_url=backend_url)

@app.route('/upload')
def upload():
    backend_url = request.host_url.rstrip('/')
    return render_template('upload.html', backend_url=backend_url)




import io
from PIL import Image

def optimize_image_for_processing(image_bytes, max_dim=1920):
    """Downscale large images to max_dim to keep memory usage under Render 512MB limit."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        output_buffer = io.BytesIO()
        # Save as PNG or JPEG depending on mode
        img.save(output_buffer, format=img.format or 'PNG')
        return output_buffer.getvalue()
    except Exception as e:
        print(f"Image optimization warning: {e}")
        return image_bytes

@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    if 'images' not in request.files:
        return jsonify({"error": "No image(s) provided"}), 400

    files = request.files.getlist('images')
    output_files = []

    temp_dir = tempfile.mkdtemp()

    for file in files:
        if file.filename == '':
            continue

        try:
            input_image = file.read()
            optimized_image = optimize_image_for_processing(input_image)
            output_image = remove(optimized_image, session=model_session)
            output_path = os.path.join(temp_dir, f"output_{os.path.splitext(file.filename)[0]}.png")
            with open(output_path, "wb") as f:
                f.write(output_image)
            output_files.append(output_path)

        except Exception as e:
            print(f"Error processing file {file.filename}: {e}")
            continue

    if len(output_files) == 0:
        return jsonify({"error": "No valid images processed"}), 400

    if len(output_files) == 1:
        @after_this_request
        def cleanup_single_file(response):
            try:
                os.remove(output_files[0])
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Cleanup error: {e}")
            return response
        return send_file(output_files[0], mimetype='image/png', as_attachment=True)

    zip_path = os.path.join(temp_dir, "processed_images.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for path in output_files:
            zipf.write(path, os.path.basename(path))
            os.remove(path)

    @after_this_request
    def cleanup_zip_file(response):
        try:
            os.remove(zip_path)
            os.rmdir(temp_dir)
        except Exception as e:
            print(f"Cleanup error: {e}")
        return response

    return send_file(zip_path, mimetype='application/zip', as_attachment=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
