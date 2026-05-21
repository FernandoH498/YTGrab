#!/usr/bin/env python3
"""
Run this locally AFTER completing YouTube OAuth2 auth to generate
the YOUTUBE_OAUTH2_TOKEN value for Railway.

Steps:
  1. pip install yt-dlp yt-dlp-youtube-oauth2
  2. yt-dlp --username oauth2 --password "" https://www.youtube.com/watch?v=dQw4w9WgXcQ
     (open the URL it prints, sign in, then press Enter)
  3. python get_oauth2_token.py
  4. Copy the output and set it as YOUTUBE_OAUTH2_TOKEN in Railway
"""
import glob
import json
import os
import platform
import sys


def _candidate_dirs() -> list[str]:
    system = platform.system()
    if system == "Windows":
        return [
            os.path.join(os.getenv("APPDATA", ""), "yt-dlp"),
            os.path.join(os.getenv("LOCALAPPDATA", ""), "yt-dlp"),
        ]
    if system == "Darwin":
        return [os.path.expanduser("~/Library/Caches/yt-dlp")]
    xdg = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return [os.path.join(xdg, "yt-dlp")]


token_files = []
for base in _candidate_dirs():
    token_files.extend(glob.glob(os.path.join(base, "youtube-oauth2", "*.json")))

if not token_files:
    print("No OAuth2 token found. Run:\n")
    print("  pip install yt-dlp yt-dlp-youtube-oauth2")
    print('  yt-dlp --username oauth2 --password "" https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    sys.exit(1)

token_file = token_files[0]
key = os.path.basename(token_file)
with open(token_file, encoding="utf-8") as f:
    token = json.load(f)

output = json.dumps({"key": key, "token": token}, separators=(",", ":"))
print("Set this as YOUTUBE_OAUTH2_TOKEN in Railway:\n")
print(output)
