from io import BytesIO
import base64
from typing import Dict, Any, List
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter

def _data_url_to_png_bytes(data_url: str) -> bytes:
    if not data_url: return b""
    header, b64data = data_url.split(",", 1)
    return base64.b64decode(b64data)

def _make_overlay(page_w, page_h, fields_for_page: List[Dict[str, Any]], values: Dict[str, Any], sig_png: bytes) -> bytes:
    buf = BytesIO(); c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    for f in fields_for_page:
        t=f.get("type")
        if t in ("text","date"):
            name=f["name"]; x=f["x"]; y=f["y"]; size=f.get("font_size",12)
            c.setFont("Helvetica", size); c.drawString(x, y, str(values.get(name,"")))
        elif t=="signature" and sig_png:
            x=f["x"]; y=f["y"]; w=f.get("w",220); h=f.get("h",60)
            c.drawImage(ImageReader(BytesIO(sig_png)), x, y, width=w, height=h, mask='auto')
    c.save(); return buf.getvalue()

def burn_fields_and_signature(base_pdf_bytes: bytes, fields_config: Dict[str, Any], values: Dict[str, Any], signature_data_url: str) -> bytes:
    reader = PdfReader(BytesIO(base_pdf_bytes)); writer = PdfWriter()
    sig_png=_data_url_to_png_bytes(signature_data_url); fields=fields_config.get("fields",[])
    for i,page in enumerate(reader.pages):
        page_w=float(page.mediabox.width); page_h=float(page.mediabox.height)
        fpage=[f for f in fields if f.get("page",0)==i]
        if fpage:
            overlay_pdf = _make_overlay(page_w, page_h, fpage, values, sig_png)
            from PyPDF2 import PdfReader as _R; overlay_page=_R(BytesIO(overlay_pdf)).pages[0]
            page.merge_page(overlay_page)
        writer.add_page(page)
    out=BytesIO(); writer.write(out); return out.getvalue()
