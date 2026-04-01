from instagrapi import Client
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SESSION_CACHE = Path("session_cache")
LIKED_CACHE = SESSION_CACHE / "liked_posts.json"

def get_liked():
    if LIKED_CACHE.exists():
        return set(json.loads(LIKED_CACHE.read_text()))
    return set()

def save_liked(pks):
    LIKED_CACHE.write_text(json.dumps(sorted(pks)))

cl = Client()
cl.load_settings("session_cache/session.json")
cl.login(os.environ.get("INSTAGRAM_USERNAME"), os.environ.get("INSTAGRAM_PASSWORD"))

accounts = ["stuttgart_blog", "stuttgartmitkind", "ankes_insta"]
already_liked = get_liked()
new_likes = []

for username in accounts:
    uid = cl.user_id_from_username(username)
    medias = cl.user_medias(uid, amount=8)
    print(f"\n=== {username} ===")
    for m in medias:
        pk_str = str(m.pk)
        media_type = {1: "Photo", 2: "Video/Reel", 8: "Album"}.get(m.media_type, "?")
        caption = getattr(m, "caption_text", "") or ""
        print(f"[{media_type}] {pk_str}: {caption[:150] if caption else '(no caption)'}")
        print(f"  code={m.code}")
        if pk_str not in already_liked:
            print(f"  --> NEW, will like + comment")
        else:
            print(f"  --> already liked")