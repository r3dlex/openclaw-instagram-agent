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

accounts = ["ankes_insta", "stuttgart_blog", "stuttgartmitkind"]
already_liked = get_liked()
newly_liked = []

for username in accounts:
    uid = cl.user_id_from_username(username)
    medias = cl.user_medias(uid, amount=10)
    print(f"\n=== {username} ===")
    for m in medias:
        if str(m.pk) in already_liked:
            continue
        media_type = {1: "Photo", 2: "Video/Reel", 8: "Album"}.get(m.media_type, "?")
        # Try to get caption from media object
        caption = ""
        try:
            caption = m.caption_text if hasattr(m, "caption_text") and m.caption_text else ""
        except:
            pass
        print(f"  [LIKE] {media_type}: {caption[:120] if caption else '(no caption)'}")
        try:
            cl.media_like(m.pk)
            already_liked.add(str(m.pk))
            newly_liked.append((username, media_type, caption[:120] if caption else ""))
            print(f"       LIKED")
        except Exception as e:
            print(f"       ERROR: {e}")

save_liked(already_liked)
print(f"\n=== SUMMARY ===")
print(f"New likes this run: {len(newly_liked)}")
for username, media_type, caption in newly_liked:
    print(f"  - [{username}] {media_type}: {caption}")
print(f"Total tracked likes: {len(already_liked)}")
