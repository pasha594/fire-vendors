"""Download vendor logos into logos/ for the rows of config/vendor_logos.csv that have a domain and no logo yet.

config/vendor_logos.csv: vendor_id (the vendor's id on the site), vendor (its name, for reading), domain (its
website, curated by hand), confidence (of the domain: high or medium), logo (the file in logos/), logo_px (its
size in pixels, the smaller side) and logo_source (the URL it was downloaded from), written here, and notes. A logo
of "-" means the downloaded icon was checked by hand and is not usable (a web host's default icon, or a white icon
that does not show on the page's white tiles); such rows are left alone unless named with --only.

For each domain, every image of: the icons the home page links (apple-touch-icon, icons with sizes, the web app
manifest's icons and the Windows tile image), /apple-touch-icon.png, Google's favicon service
(https://www.google.com/s2/favicons?domain=<domain>&sz=128) and /favicon.ico. The page shows logos at 18 to 44
pixels, so the smallest image of at least 64 pixels and at most 40 kB is kept; else the largest of at least 16
pixels (many sites publish only a 16 or 32 pixel favicon). A site whose icon is its web host's default (Wix,
Squarespace, WordPress) gets no logo: Google's service and /favicon.ico would return the same default. Only PNG, ICO, JPEG, GIF and WebP files under 200 kB are kept (no SVG: a
file served from the site's own origin must not be able to run script). Files are named logos/<vendor_id>.<ext>.

Standard library only. Rows that already have a logo are left alone (--force downloads them again; --only
ID,ID limits the run to those vendor ids).

    python3 pipeline/fetch_logos.py [--force] [--only ID,ID]
"""

import concurrent.futures
import csv
import html.parser
import json
import pathlib
import re
import struct
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV = ROOT / "config" / "vendor_logos.csv"
LOGOS = ROOT / "logos"
FIELDS = ["vendor_id", "vendor", "domain", "confidence", "logo", "logo_px", "logo_source", "notes"]
MAX_BYTES = 200_000
GOOD = 64                                                     # pixels: the smallest image this large is kept
SMALL = 40_000                                                # bytes: ... if it is no larger than this
PLATFORM_DEFAULT = re.compile(r"static\.parastorage\.com/client/pfavico\.ico|assets\.squarespace\.com/universal/default-favicon"
                              r"|/wp-includes/images/w-logo|s\.w\.org/favicon", re.I)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def get(url, limit=MAX_BYTES, timeout=12):
    """(final url, content type, body) or None. Bodies over limit are dropped."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(limit + 1)
            if len(body) > limit:
                return None
            return r.geturl(), (r.headers.get("Content-Type") or "").split(";")[0].strip().lower(), body
    except Exception:
        return None


def image_info(b):
    """(extension, width, height) of a raster image, or None."""
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24:
        w, h = struct.unpack(">II", b[16:24])
        return "png", w, h
    if b[:4] == b"\x00\x00\x01\x00" and len(b) >= 6:              # ICO: the largest image in the directory
        n = struct.unpack("<H", b[4:6])[0]
        best = 0
        for i in range(min(n, 32)):
            e = b[6 + 16 * i: 6 + 16 * (i + 1)]
            if len(e) < 16:
                break
            best = max(best, e[0] or 256, e[1] or 256)
        return ("ico", best, best) if best else None
    if b[:3] == b"\xff\xd8\xff":                                  # JPEG: the first frame header
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            m = b[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return "jpg", w, h
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
        return None
    if b[:6] in (b"GIF87a", b"GIF89a") and len(b) >= 10:
        w, h = struct.unpack("<HH", b[6:10])
        return "gif", w, h
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP" and len(b) >= 30:
        if b[12:16] == b"VP8X":
            w = 1 + int.from_bytes(b[24:27], "little")
            h = 1 + int.from_bytes(b[27:30], "little")
            return "webp", w, h
        return "webp", 64, 64                                      # simple formats: size not read, accept
    return None


class Icons(html.parser.HTMLParser):
    """Icon links of a page: [(declared size, url)], and its web app manifest's url."""

    def __init__(self, base):
        super().__init__()
        self.base, self.found, self.manifest = base, [], None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("name", "").lower() == "msapplication-tileimage" and a.get("content", "").strip():
            self.found.append((144, urllib.parse.urljoin(self.base, a["content"].strip())))
            return
        if tag != "link":
            return
        rel = a.get("rel", "").lower().split()
        href = a.get("href", "").strip()
        if "manifest" in rel and href:
            self.manifest = urllib.parse.urljoin(self.base, href)
            return
        if not href or href.startswith("data:") or not ({"icon", "apple-touch-icon", "apple-touch-icon-precomposed"} & set(rel)):
            return
        if href.lower().split("?")[0].endswith(".svg") or "svg" in a.get("type", ""):
            return
        sizes = [int(x) for x in re.findall(r"(\d+)x\d+", a.get("sizes", ""))]
        size = max(sizes) if sizes else (180 if any(r.startswith("apple-touch-icon") for r in rel) else 0)
        self.found.append((size, urllib.parse.urljoin(self.base, href)))


def candidates(domain):
    """Icon URLs to try, or None when the site's own icon is its web host's default."""
    page = get("https://" + domain + "/", limit=2_000_000) or get("https://www." + domain + "/", limit=2_000_000) \
        or get("http://" + domain + "/", limit=2_000_000)
    out = []
    base = "https://" + domain + "/"
    if page and page[1].startswith("text/html"):
        base = page[0]
        p = Icons(base)
        try:
            p.feed(page[2].decode("utf-8", "replace"))
        except Exception:
            pass
        found = list(p.found)
        m = get(p.manifest, limit=200_000) if p.manifest else None
        if m:
            try:
                for ic in json.loads(m[2].decode("utf-8", "replace")).get("icons", []):
                    src = str(ic.get("src", ""))
                    if src and not src.lower().split("?")[0].endswith(".svg") and "svg" not in str(ic.get("type", "")):
                        sizes = [int(x) for x in re.findall(r"(\d+)x\d+", str(ic.get("sizes", "")))]
                        found.append((max(sizes) if sizes else 0, urllib.parse.urljoin(m[0], src)))
            except (ValueError, AttributeError):
                pass
        out += [u for _, u in sorted(found, key=lambda x: -x[0])]
        if out and all(PLATFORM_DEFAULT.search(u) for u in out):
            return None
    root = urllib.parse.urlsplit(base)
    origin = root.scheme + "://" + root.netloc
    out += [origin + "/apple-touch-icon.png", "https://www.google.com/s2/favicons?domain=" + domain + "&sz=128", origin + "/favicon.ico"]
    seen, uniq = set(), []
    for u in out:
        if u not in seen and urllib.parse.urlsplit(u).scheme in ("http", "https"):
            seen.add(u)
            uniq.append(u)
    return uniq


def fetch_logo(domain):
    """(extension, body, source url, pixels) or None."""
    urls = candidates(domain)
    if urls is None:
        return None
    found = []
    for u in urls:
        if PLATFORM_DEFAULT.search(u):
            continue
        r = get(u)
        info = image_info(r[2]) if r else None
        if info and min(info[1], info[2]) >= 16:
            found.append((info[0], r[2], u, min(info[1], info[2])))
    good = [f for f in found if f[3] >= GOOD and len(f[1]) <= SMALL]
    if good:
        return min(good, key=lambda f: (f[3], len(f[1])))
    return max(found, key=lambda f: (f[3], -len(f[1]))) if found else None


def main(argv):
    force = "--force" in argv
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        if i + 1 >= len(argv):
            sys.exit("usage: fetch_logos.py [--force] [--only ID,ID]")
        only = set(argv[i + 1].split(","))
    with open(CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in FIELDS:
            r.setdefault(k, "")
    todo = [r for r in rows if r["domain"].strip() and (only is None or r["vendor_id"] in only)
            and (only is not None or (r["logo"] != "-" and (force or not r["logo"])))]
    LOGOS.mkdir(exist_ok=True)
    print(f"{len(todo)} logos to fetch")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = dict(zip((r["vendor_id"] for r in todo), ex.map(lambda r: fetch_logo(r["domain"].strip()), todo)))
    got = 0
    for r in todo:
        res = results[r["vendor_id"]]
        if not res:
            print(f"  no logo: {r['vendor_id']} ({r['domain']})")
            if r["logo"]:
                print(f"    {r['logo']} is no longer used")
            r["logo"] = r["logo_px"] = r["logo_source"] = ""
            continue
        ext, body, src, px = res
        for old in LOGOS.glob(r["vendor_id"] + ".*"):
            old.unlink()
        path = LOGOS / f"{r['vendor_id']}.{ext}"
        path.write_bytes(body)
        r["logo"], r["logo_px"], r["logo_source"] = f"logos/{path.name}", str(px), src
        got += 1
        if px < GOOD:
            print(f"  small ({px}px): {r['vendor_id']} from {src}")
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in FIELDS})
    print(f"{got} of {len(todo)} logos saved in logos/; config/vendor_logos.csv updated")


if __name__ == "__main__":
    main(sys.argv[1:])
