import base64
from dotenv import load_dotenv

# Load environment variables from .env (locally)
load_dotenv()

from flask import (
    Flask,
    request,
    render_template,
    abort,
    jsonify,
)

import fitz  # PyMuPDF

# =============================
# Flask App
# =============================

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB

# No longer storing PDFs on server - returning directly to client

# =============================
# Helpers – PDF
# =============================

ALLOWED_EXT = {"pdf"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def render_pdf_to_base64_images(pdf_bytes, zoom: float = 1.5):
    """
    Renders PDF pages to PNG images encoded in base64
    Returns list of dict: [{idx, base64, width, height}, ...]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for i, page in enumerate(doc):
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert pixmap to PNG bytes
        png_bytes = pix.tobytes("png")

        # Encode to base64
        base64_img = base64.b64encode(png_bytes).decode('utf-8')

        pages.append({
            "idx": i,
            "base64": base64_img,
            "width": pix.width,
            "height": pix.height
        })

    doc.close()
    return pages

# =============================
# Endpoints
# =============================

@app.get("/")
def index():
    """Main page - upload PDF"""
    return render_template("upload.html")

@app.post("/upload")
def upload():
    """Render PDF pages for preview"""
    if "file" not in request.files:
        abort(400, "No file")

    f = request.files["file"]
    if f.filename == "":
        abort(400, "No file selected")

    if not allowed_file(f.filename):
        abort(400, "Only PDF allowed")

    # Render pages for preview
    pdf_bytes = f.read()
    pages = render_pdf_to_base64_images(pdf_bytes, zoom=1.5)

    # Return rendered pages
    return jsonify({
        "success": True,
        "pages": pages,
        "filename": f.filename
    })

@app.post("/submit")
def submit():
    """Return signed document directly as base64"""
    data = request.get_json(silent=True) or {}
    pages_with_signatures = data.get("pages", [])
    original_pdf_base64 = data.get("original_pdf", "")
    original_filename = data.get("filename", "document.pdf")

    if not original_pdf_base64:
        abort(400, "No original PDF")

    # Decode original PDF from base64
    try:
        pdf_bytes = base64.b64decode(original_pdf_base64)
    except Exception:
        abort(400, "Invalid PDF format")

    # Open PDF and add signatures
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        for item in pages_with_signatures:
            idx = int(item.get("index", 0))
            if idx < 0 or idx >= len(doc):
                continue

            dataURL = item.get("dataURL", "")
            if not dataURL.startswith("data:image/png;base64,"):
                continue

            b64 = dataURL.split(",", 1)[1]
            png_bytes = base64.b64decode(b64)

            page = doc.load_page(idx)
            rect = page.rect
            page.insert_image(rect, stream=png_bytes, keep_proportion=False, overlay=True)

        # Save signed PDF to bytes
        signed_pdf_bytes = doc.tobytes()
    finally:
        doc.close()

    # Return signed PDF as base64
    signed_pdf_base64 = base64.b64encode(signed_pdf_bytes).decode('utf-8')

    return jsonify({
        "success": True,
        "pdf_base64": signed_pdf_base64,
        "filename": original_filename
    })

@app.get("/health")
def health():
    """Health check for Vercel"""
    return jsonify({"status": "ok"})

# =============================
# Run
# =============================
if __name__ == "__main__":
    # Local run
    app.run(host="0.0.0.0", port=5000, debug=True)
