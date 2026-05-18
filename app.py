from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io

app = Flask(__name__)
CORS(app)  # Allow requests from your Netlify site

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
        output_bytes = remove(input_bytes)

        return send_file(
            io.BytesIO(output_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name="result.png"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
