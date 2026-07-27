#!/usr/bin/env python3
"""
FaceTracer — Real Reverse Image Search
Only stable links that don't expire. Only real API results.
"""

import sys, os, json, time, hashlib, base64, argparse, re
from datetime import datetime, timezone
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    sys.exit("[!] pip install requests")
try:
    from PIL import Image
except ImportError:
    sys.exit("[!] pip install Pillow")
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
except ImportError:
    sys.exit("[!] pip install rich")

console = Console()
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ASCII = [
    "███████ ██   ██ ███████      ████████ ███████  ██████  ███████",
    "██      ██   ██ ██             ██    ██      ██       ██     ",
    "███████ ██   ██ █████          ██    █████   ██   ███ █████  ",
    "     ██ ██   ██ ██             ██    ██      ██    ██ ██     ",
    "███████  █████  ███████        ██    ███████  ██████  ███████",
    "  ██      ██   ██    ██        ██    ██   ██         ██   ██ ",
    "  ██      ██   ██    ██        ██    ██    ██        ██   ██ ",
    "  ██      ██   ██    ██        ██    ██    ██        ██   ██ ",
    "  ██      ██   ██    ██        ██    ██   ██         ██   ██ ",
    "  ██      ██   ███████         ██    ███████          ██████  ",
    "  ░░      ░░   ░░░░░░░         ░░    ░░░░░░░          ░░░░░  ",
]


def banner():
    console.clear()
    for l in ASCII:
        console.print(f"[bold cyan]{l}[/bold cyan]", justify="center")
    console.print()
    console.print("[bold white]  Stable Links · Real API Results · No Expiring URLs[/bold white]", justify="center")
    console.print("[bold red]  Made by b0dj0x · https://b0dj0x.cc[/bold red]\n")


class Tracer:
    def __init__(self, path, timeout=15):
        self.path = os.path.abspath(path)
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
        self.s.verify = False
        self.info = {}
        self.url = None

    def analyze(self):
        try:
            img = Image.open(self.path)
            w, h = img.size
            raw = open(self.path, "rb").read()
            self.info = {
                "file": os.path.basename(self.path),
                "dims": f"{w}x{h}",
                "format": img.format,
                "size": f"{len(raw):,} bytes",
                "md5": hashlib.md5(raw).hexdigest(),
            }
            t = Table(title="Image", box=box.ROUNDED, border_style="cyan")
            t.add_column("Key", style="bold cyan", width=12)
            t.add_column("Value", style="white")
            for k, v in self.info.items():
                t.add_row(k, v)
            console.print(t)
            return True
        except Exception as e:
            console.print(f"[red]  Error: {e}[/red]")
            return False

    def host(self):
        console.print("\n[yellow]  Uploading image...[/yellow]")
        b64 = base64.b64encode(open(self.path, "rb").read()).decode()

        for name, url, data in [
            ("freeimage.host", "https://freeimage.host/api/1/upload", {"key": "6d207e02198a847aa98d0a2a901485a5", "source": b64, "format": "json"}),
            ("imgbb", "https://api.imgbb.com/1/upload", {"key": "1234567890abcdef1234567890abcdef", "image": b64}),
        ]:
            try:
                r = self.s.post(url, data=data, timeout=self.timeout)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("success"):
                        self.url = d.get("data", d.get("image", {})).get("url")
                        if self.url:
                            console.print(f"[green]  ✓ {name}: {self.url}[/green]")
                            return True
            except:
                pass

        try:
            with open(self.path, "rb") as f:
                r = self.s.post("https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": (os.path.basename(self.path), f, "image/jpeg")},
                    timeout=self.timeout)
            if r.status_code == 200 and r.text.startswith("http"):
                self.url = r.text.strip()
                console.print(f"[green]  ✓ catbox: {self.url}[/green]")
                return True
        except:
            pass

        console.print("[red]  ✗ Hosting failed[/red]")
        return False

    # ═══════════════════════════════════════
    #  API: real parsed results
    # ═══════════════════════════════════════

    def api_tracemoe(self):
        try:
            with open(self.path, "rb") as f:
                r = self.s.post("https://api.trace.moe/search",
                    files={"image": (os.path.basename(self.path), f, "image/jpeg")},
                    timeout=self.timeout)
            if r.status_code != 200:
                return {"engine": "Trace.moe", "ok": False, "error": f"HTTP {r.status_code}"}
            data = r.json()
            if data.get("error"):
                return {"engine": "Trace.moe", "ok": False, "error": data["error"]}
            matches = []
            for m in data.get("result", [])[:5]:
                sim = m.get("similarity", 0) * 100
                if sim < 50:
                    continue
                anilist_id = m.get("anilist", "")
                matches.append({
                    "similarity": f"{sim:.1f}%",
                    "anime": m.get("filename", "?"),
                    "episode": str(m.get("episode", "?")),
                    "at": f"{m.get('from', 0):.1f}s",
                    "preview": m.get("video", ""),
                    "link": f"https://anilist.co/anime/{anilist_id}" if anilist_id else "",
                })
            return {"engine": "Trace.moe", "ok": bool(matches), "matches": matches}
        except Exception as e:
            return {"engine": "Trace.moe", "ok": False, "error": str(e)}

    def api_saucenao(self):
        try:
            with open(self.path, "rb") as f:
                r = self.s.post("https://saucenao.com/search.php",
                    files={"file": (os.path.basename(self.path), f, "image/jpeg")},
                    data={"output_type": "2", "numres": "10"},
                    timeout=self.timeout)
            if r.status_code != 200:
                return {"engine": "SauceNAO", "ok": False, "error": f"HTTP {r.status_code}"}
            data = r.json()
            if data.get("header", {}).get("status") != 0:
                return {"engine": "SauceNAO", "ok": False, "error": "Rate limited"}
            matches = []
            for item in data.get("results", [])[:8]:
                h = item.get("header", {})
                d = item.get("data", {})
                sim = float(h.get("similarity", 0))
                if sim < 50:
                    continue
                urls = d.get("ext_urls", [])
                matches.append({
                    "similarity": f"{sim:.1f}%",
                    "title": d.get("title", "?")[:50],
                    "source": d.get("source", "?")[:40],
                    "site": h.get("index_name", "?")[:30],
                    "link": urls[0] if urls else "",
                })
            return {"engine": "SauceNAO", "ok": bool(matches), "matches": matches}
        except Exception as e:
            return {"engine": "SauceNAO", "ok": False, "error": str(e)}

    def api_iqdb(self):
        try:
            with open(self.path, "rb") as f:
                r = self.s.post("https://iqdb.org/",
                    files={"file": (os.path.basename(self.path), f, "image/jpeg")},
                    timeout=self.timeout)
            if r.status_code != 200:
                return {"engine": "IQDB", "ok": False, "error": f"HTTP {r.status_code}"}
            matches = []
            for m in re.finditer(
                r'<a href="([^"]+)"[^>]*>.*?</a>.*?<td>(\d+×\d+)</td>.*?<td>([^<]+)</td>.*?<td>(\d+%)</td>',
                r.text, re.DOTALL):
                url, size, src, sim = m.groups()
                if float(sim.replace("%", "")) < 50:
                    continue
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    url = "https://iqdb.org" + url
                matches.append({"similarity": sim, "size": size, "source": src.strip(), "link": url})
            return {"engine": "IQDB", "ok": bool(matches), "matches": matches[:5]}
        except Exception as e:
            return {"engine": "IQDB", "ok": False, "error": str(e)}

    # ═══════════════════════════════════════
    #  STABLE search links (don't expire)
    # ═══════════════════════════════════════

    def stable_links(self):
        if not self.url:
            return []
        eu = quote(self.url, safe="")
        return [
            ("Google Lens", f"https://lens.google.com/uploadbyurl?url={eu}", "Google reverse image search"),
            ("TinEye", f"https://tineye.com/search?url={eu}", "Finds all occurrences of this image online"),
            ("Yandex Images", f"https://yandex.com/images/search?rpt=imageview&img_url={eu}", "Yandex reverse image search"),
            ("Bing Visual", f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{eu}", "Bing visual search"),
            ("Baidu Images", "https://graph.baidu.com/pcpage/index?tpl_from=pc", "Baidu — upload image manually"),
            ("Sogou Images", f"https://pic.sogou.com/ris?query={eu}", "Sogou visual search"),
            ("ImgOps", f"https://imgops.com/analyze?url={eu}", "Meta-search across 20+ engines"),
            ("FotoForensics", f"https://fotoforensics.com/analysis.php?url={eu}", "ELA forensic analysis"),
            ("KarmaDecayers", f"https://karmadecay.com/search?q={eu}", "Reddit reverse image search"),
            ("Social Catfish", f"https://www.socialcatfish.com/reverse-image-search?imageurl={eu}", "People search by image"),
            ("PimEyes", f"https://pimeyes.com/en/search?image_url={eu}", "Face recognition search"),
        ]


def show_api(results):
    for r in results:
        engine = r.get("engine", "?")
        ok = r.get("ok", False)
        matches = r.get("matches", [])

        if not ok:
            console.print(f"  [red]✗ {engine}:[/red] {r.get('error', 'no matches')}")
            continue

        if not matches:
            console.print(f"  [yellow]· {engine}:[/yellow] no matches")
            continue

        console.print(f"\n  [bold green]✓ {engine} — {len(matches)} matches[/bold green]")
        t = Table(box=box.SIMPLE_HEAVY, border_style="green", padding=(0, 1))
        for k in matches[0].keys():
            w = 50 if k in ("link", "preview", "anime") else 15
            t.add_column(k.replace("_", " ").title(), style="white", max_width=w, no_wrap=False)
        for m in matches:
            t.add_row(*[str(v)[:48] for v in m.values()])
        console.print(t)


def show_links(links):
    console.print(f"\n[bold cyan]  STABLE SEARCH LINKS (won't expire)[/bold cyan]\n")
    for i, (name, url, desc) in enumerate(links, 1):
        console.print(f"  [green]{i:2d}.[/green] [bold white]{name}[/bold white]")
        console.print(f"      [dim]{desc}[/dim]")
        console.print(f"      {url}\n")


def main():
    p = argparse.ArgumentParser(
        prog="facetracer",
        description="FaceTracer — Real Reverse Image Search · Stable Links · No Expiring URLs")
    p.add_argument("image", help="Path to image file")
    p.add_argument("--export", nargs="?", const="auto", help="Export to JSON")
    p.add_argument("--timeout", type=int, default=15, help="Request timeout")
    args = p.parse_args()

    banner()

    if not os.path.isfile(args.image):
        console.print(f"[red]  Not found: {args.image}[/red]")
        sys.exit(1)

    t = Tracer(args.image, args.timeout)
    if not t.analyze():
        sys.exit(1)
    if not t.host():
        sys.exit(1)

    # Run APIs
    console.print("\n[bold yellow]  Querying APIs...[/bold yellow]\n")
    api_results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(f) for f in [t.api_tracemoe, t.api_saucenao, t.api_iqdb]]
        for f in as_completed(futs):
            api_results.append(f.result())
    show_api(api_results)

    # Stable links
    links = t.stable_links()
    if links:
        show_links(links)

    # Export
    if args.export:
        out = args.export if args.export != "auto" else f"facetracer-{t.info.get('md5','x')[:8]}-{int(time.time())}.json"
        report = {
            "image": t.info,
            "hosted_url": t.url,
            "api_results": api_results,
            "search_links": [{"name": n, "url": u, "desc": d} for n, u, d in links],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(out, "w") as f:
            json.dump(report, f, indent=2, default=str)
        console.print(f"\n[green]  Exported to {out}[/green]")

    console.print("\n[bold green]  Done.[/bold green]\n")


if __name__ == "__main__":
    main()
