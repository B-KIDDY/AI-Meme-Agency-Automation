"""
8. Instagram Publisher – posts as Reels (video) by default
"""
import json
import time
import random
import os
import subprocess
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import (
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    RUN_MODE,
    LOGS_DIR,
    GENERATED_DIR,
)
from database import get_session, Meme

PUBLISH_AS_REELS = os.getenv("PUBLISH_AS_REELS", "true").lower() in ("1", "true", "yes")
REEL_DURATION_SEC = float(os.getenv("REEL_DURATION_SEC", "5"))


def _can_use_live() -> bool:
    return (
        RUN_MODE == "live"
        and bool(INSTAGRAM_ACCESS_TOKEN)
        and bool(INSTAGRAM_BUSINESS_ACCOUNT_ID)
    )


def _log(entry: dict):
    log_file = LOGS_DIR / "publish_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def upload_to_cloudinary(file_path: Path) -> Optional[str]:
    """Last-resort host. Needs CLOUDINARY_* in .env"""
    cloud = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    key = os.getenv("CLOUDINARY_API_KEY", "").strip()
    secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()
    if not (cloud and key and secret):
        return None
    is_video = str(file_path).lower().endswith((".mp4", ".mov", ".webm"))
    resource = "video" if is_video else "image"
    url = f"https://api.cloudinary.com/v1_1/{cloud}/{resource}/upload"
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                url,
                auth=(key, secret),
                files={"file": f},
                data={"folder": "ai_meme_agency"},
                timeout=180,
            )
        data = resp.json()
        secure = data.get("secure_url")
        if secure:
            print(f"☁️  Uploaded to Cloudinary → {secure}")
            return secure
        print(f"⚠️ Cloudinary failed: {resp.status_code} {str(data)[:150]}")
    except Exception as e:
        print(f"⚠️ Cloudinary error: {e}")
    return None

def upload_to_imgur(image_path: Path, client_id: str = None) -> Optional[str]:
    client_id = client_id or os.getenv("IMGUR_CLIENT_ID", "")
    if not client_id:
        return None
    headers = {"Authorization": f"Client-ID {client_id}"}
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://api.imgur.com/3/image",
                headers=headers,
                files={"image": f},
                timeout=30,
            )
        if resp.status_code == 200:
            url = resp.json()["data"]["link"]
            print(f"☁️  Uploaded to Imgur → {url}")
            return url
        print(f"⚠️ Imgur failed: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Imgur error: {e}")
    return None


def upload_to_catbox(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (file_path.name, f)},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=180,
            )
        text = (resp.text or "").strip()
        if resp.status_code == 200 and text.startswith("http"):
            print(f"☁️  Uploaded to catbox → {text}")
            return text
        print(f"⚠️ catbox failed: {resp.status_code} {text[:150]}")
    except Exception as e:
        print(f"⚠️ catbox error: {e}")
    return None


def upload_to_litterbox(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "24h"},
                files={"fileToUpload": (file_path.name, f)},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=180,
            )
        text = (resp.text or "").strip()
        if resp.status_code == 200 and text.startswith("http"):
            print(f"☁️  Uploaded to litterbox → {text}")
            return text
        print(f"⚠️ litterbox failed: {resp.status_code} {text[:150]}")
    except Exception as e:
        print(f"⚠️ litterbox error: {e}")
    return None


def upload_to_fileio(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://file.io",
                files={"file": (file_path.name, f)},
                data={"expires": "1d"},
                timeout=180,
            )
        if resp.status_code == 200:
            data = resp.json()
            url = data.get("link") or data.get("url")
            if url:
                print(f"☁️  Uploaded to file.io → {url}")
                return url
        print(f"⚠️ file.io failed: {resp.status_code} {resp.text[:120]}")
    except Exception as e:
        print(f"⚠️ file.io error: {e}")
    return None


def upload_to_0x0(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post("https://0x0.st", files={"file": f}, timeout=60)
        text = (resp.text or "").strip()
        if resp.status_code == 200 and text.startswith("http"):
            print(f"☁️  Uploaded to 0x0.st → {text}")
            return text
        print(f"⚠️ 0x0.st failed: {resp.status_code} {text[:120]}")
    except Exception as e:
        print(f"⚠️ 0x0.st error: {e}")
    return None


def upload_to_gofile(file_path: Path) -> Optional[str]:
    """Only DIRECT link — page links (gofile.io/d/...) break IG containers."""
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://upload.gofile.io/uploadfile",
                files={"file": (file_path.name, f)},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=180,
            )
        data = resp.json()
        if data.get("status") == "ok":
            d = data.get("data") or {}
            url = d.get("directLink")
            if url and url.startswith("http"):
                print(f"☁️  Uploaded to gofile (direct) → {url}")
                return url
            print("⚠️ gofile only gave page link — skip for IG")
            return None
        print(f"⚠️ gofile failed: {resp.status_code} {str(data)[:150]}")
    except Exception as e:
        print(f"⚠️ gofile error: {e}")
    return None


def upload_to_transfer_sh(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            resp = requests.put(
                f"https://transfer.sh/{file_path.name}",
                data=f,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=180,
            )
        text = (resp.text or "").strip()
        if resp.status_code in (200, 201) and text.startswith("http"):
            print(f"☁️  Uploaded to transfer.sh → {text}")
            return text
        print(f"⚠️ transfer.sh failed: {resp.status_code} {text[:120]}")
    except Exception as e:
        print(f"⚠️ transfer.sh error: {e}")
    return None


def upload_to_tmpfiles(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": (file_path.name, f)},
                timeout=180,
            )
        data = resp.json()
        url = (data.get("data") or {}).get("url")
        if url:
            if "tmpfiles.org/" in url and "/dl/" not in url:
                url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            if url.startswith("http://"):
                url = "https://" + url[7:]
            print(f"☁️  Uploaded to tmpfiles → {url}")
            return url
        print(f"⚠️ tmpfiles failed: {resp.status_code} {str(data)[:120]}")
    except Exception as e:
        print(f"⚠️ tmpfiles error: {e}")
    return None


def get_public_image_url(image_path: Path) -> Optional[str]:
    # TEMP: Cloudinary first so IG gets a real direct URL
    url = upload_to_cloudinary(image_path)
    if url:
        return url

    is_video = str(image_path).lower().endswith((".mp4", ".mov", ".webm"))
    if not is_video:
        url = upload_to_imgur(image_path)
        if url:
            return url

    for uploader in (
        upload_to_transfer_sh,
        upload_to_tmpfiles,
        upload_to_catbox,
        upload_to_litterbox,
        upload_to_gofile,
        upload_to_fileio,
        upload_to_0x0,
    ):
        try:
            url = uploader(image_path)
            if url:
                return url
        except Exception as e:
            print(f"⚠️ upload attempt failed: {e}")

    print("❌ No public media host worked.")
    return None

def _find_bg_music() -> Optional[Path]:
    base = Path(__file__).parent
    tracks = []
    music_dir = base / "music"
    if music_dir.is_dir():
        for p in music_dir.glob("*.*"):
            if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg"):
                tracks.append(p)
    for name in ("bg.mp3", "background.mp3", "music.mp3", "bg_music.mp3"):
        p = base / name
        if p.exists() and p not in tracks:
            tracks.append(p)
    if not tracks:
        return None
    return random.choice(tracks)


def image_to_reel_video(image_path: Path, duration: float = None) -> Optional[Path]:
    duration = duration or REEL_DURATION_SEC
    if not shutil.which("ffmpeg"):
        print("❌ ffmpeg not found. Install ffmpeg to publish Reels.")
        return None

    out = Path(GENERATED_DIR) / f"{image_path.stem}_reel.mp4"
    vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p"
    music = _find_bg_music()
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path)]

    v_encode = [
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-r", "30",
        "-movflags", "+faststart",
    ]

    if music:
        print(f"🎵 Using music: {music.name}")
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        cmd += [
            "-t", str(duration),
            *v_encode,
            "-map", "0:v", "-map", "1:a",
            "-c:a", "aac", "-b:a", "96k",
            "-shortest",
            str(out),
        ]
    else:
        print("⚠️ No music in music/ folder – silent reel")
        cmd += [
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(duration),
            *v_encode,
            "-map", "0:v", "-map", "1:a",
            "-c:a", "aac", "-b:a", "96k",
            "-shortest",
            str(out),
        ]

    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0:
            print(f"❌ ffmpeg failed: {r.stderr[-300:] if r.stderr else r.returncode}")
            return None
        if out.exists() and out.stat().st_size > 1000:
            print(f"🎬 Reel video ready → {out.name} ({out.stat().st_size // 1024} KB)")
            return out
    except Exception as e:
        print(f"❌ ffmpeg reel convert failed: {e}")
    return None


def _graph_base() -> str:
    token = (INSTAGRAM_ACCESS_TOKEN or "").strip()
    if token.startswith("IG"):
        return "https://graph.instagram.com/v21.0"
    return "https://graph.facebook.com/v21.0"


def _create_media_container(media_url: str, caption: str, as_reel: bool = False) -> Optional[str]:
    token = (INSTAGRAM_ACCESS_TOKEN or "").strip()
    account_id = (INSTAGRAM_BUSINESS_ACCOUNT_ID or "").strip()
    url = f"{_graph_base()}/{account_id}/media"
    if as_reel:
        payload = {
            "media_type": "REELS",
            "video_url": media_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        }
    else:
        payload = {
            "image_url": media_url,
            "caption": caption,
            "access_token": token,
        }
    try:
        resp = requests.post(url, data=payload, timeout=60)
        data = resp.json()
    except Exception as e:
        print(f"❌ Container request failed (network): {e}")
        return None
    if "id" in data:
        print(f"📦 Container created: {data['id']} ({'REEL' if as_reel else 'IMAGE'})")
        return data["id"]
    print(f"❌ Container creation failed: {data}")
    return None


def _wait_container_ready(container_id: str, max_wait: int = 120) -> bool:
    token = (INSTAGRAM_ACCESS_TOKEN or "").strip()
    url = f"{_graph_base()}/{container_id}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            resp = requests.get(
                url,
                params={"fields": "status_code,status", "access_token": token},
                timeout=30,
            )
            data = resp.json()
            status = (data.get("status_code") or "").upper()
            detail = data.get("status") or ""
            print(f"   … container status: {status} {detail}")
            if status == "FINISHED":
                return True
            if status in ("ERROR", "EXPIRED"):
                print(f"❌ Container error detail: {data}")
                return False
        except Exception as e:
            print(f"⚠️ status check: {e}")
        time.sleep(5)
    print("⚠️ Container not ready in time")
    return False


def _publish_container(container_id: str) -> Optional[str]:
    token = (INSTAGRAM_ACCESS_TOKEN or "").strip()
    account_id = (INSTAGRAM_BUSINESS_ACCOUNT_ID or "").strip()
    url = f"{_graph_base()}/{account_id}/media_publish"
    payload = {"creation_id": container_id, "access_token": token}
    time.sleep(2)
    try:
        resp = requests.post(url, data=payload, timeout=60)
        data = resp.json()
    except Exception as e:
        print(f"❌ Publish request failed (network): {e}")
        return None
    if "id" in data:
        print(f"✅ Published! Media ID: {data['id']}")
        return data["id"]
    print(f"❌ Publish failed: {data}")
    return None


def _simulate_publish(meme_id: int, image_path: Path, caption: str, reason: str = "sim_mode") -> dict:
    entry = {
        "meme_id": meme_id,
        "image": str(image_path),
        "caption": caption[:400],
        "status": "simulated_success",
        "reason": reason,
        "fake_post_id": f"sim_{meme_id}_{random.randint(10000, 99999)}",
        "simulated_at": datetime.utcnow().isoformat(),
    }
    _log(entry)
    session = get_session()
    meme = session.query(Meme).filter(Meme.id == meme_id).first()
    if meme:
        meme.is_published = True
        meme.published_at = datetime.utcnow()
        session.commit()
    session.close()
    print(f"📤 [SIM] Published meme #{meme_id} → {image_path.name} ({reason})")
    return entry


def _live_publish(meme_id: int, image_path: Path, caption: str) -> dict:
    mode = "REEL" if PUBLISH_AS_REELS else "POST"
    print(f"🚀 LIVE publishing meme #{meme_id} as {mode} …")
    public_url = None
    media_id = None
    try:
        media_path = image_path
        as_reel = PUBLISH_AS_REELS

        if as_reel:
            video_path = image_to_reel_video(image_path)
            if not video_path:
                print("⚠️ Reel convert failed – falling back to image post")
                as_reel = False
            else:
                media_path = video_path

        public_url = get_public_image_url(media_path)
        if not public_url:
            return _simulate_publish(meme_id, image_path, caption, reason="no_public_url")

        container_id = _create_media_container(public_url, caption, as_reel=as_reel)
        if not container_id:
            return _simulate_publish(meme_id, image_path, caption, reason="container_failed")

        if as_reel:
            if not _wait_container_ready(container_id):
                print("⚠️ Reel container failed – falling back to IMAGE post…")
                as_reel = False
                public_url = get_public_image_url(image_path)
                if not public_url:
                    return _simulate_publish(meme_id, image_path, caption, reason="container_not_ready")
                container_id = _create_media_container(public_url, caption, as_reel=False)
                if not container_id:
                    return _simulate_publish(meme_id, image_path, caption, reason="image_container_failed")

        media_id = _publish_container(container_id)
        if not media_id:
            return _simulate_publish(meme_id, image_path, caption, reason="publish_failed")
    except Exception as e:
        print(f"❌ LIVE publish error meme #{meme_id}: {e}")
        return _simulate_publish(meme_id, image_path, caption, reason=f"network_error:{e}")

    session = get_session()
    meme = session.query(Meme).filter(Meme.id == meme_id).first()
    if meme:
        meme.is_published = True
        meme.published_at = datetime.utcnow()
        session.commit()
    session.close()

    entry = {
        "meme_id": meme_id,
        "image": str(image_path),
        "public_url": public_url,
        "caption": caption[:400],
        "status": "live_success",
        "instagram_media_id": media_id,
        "published_at": datetime.utcnow().isoformat(),
    }
    _log(entry)
    return entry


def publish_meme(meme_id: int, image_path: Path, caption: str, hashtags: list = None) -> dict:
    full_caption = caption or ""
    if hashtags:
        full_caption = f"{full_caption}\n\n{' '.join(hashtags)}".strip()
    if _can_use_live():
        return _live_publish(meme_id, image_path, full_caption)
    return _simulate_publish(meme_id, image_path, full_caption, reason="sim_mode")