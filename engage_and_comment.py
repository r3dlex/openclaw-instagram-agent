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

# Comments per account and post (reels only, contextual)
comments = {
    "stuttgart_blog": {
        "DU8xJvsDCo-": "Toller Beitrag! Stuttgart West hat so viel zu bieten. 👏",
        "DWgYyP1iKou": "Das Mauritius Beach kenne ich noch gar nicht! Urlaubsfeeling mitten in der Stadt, wow! ☀️🏖️",
        "DWcFKRFiK8P": "So eine coole Idee! Schmuck selber machen in Stuttgart 👀✨",
        "DWdzJzACOjf": "Die Magnolien in der Wilhelma sind unglaublich! Danke für den Tipp 🌸",
        "DWOaz_ECHmX": "Du siehst großartig auf den neuen Business-Fotos! So mutig, sich vor die Linse zu trauen 📸",
        "DWG3f0NiJ1T": "Diese Terrasse muss ich dieses Jahr unbedingt besuchen! 😎☀️",
        "DV1QI1diPG-": "Faszinierend! So ein exklusiver Blick hinter die Kulissen von Stuttgart 21 🚧",
    },
    "stuttgartmitkind": {
        "DV5XPDwjAQU": "Was für eine tolle Idee! Nicky als Reporter 🧒📣 Die Perspektive von Kindern ist so wertvoll!",
        "DV_YIQOjMBg": "Artbeat.stg siehtmega aus! Nicky war ja direkt kreativ 🎨🤩",
        "DUiQDmZDPoD": "Mauri Games klingt nach perfektem Spaß für Nicky! 😄🎮",
        "DThm6gqjH7d": "Ein Indoor-Spielplatz in der Innenstadt? Nicky war wohl sofort Fan! 👀🎢",
        "DULGCtWjHya": "Build-a-Beard klingt nach einem Abenteuer! Nicky's Kuscheltier ist so cute ✂️🐻",
        "DTVqKCnDLfz": "Monatliches Spielzeug zum Testen? Nicky hat bestimmt Spaß dabei! 🎁🧸",
        "DTLlB13jPvW": "Das klingt nach dem perfekten Tag für Nicky! Spielen und Essen 🍽️🚗",
        "DUlab_ADJUX": "Nicky entdeckt Stuttgart aus der besten Perspektive 🧒✨",
    },
    "ankes_insta": {
        "DDfOPy4xwpT": "Wunderschöne Liebesgeschichte! ❤️ So schön, dass ihr sie bei @ichhier_dudort teilt!",
        "C_SbxlLtLon": "What a wonderful contribution to OursColorfully Languages! Greetings from Stuttgart 🇩🇪✨",
        "C7_EHeeMtOe6GKHmDnSd1PfvxancAyB5kokb340": "One year with Floriano already! 🥳 Wishing you all the love in the world! 💕",
    },
}

for username in accounts:
    uid = cl.user_id_from_username(username)
    medias = cl.user_medias(uid, amount=8)
    print(f"\n=== {username} ===")
    for m in medias:
        pk_str = str(m.pk)
        media_type = {1: "Photo", 2: "Video/Reel", 8: "Album"}.get(m.media_type, "?")
        caption = getattr(m, "caption_text", "") or ""
        code = m.code

        if pk_str not in already_liked:
            try:
                cl.media_like(pk_str)
                print(f"  LIKED: [{media_type}] {caption[:80] if caption else ''}")
            except Exception as e:
                print(f"  LIKE ERROR: {e}")

            # Comment on reels with context
            if media_type == "Video/Reel" and code in comments.get(username, {}):
                comment_text = comments[username][code]
                try:
                    cl.media_comment(pk_str, comment_text)
                    print(f"    COMMENTED: {comment_text}")
                except Exception as e:
                    print(f"    COMMENT ERROR: {e}")

            already_liked.add(pk_str)
        else:
            print(f"  SKIPPED (already liked): [{media_type}] {caption[:80] if caption else ''}")

save_liked(already_liked)
print(f"\nDone. Total tracked likes: {len(already_liked)}")