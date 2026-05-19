from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image
import io
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 50MB."}), 413

# Lightweight model — fits in 512MB free tier
logging.info("Loading rembg model...")
session = new_session("u2netp")
logging.info("Model loaded.")

MAX_PROCESS_SIZE = 1024  # Process at max 1024px on longest side, then scale result back up

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Scklit BG Removal API"})

@app.route("/remove-bg", methods=["POST"])
def remove_bg():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        input_bytes = file.read()
        logging.info(f"Processing: {file.filename}, size: {len(input_bytes)} bytes")

        # Open original image
        original = Image.open(io.BytesIO(input_bytes)).convert("RGBA")
        orig_w, orig_h = original.size
        logging.info(f"Original resolution: {orig_w}×{orig_h}")

        # Downscale for processing if larger than MAX_PROCESS_SIZE
        scale_factor = 1.0
        if max(orig_w, orig_h) > MAX_PROCESS_SIZE:
            scale_factor = MAX_PROCESS_SIZE / max(orig_w, orig_h)
            proc_w = int(orig_w * scale_factor)
            proc_h = int(orig_h * scale_factor)
            process_img = original.resize((proc_w, proc_h), Image.LANCZOS)
            logging.info(f"Downscaled to {proc_w}×{proc_h} for processing")
        else:
            process_img = original

        # Run background removal on downscaled image
        proc_bytes = io.BytesIO()
        process_img.save(proc_bytes, format="PNG")
        proc_bytes.seek(0)
        result_bytes = remove(proc_bytes.read(), session=session)

        # Load the mask result
        result_img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        # Scale result back up to original resolution if we downscaled
        if scale_factor < 1.0:
            result_img = result_img.resize((orig_w, orig_h), Image.LANCZOS)
            logging.info(f"Upscaled result back to {orig_w}×{orig_h}")

        # Return final PNG
        out = io.BytesIO()
        result_img.save(out, format="PNG")
        out.seek(0)

        logging.info("Done.")
        return send_file(out, mimetype="image/png", as_attachment=False, download_name="result.png")

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
