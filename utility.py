# utility.py — proxy helpers ثابت/متغيّر بدون أسرار صلبة
import os, sys, random, string
from typing import Optional, Dict, Union

def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

_ALPHABET = string.ascii_letters + string.digits
def generate_random_str(n: int = 8) -> str:
    return "".join(random.choice(_ALPHABET) for _ in range(n))

def _should_rotate(suffix: str) -> bool:
    """
    ندوّر بس لو:
    - PROXY_STICKY=0 (أو غير محدد)
    - وفي suffix فيه {session}
    """
    sticky = os.getenv("PROXY_STICKY", "1").strip()  # الافتراضي: ثابت
    return (sticky == "0") and ("{session}" in (suffix or ""))

def rotate_proxy(async_session: bool = False) -> Optional[Union[str, Dict[str, str]]]:
    """
    يكوّن بروكسي SOCKS5 من متغيرات البيئة:
      PROXY_USER, PROXY_PASS, PROXY_HOST, PROXY_PORT, PROXY_SUFFIX (اختياري)
    ملاحظات:
      - لو PROXY_STICKY=1 (الافتراضي): مش هنبدّل {session} -> يفضل ثابت.
      - لو PROXY_STICKY=0 ومعاكي {session} في PROXY_SUFFIX: هنولّد Session عشوائي.
    إخراج:
      - async_session=True  -> string "socks5://user:pass@host:port{suffix}" (مناسب لـ Playwright)
      - otherwise           -> dict  {'http': 'socks5h://...', 'https': 'socks5h://...'} (لـ requests)
    """
    user   = os.getenv("PROXY_USER")
    pwd    = os.getenv("PROXY_PASS")
    host   = os.getenv("PROXY_HOST")
    port   = os.getenv("PROXY_PORT")
    suffix = os.getenv("PROXY_SUFFIX", "")  # مثال: "_country-eg_city-alexandria_session-{session}_lifetime-168h"

    if not all([user, pwd, host, port]):
        return None

    # قرري هل هنروّتِت السيشن ولا لأ
    if _should_rotate(suffix):
        sess = generate_random_str(8)
        suffix = suffix.replace("{session}", sess)
    else:
        # لو فيه placeholder ومش عايزة تدوير، شيله أو سيبيه زي ما هو (لو عايزة اسم محدد)
        # هنا هنسيبه كما هو لو فيه اسم متحدد بالفعل
        pass

    scheme = "socks5"
    base = f"{scheme}://{user}:{pwd}@{host}:{port}{suffix}"

    if async_session:
        # Playwright → لازم string مع البروتوكول
        return base

    # requests/urllib3 → dict مع socks5h (يعدّي الـDNS عبر البروكسي)
    return {
        "http":  f"{scheme}h://{user}:{pwd}@{host}:{port}{suffix}",
        "https": f"{scheme}h://{user}:{pwd}@{host}:{port}{suffix}",
    }

# Helpers اختيارية:
def playwright_proxy_parts() -> Optional[Dict[str, str]]:
    """
    يجهّز أجزاء بروكسي لـ Playwright:
      server = "socks5://host:port"
      username, password
    يستخدم PROXY_SERVER لو متوفر (مثلاً "geo.iproyal.com:12321")
    أو يبنيه من PROXY_HOST/PORT.
    """
    host = os.getenv("PROXY_HOST")
    port = os.getenv("PROXY_PORT")
    server_env = os.getenv("PROXY_SERVER")
    user = os.getenv("PROXY_USER")
    pwd  = os.getenv("PROXY_PASS")
    suffix = os.getenv("PROXY_SUFFIX", "")

    if not all([user, pwd]) or (not server_env and not (host and port)):
        return None

    # Playwright يتوقع server بدون user:pass جوّاه
    server = server_env or f"socks5://{host}:{port}"  # نزود البروتوكول هنا
    if not server.startswith("socks5://"):
        server = f"socks5://{server}"

    # لو عندك suffix زي country/session/lifetime في الPASS عند IPRoyal، سيبيه جوّه الـPASS نفسه
    # (IPRoyal بيقرأه من الـpassword)
    return {"server": server, "username": user, "password": pwd}
