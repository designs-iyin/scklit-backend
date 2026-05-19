from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from rembg import remove, new_session
import io
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# u2netp is the lightweight model (~4x less memory than u2net, fits in 512MB)
logging.info("Loading rembg model...")
session = new_session("u2netp")
logging.info("Model loaded.")

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
        logging.info(f"Processing image: {file.filename}, size: {len(input_bytes)} bytes")
        output_bytes = remove(input_bytes, session=session)
        logging.info("Image processed successfully")

        return send_file(
            io.BytesIO(output_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name="result.png"
        )

    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
