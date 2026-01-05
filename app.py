import os
import uuid
import base64
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe z .env (lokalnie)
load_dotenv()

from flask import (
    Flask,
    request,
    render_template,
    abort,
    jsonify,
    send_file,
)

import fitz  # PyMuPDF

# =============================
# Flask App
# =============================

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB

# Folder do przechowywania podpisanych PDFów
SIGNED_PDFS_FOLDER = os.path.join(os.path.dirname(__file__), 'signed_pdfs')
os.makedirs(SIGNED_PDFS_FOLDER, exist_ok=True)

# =============================
# Pomocnicze – PDF
# =============================

ALLOWED_EXT = {"pdf"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def render_pdf_to_base64_images(pdf_bytes, zoom: float = 1.5):
    """
    Renderuje strony PDF do obrazów PNG zakodowanych w base64
    Zwraca listę dict: [{idx, base64, width, height}, ...]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for i, page in enumerate(doc):
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Konwertuj pixmap do PNG bytes
        png_bytes = pix.tobytes("png")

        # Encode do base64
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
# Endpointy
# =============================

@app.get("/")
def index():
    """Strona główna - upload PDF"""
    return render_template("upload.html")

@app.post("/upload")
def upload():
    """Renderuj strony PDF dla podglądu"""
    if "file" not in request.files:
        abort(400, "Brak pliku")

    f = request.files["file"]
    if f.filename == "":
        abort(400, "Nie wybrano pliku")

    if not allowed_file(f.filename):
        abort(400, "Dozwolone tylko PDF")

    # Renderuj strony do podglądu
    pdf_bytes = f.read()
    pages = render_pdf_to_base64_images(pdf_bytes, zoom=1.5)

    # Zwróć renderowane strony
    return jsonify({
        "success": True,
        "pages": pages,
        "filename": f.filename
    })

@app.post("/submit")
def submit():
    """Zapisz podpisany dokument lokalnie"""
    data = request.get_json(silent=True) or {}
    pages_with_signatures = data.get("pages", [])
    original_pdf_base64 = data.get("original_pdf", "")
    original_filename = data.get("filename", "document.pdf")

    if not original_pdf_base64:
        abort(400, "Brak oryginalnego PDF")

    # Dekoduj oryginalny PDF z base64
    try:
        pdf_bytes = base64.b64decode(original_pdf_base64)
    except Exception:
        abort(400, "Nieprawidłowy format PDF")

    # Generuj doc_id
    doc_id = uuid.uuid4().hex[:12]

    # Otwórz PDF i dodaj podpisy
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

        # Zapisz podpisany PDF do bytes
        signed_pdf_bytes = doc.tobytes()
    finally:
        doc.close()

    # Zapisz podpisany PDF lokalnie na dysku
    pdf_filename = f"{doc_id}.pdf"
    pdf_path = os.path.join(SIGNED_PDFS_FOLDER, pdf_filename)

    with open(pdf_path, 'wb') as f:
        f.write(signed_pdf_bytes)

    return jsonify({
        "success": True,
        "doc_id": doc_id,
        "filename": pdf_filename,
        "message": "Dokument zapisany lokalnie"
    })

@app.get("/download/<string:doc_id>")
def download_pdf(doc_id):
    """Pobierz podpisany PDF"""
    pdf_filename = f"{doc_id}.pdf"
    pdf_path = os.path.join(SIGNED_PDFS_FOLDER, pdf_filename)

    if not os.path.exists(pdf_path):
        abort(404, "Plik nie znaleziony")

    return send_file(
        pdf_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=pdf_filename
    )

@app.get("/health")
def health():
    """Health check dla Vercel"""
    return jsonify({"status": "ok"})

# =============================
# Uruchomienie
# =============================
if __name__ == "__main__":
    # Lokalne uruchomienie
    app.run(host="0.0.0.0", port=5000, debug=True)
