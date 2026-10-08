"""Render a post from posts.json to out/<id>.jpg (1080x1350) with the Nuvo 'La clave' brand.

Usage: python render.py p001 [p002 ...]   |   python render.py --all
Photos come from Pexels (photo_id). Set PHOTO_DIR to use local files named <photo_id>.jpg instead.
"""
import asyncio, base64, html, json, math, os, sys, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
POSTS = {p["id"]: p for p in json.loads((HERE / "posts.json").read_text())["posts"]}
LOGO = json.loads((HERE / "logo.json").read_text())
FONT = "data:font/woff2;base64," + base64.b64encode((HERE / "bricolage.woff2").read_bytes()).decode()
TEJA, CARBON, CAL, STONE, KEY, PEACH = "#b9441f", "#1a1716", "#fbfaf8", "#efe9e1", "#c84f2a", "#f0a184"
esc = html.escape


def keystone_path():
    R_out, r_in, a_out, x_in = 51.5, 40.5, 10.5, 5.2
    ox = R_out * math.sin(math.radians(a_out)); oy = 50 - R_out * math.cos(math.radians(a_out))
    a_in = math.degrees(math.asin(x_in / r_in)); iy = 50 - r_in * math.cos(math.radians(a_in))
    return (f"M{50 + x_in:.3f} {iy:.3f} L{50 + ox:.3f} {oy:.3f} A{R_out} {R_out} 0 0 0 {50 - ox:.3f} {oy:.3f} "
            f"L{50 - x_in:.3f} {iy:.3f} A{r_in} {r_in} 0 0 1 {50 + x_in:.3f} {iy:.3f} Z")


KS = keystone_path()


def lockup(color, key):
    return LOGO["lockup"].replace('class="logo"', f'style="height:54px;width:auto;color:{color};display:block"').replace('class="k"', f'fill="{key}"')


def photo_uri(pid):
    local = os.environ.get("PHOTO_DIR")
    if local and Path(local, f"{pid}.jpg").exists():
        data = Path(local, f"{pid}.jpg").read_bytes()
    else:
        url = f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w=1200"
        req = urllib.request.Request(url, headers={"User-Agent": "nuvo-social/1.0"})
        data = urllib.request.urlopen(req, timeout=60).read()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


CSS = """@font-face{font-family:B;src:url(%s) format('woff2');font-weight:200 800}
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:B;-webkit-font-smoothing:antialiased}
.logo{position:absolute;left:72px;top:68px}
.url{position:absolute;left:72px;bottom:62px;font-size:30px;font-weight:650;letter-spacing:-.01em}
.fit{font-weight:780;letter-spacing:-.035em;line-height:1}
.arch{position:absolute;overflow:hidden;border-radius:50%% 50%% 0 0 / 40%% 40%% 0 0}
.arch img{width:100%%;height:100%%;object-fit:cover;display:block}
.arch svg{position:absolute;inset:0;width:100%%;height:100%%}
.ico{width:1em;height:1em;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
""" % FONT

FIT_JS = """
for (const el of document.querySelectorAll('[data-fit]')) {
  const max = +el.dataset.max, min = +el.dataset.min, box = +el.dataset.h;
  let s = max; el.style.fontSize = s + 'px';
  while (el.scrollHeight > box && s > min) { s -= 2; el.style.fontSize = s + 'px'; }
}
"""


def fit(text, top, h, maxs, mins, color, width=936, left=72, extra=""):
    return (f'<div class="fit" data-fit data-max="{maxs}" data-min="{mins}" data-h="{h}" '
            f'style="position:absolute;left:{left}px;top:{top}px;width:{width}px;color:{color};{extra}">{esc(text)}</div>')


def url_label(p):
    return "nuvogroup.co" if p["lang"] == "es" else "nuvogroup.co/en"


def palette(p):
    n = int(p["id"][1:])
    return [(TEJA, "#fff", "#fff", CARBON), (CARBON, CAL, PEACH, KEY), (STONE, CARBON, TEJA, KEY)][n % 3]


def page(bg, body):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body style='background:{bg}'>{body}<script>{FIT_JS}</script></body></html>"


def t_statement(p):
    bg, fg, acc, key = palette(p)
    sub = p.get("sub", "")
    arch = (f'<svg viewBox="0 0 100 110" style="position:absolute;right:72px;bottom:150px;width:150px;opacity:.95">'
            f'<path d="M0 110 V50 A50 50 0 0 1 100 50 V110 H77 V50 A27 27 0 0 0 23 50 V110 Z" fill="{acc}" opacity=".18"/>'
            f'<path d="{KS}" fill="{acc}"/></svg>')
    return page(bg, f'<div class="logo">{lockup(fg, key if bg != TEJA else CARBON)}</div>'
                    + fit(p["headline"], 300, 560, 128, 64, fg)
                    + (f'<p style="position:absolute;left:72px;width:820px;top:900px;color:{fg};opacity:.92;font-size:40px;line-height:1.25;font-weight:450">{esc(sub)}</p>' if sub else "")
                    + arch + f'<div class="url" style="color:{acc}">{url_label(p)}</div>')


def t_question(p):
    bg, fg, acc, key = (TEJA, "#fff", "#fff", CARBON) if int(p["id"][1:]) % 2 else (CARBON, CAL, PEACH, KEY)
    return page(bg, f'<div class="logo">{lockup(fg, key)}</div>'
                    f'<div style="position:absolute;right:40px;top:120px;font-size:520px;font-weight:800;line-height:1;color:{acc};opacity:.14">?</div>'
                    + fit(p["headline"], 330, 560, 120, 60, fg)
                    + (f'<p style="position:absolute;left:72px;width:840px;top:930px;color:{fg};opacity:.92;font-size:40px;line-height:1.25;font-weight:450">{esc(p.get("sub",""))}</p>')
                    + f'<div class="url" style="color:{acc}">{url_label(p)}</div>')


def t_number(p):
    bg, fg, acc, key = (CARBON, CAL, PEACH, KEY)
    return page(bg, f'<div class="logo">{lockup(fg, key)}</div>'
                    f'<div style="position:absolute;left:60px;top:190px;font-size:360px;font-weight:800;letter-spacing:-.06em;line-height:1;color:{acc};white-space:nowrap">{esc(p["number"])}</div>'
                    + fit(p["headline"], 600, 330, 92, 52, fg)
                    + f'<p style="position:absolute;left:72px;width:880px;top:960px;color:#cfc6bd;font-size:40px;line-height:1.25;font-weight:450">{esc(p.get("sub",""))}</p>'
                    + f'<div class="url" style="color:{acc}">{url_label(p)}</div>')


def t_checklist(p):
    bullets = "".join(f'<li style="display:flex;gap:22px;align-items:center"><span style="flex:none;width:76px;height:76px;border-radius:50%;background:{TEJA};color:#fff;display:grid;place-items:center;font-size:42px"><svg class="ico" viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7"/></svg></span><span>{esc(b)}</span></li>' for b in p["bullets"])
    return page(STONE, f'<div class="logo">{lockup(CARBON, KEY)}</div>'
                       + fit(p["headline"], 250, 340, 104, 56, CARBON)
                       + f'<ul style="position:absolute;left:72px;right:72px;top:720px;list-style:none;display:grid;gap:52px;color:{CARBON};font-size:52px;font-weight:620;line-height:1.15;letter-spacing:-.01em">{bullets}</ul>'
                       + f'<div class="url" style="color:{TEJA}">{url_label(p)}</div>')


def t_photo(p):
    n = int(p["id"][1:])
    bg, fg, acc, key = (TEJA, "#fff", "#fff", CARBON) if n % 2 else (CARBON, CAL, PEACH, KEY)
    img = photo_uri(p["photo_id"])
    arch = (f'<div class="arch" style="left:432px;top:150px;width:576px;height:720px">'
            f'<img src="{img}" alt="">'
            f'<svg viewBox="0 0 100 125" preserveAspectRatio="none"><path d="{KS}" fill="{key}" stroke="{bg}" stroke-width="1.1" paint-order="stroke"/></svg></div>')
    return page(bg, f'<div class="logo">{lockup(fg, key)}</div>' + arch
                    + fit(p["headline"], 905, 230, 84, 48, fg)
                    + f'<p style="position:absolute;left:72px;width:900px;top:1145px;color:{fg};opacity:.92;font-size:34px;line-height:1.25;font-weight:450">{esc(p.get("sub",""))}</p>'
                    + f'<div class="url" style="color:{acc};bottom:40px;left:auto;right:72px">{url_label(p)}</div>')


TEMPLATES = {"statement": t_statement, "question": t_question, "number": t_number, "checklist": t_checklist, "photo": t_photo}


async def render(ids):
    OUT.mkdir(exist_ok=True)
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        for pid in ids:
            p = POSTS[pid]
            await pg.set_content(TEMPLATES[p["template"]](p), wait_until="load")
            await pg.evaluate("document.fonts.ready")
            await pg.evaluate(FIT_JS)
            await pg.wait_for_timeout(150)
            path = OUT / f"{pid}.jpg"
            await pg.screenshot(path=str(path), type="jpeg", quality=90)
            print(path)
        await b.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    ids = list(POSTS) if args == ["--all"] else args
    asyncio.run(render(ids))
