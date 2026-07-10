#!/usr/bin/env python3
"""
service/parser.py — Convert PDF/DOCX to Markdown.

Uses (in priority order):
  1. Local parser server at http://localhost:4000 (from C:\parser\parser)
  2. Firecrawl API (requires FIRECRAWL_API_KEY env var or in C:\parser\parser\server\.env)
  3. Docling (pip install docling) — slow but self-contained

Usage as module:
  from service.parser import parse_pdf
  md = parse_pdf("path/to/doc.pdf")

Usage as CLI:
  python service/parser.py input.pdf
"""
import os, sys, io, json, re, urllib.request, urllib.error

PARSER_DIR = r"C:\parser\parser"
PARSER_URL = "http://localhost:4000"


def _get_api_key():
    """Get Firecrawl API key from env or parser .env file."""
    for path in [
        os.path.join(PARSER_DIR, "server", ".env"),
        os.path.join(PARSER_DIR, ".env"),
    ]:
        if os.path.exists(path):
            with io.open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("FIRECRAWL_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
    return os.environ.get("FIRECRAWL_API_KEY", "")


def _parser_running():
    """Check if local parser server is running."""
    try:
        urllib.request.urlopen(urllib.request.Request(PARSER_URL, method="HEAD"), timeout=1)
        return True
    except Exception:
        return False


def _upload_and_parse(filepath, api_url, api_key=None):
    """Upload a file to Firecrawl-compatible API and return markdown."""
    filename = os.path.basename(filepath)
    boundary = "----PyFormBoundary7MA4YWxk"

    with io.open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body += file_data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if api_key and "firecrawl.dev" in api_url:
        headers["Authorization"] = f"Bearer {api_key}"

    print(f"    [parser] Uploading {filename} ({len(file_data)//1024} KB) to {api_url}...")
    req = urllib.request.Request(api_url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read().decode("utf-8")
            # Try JSON
            try:
                result = json.loads(data)
                if isinstance(result, dict):
                    if result.get("success") and "data" in result:
                        return result["data"].get("markdown", "")
                    if "markdown" in result:
                        return result["markdown"]
                    # Check for v1/v2 different response shapes
                    if "data" in result and isinstance(result["data"], dict):
                        if "markdown" in result["data"]:
                            return result["data"]["markdown"]
                        return str(result["data"])
                return data  # plain markdown
            except json.JSONDecodeError:
                return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        print(f"    [parser] HTTP {e.code}: {body}")
        return None
    except Exception as e:
        print(f"    [parser] Error: {e}")
        return None


def parse_pdf(filepath):
    """
    Convert PDF to markdown. Returns markdown string or None.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".pdf", ".docx", ".doc", ".xlsx", ".xls"):
        print(f"    [parser] Unsupported format: {ext}")
        return None

    # 1. Try local parser server
    if _parser_running():
        print(f"    [parser] Local server found at {PARSER_URL}")
        api_url = f"{PARSER_URL}/api/parse"
        return _upload_and_parse(filepath, api_url)

    # 2. Try Firecrawl API
    api_key = _get_api_key()
    if api_key:
        print(f"    [parser] Using Firecrawl API")
        api_url = "https://api.firecrawl.dev/v2/parse"
        return _upload_and_parse(filepath, api_url, api_key=api_key)

    # 3. Try Docling (offline, no API key needed)
    try:
        from docling.document_converter import DocumentConverter
        print(f"    [parser] Using Docling (offline, may be slow)")
        converter = DocumentConverter()
        result = converter.convert(filepath)
        md = result.document.export_to_markdown()
        return md
    except ImportError:
        pass

    # 4. Give up
    print(f"    [parser] No parser available.")
    print(f"    Options:")
    print(f"      a) Start local server: cd {PARSER_DIR} && npm run dev")
    print(f"      b) Set FIRECRAWL_API_KEY in {PARSER_DIR}\\server\\.env")
    print(f"      c) pip install docling")
    return None


def ensure_markdown(pdf_path):
    """
    Ensure a .md file exists for the given PDF.
    Checks these locations in order:
      1. Same folder as PDF (input/документ.md)
      2. Parent folder (HTMLart/документ_struct.md)
      3. Parse the PDF using available parser
    Returns path to the .md file, or None.
    """
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    candidates = [
        os.path.splitext(pdf_path)[0] + ".md",
        os.path.join(os.path.dirname(pdf_path), basename + ".md"),
        os.path.join(os.path.dirname(os.path.dirname(pdf_path)), basename + "_struct.md"),
        os.path.join(os.path.dirname(os.path.dirname(pdf_path)), basename + ".md"),
    ]
    for cand in candidates:
        if os.path.exists(cand) and os.path.getsize(cand) > 100:
            print(f"    [parser] Found existing .md: {os.path.basename(cand)}")
            return cand

    # No .md found — try to parse
    md = parse_pdf(pdf_path)
    if md:
        md_path = os.path.splitext(pdf_path)[0] + ".md"
        md = re.sub(r"\bСП\s*\d+(?:\.\d+)*\s*\d{1,2}\b", "", md)
        md = re.sub(r"(?:^|\n)\d{1,3}(\n|$)", "\n", md)
        with io.open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"    [parser] Saved: {md_path} ({len(md)} chars)")
        return md_path
    return None


# ── CLI ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python service/parser.py document.pdf")
        sys.exit(1)

    path = sys.argv[1]
    result = ensure_markdown(path)
    if result:
        print(f"Done: {result}")
    else:
        print("Failed")
        sys.exit(1)
