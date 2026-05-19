import io
import os
import logging
from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

CORS(app, origins="*")

@app.after_request
def apply_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
    return response

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Max size is 50MB."}), 413

# Lazy-loaded model
_session = None

def get_session():
    global _session
    if _session is None:
        logging.info("Loading rembg u2netp model...")
        _session = new_session("u2netp")
        logging.info("Model ready.")
    return _session

MAX_PROCESS_SIZE = 1024

@app.route("/", methods=["GET", "OPTIONS"])
def health():
    return jsonify({"status": "ok", "service": "Scklit BG Removal API"})

@app.route("/remove-bg", methods=["POST", "OPTIONS"])
def remove_bg():
    if request.method == "OPTIONS":
        return make_response('', 204)

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty file"}), 400

    try:
        input_bytes = file.read()
        logging.info(f"Received: {file.filename} ({len(input_bytes)} bytes)")

        original = Image.open(io.BytesIO(input_bytes)).convert("RGBA")
        orig_w, orig_h = original.size
        logging.info(f"Resolution: {orig_w}x{orig_h}")

        # Downscale for AI processing
        scale = 1.0
        if max(orig_w, orig_h) > MAX_PROCESS_SIZE:
            scale = MAX_PROCESS_SIZE / max(orig_w, orig_h)
            small = original.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
            logging.info(f"Downscaled to {small.size} for processing")
        else:
            small = original

        # Run removal
        buf = io.BytesIO()
        small.save(buf, format="PNG")
        result_bytes = remove(buf.getvalue(), session=get_session())

        # Upscale result back to original size
        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        if scale < 1.0:
            result = result.resize((orig_w, orig_h), Image.LANCZOS)
            logging.info(f"Upscaled back to {orig_w}x{orig_h}")

        out = io.BytesIO()
        result.save(out, format="PNG")
        out.seek(0)

        logging.info("Done.")
        return send_file(out, mimetype="image/png", download_name="result.png")

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Starting Scklit backend on port {port}...")
    # Use threaded=True so model loading on first request doesn't block health checks
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
