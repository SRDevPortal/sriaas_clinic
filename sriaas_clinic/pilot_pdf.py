"""Opt-in development renderer. Never selected by default or installed on a format."""
import hashlib
import io
import re
from pathlib import Path
from bs4 import BeautifulSoup
import frappe

GENERATOR = "clinic_privacy_pilot"
FORMATS = {"Kit Billing Invoice": "Sales Invoice", "Patient Encounter New": "Patient Encounter"}


def require_access(print_format):
    if (frappe.local.site != "privacy-pilot.local"
        or not frappe.conf.get("privacy_shield_desk_enabled")
        or not frappe.conf.get("clinic_pdf_pilot_enabled")):
        raise frappe.PermissionError("Clinic PDF renderer is disabled outside the opted-in pilot")
    if print_format not in FORMATS:
        raise frappe.PermissionError("Print format is outside the renderer pilot")
    from privacy_shield.import_access import restricted
    if restricted():
        raise frappe.PermissionError("Full-detail formats are not approved for restricted viewers")
    form = frappe.local.form_dict
    if form.get("doctype") != FORMATS[print_format] or not form.get("name") or form.get("doc"):
        raise frappe.PermissionError("Pilot printing requires a saved document reference")
    doc = frappe.get_doc(form.doctype, form.name)
    doc.check_permission("read")
    doc.check_permission("print")


def compatible_html(html, print_format):
    soup = BeautifulSoup(html, "html.parser")
    if print_format == "Kit Billing Invoice":
        expected = {"--sr-color": "#222222", "--sr-mutecolor": "#666666",
                    "--sr-lbl-bg-color": "#eeeeee", "--sr-border": "#b1b1b1"}
        found = {}
        for style in soup.find_all("style"):
            found.update(re.findall(r"(--sr-[a-z-]+)\s*:\s*(#[a-fA-F0-9]+)\s*;", style.get_text()))
        if any(found.get(k) != v for k, v in expected.items()):
            raise ValueError("Invoice stylesheet differs from the reviewed pilot")
        for style in soup.find_all("style"):
            def fallback(match):
                prop, value = match.groups()
                if 'var(--sr-' not in value:
                    return match.group(0)
                literal = re.sub(r"var\((--sr-[a-z-]+)\)", lambda m: expected[m.group(1)], value)
                return prop + ':' + literal + ';' + prop + ':' + value + ';'
            style.string = re.sub(r"([a-z-]+)\s*:\s*([^{};]+);", fallback, style.get_text())
        css = '@media print {.si-wrap {line-height:1.3;} }'
    elif print_format == "Patient Encounter New":
        for table in soup.select('.rx-table'):
            parent = table.find_parent(class_='section-block')
            if parent is None:
                raise ValueError("Prescription structure differs from the reviewed pilot")
            parent['class'] = parent.get('class', []) + ['candidate-rx-page']
        css = ('@media print {.candidate-rx-page {page-break-before:always;} '
               '.rx-table th,.rx-table td {padding:5px 8px;line-height:1.3;} '
               '.rx-instruction td {padding:4px 8px;} }')
    else:
        raise ValueError("Unsupported pilot format")
    style = soup.new_tag('style')
    style.string = css
    (soup.head or soup).append(style)
    return str(soup)


def inline_print_styles(html):
    """Inline bench-local styles/fonts; never fetch external assets for the pilot."""
    import base64
    import mimetypes
    from urllib.parse import urljoin, urlsplit
    soup = BeautifulSoup(html, 'html.parser')
    bench = Path(frappe.get_app_path('frappe')).resolve().parents[2]
    def asset(url):
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path.startswith('/assets/'):
            raise ValueError('Only local bench print assets are supported by this pilot')
        path = (bench / 'sites' / parts.path.lstrip('/')).resolve()
        if not path.is_relative_to(bench) or not path.is_file() or path.stat().st_size > 10000000:
            raise ValueError('Invalid pilot print asset')
        if path.suffix.lower() not in {'.css', '.woff', '.woff2', '.ttf', '.png', '.jpg', '.svg'}:
            raise ValueError('Unsupported pilot asset type')
        return path
    for link in soup.find_all('link'):
        if 'stylesheet' not in link.get('rel', []):
            continue
        href = link.get('href', '')
        css = asset(href).read_text()
        if '@import' in css:
            raise ValueError('Imported stylesheets need pilot review')
        def embed(match):
            url = match.group(1).strip(' \"\'')
            if url.startswith('data:'):
                return match.group(0)
            path = asset(urljoin(href, url))
            mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
            return 'url("data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()+'")'
        css = re.sub(r'url\(([^)]+)\)', embed, css)
        style = soup.new_tag('style');style.string = css;link.replace_with(style)
    return str(soup)


def renderer_path():
    path = Path(frappe.conf.get('clinic_pdf_pilot_binary') or '')
    expected = frappe.conf.get('clinic_pdf_pilot_sha256')
    if not path.is_absolute() or not path.is_file() or not expected:
        raise ValueError("An absolute renderer path and SHA-256 pin are required")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Pilot renderer checksum does not match")
    return str(path)


def generate(print_format, html, options=None, output=None, pdf_generator=None):
    if pdf_generator != GENERATOR:
        return None
    require_access(print_format)
    binary = renderer_path()
    allowed = {'page-size', 'orientation', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right'}
    if set(options or {}) - allowed:
        raise ValueError("PDF options are outside the reviewed pilot")
    import pdfkit
    from pypdf import PdfReader
    from frappe.utils.pdf import prepare_options, cleanup
    prepared = {}
    try:
        body, prepared = prepare_options(inline_print_styles(compatible_html(html, print_format)), dict(options or {}))
        prepared.update({'disable-javascript': '', 'disable-local-file-access': '', 'disable-smart-shrinking': ''})
        data = pdfkit.from_string(body, options=prepared, configuration=pdfkit.configuration(wkhtmltopdf=binary))
        reader = PdfReader(io.BytesIO(data))
        if output is not None:
            output.append_pages_from_reader(reader)
            return output
        return data
    finally:
        cleanup(prepared)
