from flask import Flask, request, jsonify, send_from_directory, render_template
import qrcode
import os
import uuid
from PIL import Image
import io
import base64

app = Flask(__name__)

# ── Folders ──────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
QR_FOLDER     = "qr_codes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER,     exist_ok=True)

# Change this to your real domain when deployed, e.g. "https://myqrapp.com"
BASE_URL = os.environ.get("BASE_URL", "https://qr-code-scanner-fgwa.onrender.com")

# ── Helpers ───────────────────────────────────────────────────────────────────
def make_qr(data: str, filename: str, fg="#000000", bg="#ffffff") -> str:
    """Generate a QR code image and return its file path."""
    qr = qrcode.QRCode(
        version=None,                              # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fg, back_color=bg).convert("RGB")
    out = os.path.join(QR_FOLDER, filename)
    img.save(out)
    return out


def img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate/text", methods=["POST"])
def gen_text():
    """Generate a QR from plain text or a URL typed by the user."""
    body = request.get_json(silent=True) or {}
    data = (body.get("text") or "").strip()
    fg   = body.get("fg", "#000000")
    bg   = body.get("bg", "#ffffff")

    if not data:
        return jsonify(error="No text provided"), 400

    qr_file = f"{uuid.uuid4().hex}.png"
    make_qr(data, qr_file, fg, bg)

    return jsonify(
        qr_url=f"{BASE_URL}/qr/{qr_file}",
        qr_b64=img_to_base64(os.path.join(QR_FOLDER, qr_file)),
        encoded_data=data,
    )


@app.route("/generate/image", methods=["POST"])
def gen_image():
    """
    Upload an image → save it → encode the hosted URL → return the QR.
    The QR itself stays small because it only stores a short URL string.
    """
    file = request.files.get("image")
    fg   = request.form.get("fg", "#000000")
    bg   = request.form.get("bg", "#ffffff")

    if not file or file.filename == "":
        return jsonify(error="No image uploaded"), 400

    # Save the original image
    ext        = os.path.splitext(file.filename)[-1].lower() or ".png"
    img_id     = uuid.uuid4().hex
    img_file   = f"{img_id}{ext}"
    img_path   = os.path.join(UPLOAD_FOLDER, img_file)
    file.save(img_path)

    # The URL that will be encoded in the QR
    hosted_url = f"{BASE_URL}/uploads/{img_file}"

    # Build the QR from that short URL (not the image bytes → stays clean)
    qr_file = f"img_{img_id}.png"
    make_qr(hosted_url, qr_file, fg, bg)

    return jsonify(
        qr_url=f"{BASE_URL}/qr/{qr_file}",
        qr_b64=img_to_base64(os.path.join(QR_FOLDER, qr_file)),
        encoded_data=hosted_url,       # shown in the UI so user understands what's inside
        image_url=hosted_url,
    )


# ── Static file serving ───────────────────────────────────────────────────────
@app.route("/qr/<path:filename>")
def serve_qr(filename):
    return send_from_directory(QR_FOLDER, filename)

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
