# login_manager.py — minimal GUI login passthrough

import sys, asyncio, subprocess

# اختيارية: علشان الـ type hints
try:
    from customtkinter import CTk
except Exception:
    CTk = object  # type: ignore

# ===== ألوان (مطلق ثم نسبي) + Fallback =====
try:
    from colors import *  # يفترض وجود success, info, warning, danger
except ImportError:
    try:
        from .colors import *
    except Exception:
        # ألوان افتراضية لو ملف colors غير متاح
        success = "#22aa22"
        info    = "#2b6cb0"
        warning = "#cc8800"
        danger  = "#cc3333"

# ===== secretvars (مطلق ثم نسبي) + Fallback بسيط =====
try:
    import secretvars
except ImportError:
    try:
        from . import secretvars
    except Exception:
        class _SV: pass
        secretvars = _SV()
        secretvars.Thread_Pool = []
        secretvars.MAIN_FLAG = 1

# ===== render_text آمن مع Fallback =====
try:
    from awesometkinter.bidirender import render_text
except Exception:
    try:
        from bidi.algorithm import get_display as render_text
    except Exception:
        def render_text(s: str) -> str:
            return s

# ===== ويندوز: لوب مناسب للـ asyncio =====
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass


def get_serial_num() -> str:
    """سيريال الماكينة (اختياري)."""
    try:
        # wmic قد يكون Deprecated في بعض النسخ؛ ده مجرد Helper
        result = subprocess.run(
            ["wmic", "bios", "get", "serialnumber"],
            capture_output=True, text=True, shell=False
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return lines[-1] if lines else ""
    except Exception:
        return ""


async def check_login(username: str, password: str, window: CTk) -> None:
    """
    تجاوز التحقق الحقيقي: يحدّث الحالة ويفتح الواجهة الرئيسية.
    بنشغّل تحديثات الـTkinter على الـmain thread بـ window.after(0, ...)
    """
    def _go():
        try:
            window.status.configure(text=render_text('تم تسجيل الدخول بنجاح'), text_color=success)
        except Exception:
            pass
        try:
            window.init_canva()
        except Exception:
            pass

    try:
        window.after(0, _go)  # نفّذ على مسلك tkinter الرئيسي
    except Exception:
        _go()
