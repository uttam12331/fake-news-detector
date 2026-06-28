"""
PDF Toolkit — an iLovePDF-style PDF editor web app.

Exposes the pdf_toolkit core package over HTTP: merge, split, reorder/delete
pages, rotate, extract pages, password protect/unlock, watermark,
image<->PDF conversion, and compress-to-target-size.
"""
import io
import os
import zipfile

from flask import Flask, jsonify, render_template, request, send_file

from pdf_toolkit import compress, convert, merge, pages, protect, watermark
from pdf_toolkit.errors import PdfToolkitError

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(HERE, "templates"), static_folder=os.path.join(HERE, "static"))

MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.errorhandler(PdfToolkitError)
def _handle_toolkit_error(exc):
    return jsonify({"error": str(exc)}), 400


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/service-worker.js")
def service_worker():
    response = app.send_static_file("service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


def _files_from_request(field_name="files"):
    files = request.files.getlist(field_name)
    if not files:
        single = request.files.get("file")
        files = [single] if single else []
    return [f.read() for f in files if f and f.filename]


def _send_pdf(data: bytes, filename: str):
    return send_file(io.BytesIO(data), mimetype="application/pdf", as_attachment=True, download_name=filename)


def _send_zip(named_files: list[tuple[str, bytes]], zip_name: str):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in named_files:
            zf.writestr(name, data)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/zip", as_attachment=True, download_name=zip_name)


@app.route("/api/merge", methods=["POST"])
def api_merge():
    contents = _files_from_request()
    result = merge.merge_pdfs(contents)
    return _send_pdf(result, "merged.pdf")


@app.route("/api/pages/reorder", methods=["POST"])
def api_reorder():
    contents = _files_from_request()
    spec = request.form.get("order", "")
    count = pages.page_count(contents[0])
    order = pages.parse_page_ranges(spec, count) if spec else list(range(count))
    result = pages.reorder_pages(contents[0], order)
    return _send_pdf(result, "reordered.pdf")


@app.route("/api/pages/delete", methods=["POST"])
def api_delete():
    contents = _files_from_request()
    spec = request.form.get("pages", "")
    count = pages.page_count(contents[0])
    to_delete = pages.parse_page_ranges(spec, count)
    result = pages.delete_pages(contents[0], to_delete)
    return _send_pdf(result, "deleted.pdf")


@app.route("/api/pages/extract", methods=["POST"])
def api_extract():
    contents = _files_from_request()
    spec = request.form.get("pages", "")
    count = pages.page_count(contents[0])
    to_extract = pages.parse_page_ranges(spec, count)
    result = pages.extract_pages(contents[0], to_extract)
    return _send_pdf(result, "extracted.pdf")


@app.route("/api/pages/rotate", methods=["POST"])
def api_rotate():
    contents = _files_from_request()
    degrees = int(request.form.get("degrees", 90))
    spec = request.form.get("pages", "")
    count = pages.page_count(contents[0])
    target = pages.parse_page_ranges(spec, count) if spec else None
    result = pages.rotate_pages(contents[0], degrees, pages=target)
    return _send_pdf(result, "rotated.pdf")


@app.route("/api/split/every-n", methods=["POST"])
def api_split_every_n():
    contents = _files_from_request()
    n = int(request.form.get("n", 1))
    chunks = pages.split_every_n(contents[0], n)
    named = [(f"part-{i + 1}.pdf", c) for i, c in enumerate(chunks)]
    return _send_zip(named, "split.zip")


@app.route("/api/split/ranges", methods=["POST"])
def api_split_ranges():
    contents = _files_from_request()
    spec = request.form.get("ranges", "")
    count = pages.page_count(contents[0])
    range_groups = [pages.parse_page_ranges(r.strip(), count) for r in spec.split(";") if r.strip()]
    chunks = pages.split_by_ranges(contents[0], range_groups)
    named = [(f"part-{i + 1}.pdf", c) for i, c in enumerate(chunks)]
    return _send_zip(named, "split.zip")


@app.route("/api/protect/add", methods=["POST"])
def api_protect_add():
    contents = _files_from_request()
    user_password = request.form.get("password", "")
    owner_password = request.form.get("owner_password") or None
    result = protect.add_password(contents[0], user_password, owner_password)
    return _send_pdf(result, "protected.pdf")


@app.route("/api/protect/remove", methods=["POST"])
def api_protect_remove():
    contents = _files_from_request()
    password = request.form.get("password", "")
    result = protect.remove_password(contents[0], password)
    return _send_pdf(result, "unlocked.pdf")


@app.route("/api/watermark", methods=["POST"])
def api_watermark():
    contents = _files_from_request()
    text = request.form.get("text", "WATERMARK")
    opacity = float(request.form.get("opacity", 0.3))
    font_size = int(request.form.get("font_size", 40))
    rotation = float(request.form.get("rotation", 45))
    result = watermark.add_text_watermark(contents[0], text, opacity=opacity, font_size=font_size, rotation=rotation)
    return _send_pdf(result, "watermarked.pdf")


@app.route("/api/convert/images-to-pdf", methods=["POST"])
def api_images_to_pdf():
    contents = _files_from_request()
    result = convert.images_to_pdf(contents)
    return _send_pdf(result, "converted.pdf")


@app.route("/api/convert/pdf-to-images", methods=["POST"])
def api_pdf_to_images():
    contents = _files_from_request()
    fmt = request.form.get("format", "png").lower()
    dpi = int(request.form.get("dpi", 150))
    images = convert.pdf_to_images(contents[0], dpi=dpi, fmt=fmt)
    ext = "jpg" if fmt in ("jpg", "jpeg") else "png"
    named = [(f"page-{i + 1}.{ext}", img) for i, img in enumerate(images)]
    return _send_zip(named, "pages.zip")


@app.route("/api/compress", methods=["POST"])
def api_compress():
    contents = _files_from_request()
    target_kb = request.form.get("target_kb")
    quality = int(request.form.get("quality", 70))
    target_bytes = int(float(target_kb) * 1024) if target_kb else None
    result = compress.compress(contents[0], target_bytes=target_bytes, quality=quality)
    response = _send_pdf(result.data, "compressed.pdf")
    response.headers["X-Original-Bytes"] = str(result.original_bytes)
    response.headers["X-Compressed-Bytes"] = str(result.compressed_bytes)
    response.headers["X-Met-Target"] = str(result.met_target)
    response.headers["X-Quality-Used"] = str(result.quality_used)
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
