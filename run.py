"""Nuvo social autopilot: every 3 days at 5 a.m. (Houston time) render the next post and publish it
to the Facebook Page and the connected Instagram account through the Meta Graph API.

Environment:
  META_TOKEN      Page access token or system-user token with pages_manage_posts,
                  pages_read_engagement, instagram_basic, instagram_content_publish (GitHub secret)
  PAGE_ID         Facebook Page id for the Graph API (default 1362020253662270)
  GRAPH_VERSION   default v25.0
  MODE            "auto" (scheduled), "dry-run" (render only) or "publish" (publish now)
  EVERY_DAYS      default 3
  GITHUB_REPOSITORY, GITHUB_TOKEN   provided by Actions
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
STATE = HERE / "state.json"
POSTS = json.loads((HERE / "posts.json").read_text())["posts"]
TZ = ZoneInfo("America/Chicago")
PAGE_ID = os.environ.get("PAGE_ID") or "1362020253662270"  # Graph API id of the Nuvo Group page
VER = os.environ.get("GRAPH_VERSION") or "v25.0"
MODE = (os.environ.get("MODE") or "auto").strip()
EVERY = int(os.environ.get("EVERY_DAYS") or 3)
GRAPH = f"https://graph.facebook.com/{VER}"


def log(*a):
    print(*a, flush=True)


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"next_index": 0, "last_published": None, "history": []}


def save_state(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n")


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=HERE, check=check, capture_output=True, text=True)


def commit_push(msg, paths):
    git("config", "user.name", "nuvo-autopilot")
    git("config", "user.email", "actions@users.noreply.github.com")
    git("add", *paths)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return git("rev-parse", "HEAD").stdout.strip()
    git("commit", "-m", msg)
    for i in range(3):
        if git("push", check=False).returncode == 0:
            break
        git("pull", "--rebase", check=False)
    return git("rev-parse", "HEAD").stdout.strip()


def api(method, path, params, retries=2):
    url = path if path.startswith("http") else f"{GRAPH}/{path}"
    data = urllib.parse.urlencode(params).encode()
    for attempt in range(retries + 1):
        try:
            if method == "GET":
                req = urllib.request.Request(url + "?" + data.decode())
            else:
                req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if attempt < retries and e.code >= 500:
                time.sleep(5 * (attempt + 1)); continue
            # never print the token
            raise RuntimeError(f"Graph API {e.code} on {path}: {body[:600]}") from None


def should_run(state):
    now = datetime.now(TZ)
    if MODE in ("dry-run", "publish"):
        return True, f"manual {MODE}"
    # GitHub can start scheduled runs late, so accept 5:00-6:59; the 3-day rule below prevents doubles.
    if not 5 <= now.hour < 7:
        return False, f"not 5 a.m. in Houston (it's {now:%H:%M})"
    last = state.get("last_published")
    if last:
        last_d = datetime.fromisoformat(last).astimezone(TZ).date()
        if (now.date() - last_d).days < EVERY:
            return False, f"last post {last_d}, next due {last_d + timedelta(days=EVERY)}"
    return True, "due"


def caption_for(p):
    tags = " ".join(h if h.startswith("#") else "#" + h for h in p.get("hashtags", []))
    return p["caption"].strip() + ("\n\n" + tags if tags else "")


def page_info(token):
    """Return (page_id, info) with the page token and linked Instagram account."""
    fields = "id,name,access_token,instagram_business_account"
    try:
        return PAGE_ID, api("GET", PAGE_ID, {"fields": fields, "access_token": token})
    except RuntimeError as e:
        log("page lookup by id failed, trying me/accounts:", str(e)[:160])
    pages = api("GET", "me/accounts", {"fields": fields, "access_token": token}).get("data", [])
    if not pages:
        raise RuntimeError("The token has no Facebook Page assigned (check the system user's assets)")
    page = next((x for x in pages if x["id"] == PAGE_ID), None) or next((x for x in pages if "nuvo" in x.get("name", "").lower()), pages[0])
    return page["id"], page


def publish(p, image_url):
    token = os.environ["META_TOKEN"]
    page_id, info = page_info(token)
    log("page:", page_id, info.get("name", ""))
    page_token = info.get("access_token") or token
    ig = (info.get("instagram_business_account") or {}).get("id")
    cap = caption_for(p)
    out = {}
    fb = api("POST", f"{page_id}/photos", {"url": image_url, "caption": cap, "published": "true", "access_token": page_token})
    out["facebook"] = fb.get("post_id") or fb.get("id")
    log("Facebook OK", out["facebook"])
    if ig:
        c = api("POST", f"{ig}/media", {"image_url": image_url, "caption": cap, "access_token": page_token})
        cid = c["id"]
        for _ in range(20):
            st = api("GET", cid, {"fields": "status_code", "access_token": page_token}).get("status_code")
            if st == "FINISHED":
                break
            if st == "ERROR":
                raise RuntimeError("Instagram could not process the image")
            time.sleep(5)
        pub = api("POST", f"{ig}/media_publish", {"creation_id": cid, "access_token": page_token})
        out["instagram"] = pub.get("id")
        log("Instagram OK", out["instagram"])
    else:
        log("No Instagram account linked to the page: skipped Instagram")
    return out


def main():
    state = load_state()
    go, why = should_run(state)
    log("decision:", go, "-", why)
    if not go:
        return 0
    if MODE != "dry-run" and not os.environ.get("META_TOKEN"):
        log("::warning::Falta el secreto META_TOKEN: no se publica hasta que se agregue en Settings > Secrets.")
        return 0
    idx = state["next_index"] % len(POSTS)
    p = POSTS[idx]
    log("post:", p["id"], p["lang"], p["template"], "-", p["headline"])
    subprocess.run([sys.executable, str(HERE / "render.py"), p["id"]], check=True)
    image_rel = f"out/{p['id']}.jpg"
    sha = commit_push(f"Imagen {p['id']}", [image_rel])
    repo = os.environ.get("GITHUB_REPOSITORY", "ivan0627/nuvo-social")
    image_url = f"https://raw.githubusercontent.com/{repo}/{sha}/{image_rel}"
    log("image:", image_url)
    if MODE == "dry-run":
        log("dry-run: not published")
        return 0
    time.sleep(8)  # let the raw CDN pick up the new commit
    result = publish(p, image_url)
    state["history"].append({"id": p["id"], "at": datetime.now(TZ).isoformat(timespec="seconds"), **result})
    state["last_published"] = datetime.now(TZ).isoformat(timespec="seconds")
    state["next_index"] = idx + 1
    save_state(state)
    commit_push(f"Publicado {p['id']}", ["state.json"])
    left = len(POSTS) - state["next_index"]
    if left <= 5:
        log(f"::warning::Quedan {max(left, 0)} publicaciones nuevas en posts.json. Después se repite el banco desde el inicio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
