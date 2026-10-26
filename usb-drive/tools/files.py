"""Operasi file. Di dalam data/ = MEDIUM, di luar data/ = HIGH (wajib konfirmasi)."""
import os
import shutil
import xml.sax.saxutils as sax
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from _paths import writable as _wr
    DATA = os.path.normpath(_wr("data"))
except ImportError:
    DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
MAX_READ = 4000


def resolve(path):
    """Return (abs_path, inside_data). Raise jika path kosong."""
    if not path:
        raise ValueError("path kosong")
    abs_p = os.path.abspath(os.path.join(DATA, path)
                            if not os.path.isabs(path) else path)
    inside = abs_p == DATA or abs_p.startswith(DATA + os.sep)
    return abs_p, inside


def _ensure_dir(d):
    """Siapkan folder; bila ditolak Windows, sertakan path penuh di pesan
    agar log diagnostik tidak menampilkan potongan path misterius."""
    try:
        os.makedirs(d, exist_ok=True)
    except OSError as e:
        raise OSError("tak bisa siapkan folder '%s': %s" % (d, e))


def read_file(path):
    abs_p, _ = resolve(path)
    if not os.path.isfile(abs_p):
        raise FileNotFoundError("tidak ada: %s" % path)
    with open(abs_p, encoding="utf-8", errors="replace") as f:
        return f.read(MAX_READ)


def create_file(path, content=""):
    abs_p, _ = resolve(path)
    _ensure_dir(os.path.dirname(abs_p) or DATA)
    with open(abs_p, "w", encoding="utf-8") as f:
        f.write(content or "")
    return "tersimpan (%d karakter)" % len(content or "")


def move_file(src, dst):
    a, _ = resolve(src)
    b, _ = resolve(dst)
    if not os.path.exists(a):
        raise FileNotFoundError("tidak ada: %s" % src)
    _ensure_dir(os.path.dirname(b) or DATA)
    shutil.move(a, b)
    return "dipindah ke %s" % dst


def delete_file(path):
    abs_p, _ = resolve(path)
    if not os.path.exists(abs_p):
        raise FileNotFoundError("tidak ada: %s" % path)
    if os.path.isdir(abs_p):
        raise ValueError("hapus folder ditolak di Fase 2")
    os.remove(abs_p)
    return "terhapus"


def create_docx(path, text="", size=None, bold=False):
    """Buat .docx minimal berisi teks. Stdlib saja (zipfile)."""
    abs_p, _ = resolve(path)
    if not abs_p.lower().endswith(".docx"):
        abs_p += ".docx"
    _ensure_dir(os.path.dirname(abs_p) or DATA)
    esc = sax.escape(text or "")
    try:
        sz = max(8, min(72, int(size or 0))) if size else 0
    except (TypeError, ValueError):
        sz = 0
    rpr = ""
    if sz:
        rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (sz * 2, sz * 2)
    if bold:
        rpr += "<w:b/><w:bCs/>"
    rpr = "<w:rPr>%s</w:rPr>" % rpr if rpr else ""
    doc = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body><w:p><w:r>' + rpr + '<w:t xml:space="preserve">' + esc +
           '</w:t></w:r></w:p></w:body></w:document>')
    ctype = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
             '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    with zipfile.ZipFile(abs_p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctype)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    return "tersimpan (%d karakter)" % len(text or "")


def list_dir(path=""):
    abs_p, _ = resolve(path or ".")
    if not os.path.isdir(abs_p):
        raise FileNotFoundError("bukan folder: %s" % path)
    names = sorted(os.listdir(abs_p))[:100]
    if not names:
        return "(kosong)"
    return "\n".join(("- " + n) for n in names)


def list_dir(path=""):
    abs_p, _ = resolve(path or ".")
    if not os.path.isdir(abs_p):
        raise FileNotFoundError("bukan folder: %s" % path)
    names = sorted(os.listdir(abs_p))[:100]
    if not names:
        return "(kosong)"
    return "\n".join(("- " + n) for n in names)


def _pdf_esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_pdf(path, text="", title=""):
    """Buat .pdf sederhana (teks, font Helvetica bawaan). Stdlib saja."""
    abs_p, _ = resolve(path)
    if not abs_p.lower().endswith(".pdf"):
        abs_p += ".pdf"
    _ensure_dir(os.path.dirname(abs_p) or DATA)
    lines = []
    for ln in (text or "").splitlines() or [""]:
        while len(ln) > 95:
            lines.append(ln[:95])
            ln = ln[95:]
        lines.append(ln)
    if title:
        lines = [title, ""] + lines
    pages = [lines[i:i + 45] for i in range(0, len(lines), 45)] or [[]]
    objs = []  # (nomor, bytes)
    objs.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    kids = " ".join("%d 0 R" % (4 + i * 2) for i in range(len(pages)))
    objs.append((2, ("<< /Type /Pages /Kids [%s] /Count %d >>"
                     % (kids, len(pages))).encode("latin-1")))
    font_no = 4 + len(pages) * 2
    for i, pg in enumerate(pages):
        content = ["BT /F1 11 Tf 50 792 Td 14 TL"]
        for ln in pg:
            content.append("(%s) Tj T*" % _pdf_esc(ln))
        content.append("ET")
        stream = "\n".join(content).encode("latin-1", errors="replace")
        page_no, cont_no = 4 + i * 2, 5 + i * 2
        objs.append((page_no,
                     ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                      "/Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>"
                      % (cont_no, font_no)).encode("latin-1")))
        objs.append((cont_no,
                     b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
    objs.append((font_no, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    out = [b"%PDF-1.4"]
    offsets = {}
    for no, body in sorted(objs):
        offsets[no] = sum(len(b) + 1 for b in out)
        out.append(b"%d 0 obj" % no)
        out.append(body)
        out.append(b"endobj")
    xref_pos = sum(len(b) + 1 for b in out)
    n = max(offsets) + 1
    out.append(b"xref")
    out.append(("0 %d" % n).encode("latin-1"))
    out.append(b"0000000000 65535 f ")
    for i in range(1, n):
        out.append(("%010d 00000 n " % offsets.get(i, 0)).encode("latin-1"))
    out.append(b"trailer")
    out.append(("<< /Size %d /Root 1 0 R >>" % n).encode("latin-1"))
    out.append(b"startxref")
    out.append(str(xref_pos).encode("latin-1"))
    out.append(b"%%EOF")
    with open(abs_p, "wb") as f:
        f.write(b"\n".join(out))
    return "tersimpan (%d baris)" % len(lines)


def _xml_esc(s):
    return sax.escape(s or "", {'"': "&quot;"})


def create_pptx(path, text=""):
    """Buat .pptx sederhana. Slide dipisah '# Judul'. Stdlib saja (zipfile)."""
    abs_p, _ = resolve(path)
    if not abs_p.lower().endswith(".pptx"):
        abs_p += ".pptx"
    _ensure_dir(os.path.dirname(abs_p) or DATA)
    slides, cur = [], []
    for ln in (text or "").splitlines():
        if ln.strip().startswith("# ") and cur:
            slides.append(cur)
            cur = []
            ln = ln.strip()[2:]
        if ln.strip():
            cur.append(ln.strip())
    if cur:
        slides.append(cur)
    if not slides:
        slides = [["Judul", "Isi presentasi"]]
    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    rels_ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    p_ns = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    ctype = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
             '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
             '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
             '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>' +
             "".join('<Override PartName="/ppt/slides/slide%d.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                     % (i + 1) for i in range(len(slides))) + '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships %s><Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="ppt/presentation.xml"/></Relationships>' % rels_ns)
    sld_ids = "".join('<p:sldId id="%d" r:id="rId%d"/>' % (256 + i, i + 2)
                      for i in range(len(slides)))
    pres = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<p:presentation %s xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<p:sldMasterIdLst><p:sldMasterId r:id="rId1"/></p:sldMasterIdLst>'
            '<p:sldIdLst>%s</p:sldIdLst><p:sldSz cx="9144000" cy="5143500"/></p:presentation>'
            % (p_ns, sld_ids))
    pres_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<Relationships %s><Relationship Id="rId1" '
                 'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
                 'Target="slideMasters/slideMaster1.xml"/>' +
                 "".join('<Relationship Id="rId%d" '
                         'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                         'Target="slides/slide%d.xml"/>' % (i + 2, i + 1)
                         for i in range(len(slides))) + '</Relationships>' % rels_ns)
    master = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<p:sldMaster %s><p:cSld><p:bg><p:bgPr><a:solidFill>'
              '<a:srgbClr val="FFFFFF"/></a:solidFill></p:bgPr></p:bg>'
              '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
              '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
              '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
              'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
              'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
              '<p:sldLayoutIdLst><p:sldLayoutId r:id="rId1"/></p:sldLayoutIdLst>'
              '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="4400" b="1"/>'
              '</a:lvl1pPr></p:titleStyle><p:bodyStyle><a:lvl1pPr>'
              '<a:defRPr sz="3200"/></a:lvl1pPr></p:bodyStyle>'
              '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr>'
              '</p:otherStyle></p:txStyles></p:sldMaster>' % p_ns)
    master_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships %s><Relationship Id="rId1" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
                   'Target="../slideLayouts/slideLayout1.xml"/>'
                   '<Relationship Id="rId2" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
                   'Target="../theme/theme1.xml"/></Relationships>' % rels_ns)
    layout = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<p:sldLayout %s preserve="1"><p:cSld name="Title and Content">'
              '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
              '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree>'
              '</p:cSld><p:clrMapOvr><a:masterClrMap/></p:clrMapOvr></p:sldLayout>' % p_ns)
    layout_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships %s><Relationship Id="rId1" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
                   'Target="../slideMasters/slideMaster1.xml"/></Relationships>' % rels_ns)
    theme = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<a:theme %s name="JURU"><a:themeElements><a:clrScheme name="JURU">'
             '<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
             '<a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="E5E7EB"/></a:lt2>'
             '<a:accent1><a:srgbClr val="4F7CFF"/></a:accent1><a:accent2><a:srgbClr val="10B981"/></a:accent2>'
             '<a:accent3><a:srgbClr val="F59E0B"/></a:accent3><a:accent4><a:srgbClr val="EF4444"/></a:accent4>'
             '<a:accent5><a:srgbClr val="8B5CF6"/></a:accent5><a:accent6><a:srgbClr val="06B6D4"/></a:accent6>'
             '<a:hlink><a:srgbClr val="4F7CFF"/></a:hlink><a:folHlink><a:srgbClr val="6B7280"/></a:folHlink>'
             '</a:clrScheme><a:fmtScheme name="JURU"><a:fillStyleLst>'
             '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
             '<a:lnStyleLst><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
             '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
             '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
             '</a:fmtScheme></a:themeElements></a:theme>' % ns)

    def shape(idx, text, title):
        sz = "4400" if title else "2800"
        b = " b=\"1\"" if title else ""
        y = "0" if title else "1200000"
        h = "1200000" if title else "3800000"
        return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="t%d"/>'
                '<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>'
                '<a:xfrm><a:off x="600000" y="%s"/><a:ext cx="7900000" cy="%s"/>'
                '</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
                '<p:txBody><a:bodyPr/><a:p><a:r><a:rPr sz="%s"%s/>'
                '<a:t xml:space="preserve">%s</a:t></a:r></a:p></p:txBody></p:sp>'
                % (idx, idx, y, h, sz, b, _xml_esc(text)))

    with zipfile.ZipFile(abs_p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctype)
        z.writestr("_rels/.rels", rels)
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        z.writestr("ppt/theme/theme1.xml", theme)
        for i, sl in enumerate(slides):
            title = sl[0] if sl else "Slide %d" % (i + 1)
            bullets = "\n".join("\u2022 " + b for b in sl[1:])
            body = ('<p:sld %s><p:cSld><p:spTree>'
                    '<p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
                    '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
                    '%s%s</p:spTree></p:cSld>'
                    '<p:clrMapOvr><a:masterClrMap/></p:clrMapOvr></p:sld>'
                    % (p_ns, shape(2, title, True), shape(3, bullets, False)))
            z.writestr("ppt/slides/slide%d.xml" % (i + 1), body)
            z.writestr("ppt/slides/_rels/slide%d.xml.rels" % (i + 1),
                       '<?xml version="1.0" encoding="UTF-8"?>'
                       '<Relationships %s><Relationship Id="rId1" '
                       'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
                       'Target="../slideLayouts/slideLayout1.xml"/></Relationships>' % rels_ns)
    return "tersimpan (%d slide)" % len(slides)


def make_dir(path):
    abs_p, _ = resolve(path)
    _ensure_dir(abs_p)
    return "folder siap"


def rename_file(src, dst):
    a, _ = resolve(src)
    b, _ = resolve(dst)
    if not os.path.exists(a):
        raise FileNotFoundError("tidak ada: %s" % src)
    os.rename(a, b)
    return "jadi %s" % dst


def create_xlsx(path, rows=""):
    """Buat .xlsx minimal. rows: teks baris dipisah baris baru, kolom dipisah ; atau ,."""
    abs_p, _ = resolve(path)
    if not abs_p.lower().endswith(".xlsx"):
        abs_p += ".xlsx"
    _ensure_dir(os.path.dirname(abs_p) or DATA)
    lines = [l for l in (rows or "").splitlines() if l.strip()]
    if not lines:
        lines = ["A;B", "1;2"]
    grid = []
    for l in lines:
        sep = ";" if ";" in l else ","
        grid.append([c.strip() for c in l.split(sep)][:10])
    grid = grid[:50]

    def cell(r, c, v):
        col = ""
        c += 1
        while c:
            c, m = divmod(c - 1, 26)
            col = chr(65 + m) + col
        return '<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>' % (
            col, r + 1, sax.escape(v))

    cells = "".join(
        "<row r=\"%d\">%s</row>" % (r + 1, "".join(cell(r, c, v) for c, v in enumerate(row)))
        for r, row in enumerate(grid))
    sheet = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData>' + cells + '</sheetData></worksheet>')
    wb = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    wbrels = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              '</Relationships>')
    ctype = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
             '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
             '</Types>')
    with zipfile.ZipFile(abs_p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctype)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return "tersimpan (%d baris)" % len(grid)
