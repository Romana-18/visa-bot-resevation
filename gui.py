import sys
if sys.platform.startswith("win"):
    try:
        import winsound
    except Exception:
        winsound = None
else:
    winsound = None
from utility import rotate_proxy

from customtkinter import *
from tkinter import messagebox

# Try to import bidi rendering, fallback if not available
try:
    from awesometkinter.bidirender import render_text
except ImportError:
    try:
        from bidi.algorithm import get_display as render_text
    except ImportError:
        # Fallback: no bidi rendering
        def render_text(text):
            return text
import webbrowser
import os, subprocess, threading, shutil
from datetime import datetime, timedelta
import time  # للـ watchdog والتوقيت المطلق
import collections

# ===== Node runner config =====
NODE = os.environ.get("NODE_PATH") or shutil.which("node") or "node"
# نحاول الاسم اللي عندك أولاً، ولو مش موجود نجرب الاسم القياسي
_SCRIPT_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "visa-bot.js"),
]
for _cand in _SCRIPT_CANDIDATES:
    if os.path.isfile(_cand):
        SCRIPT = _cand
        break
else:
    # لو ولا واحد موجود، خليه الافتراضي الأول (وهنطبع ERR في وقت التشغيل)
    SCRIPT = _SCRIPT_CANDIDATES[0]

# ===== Colors (fallbacks) =====
try:
    from colors import *
except ImportError:
    success = "#22aa22"
    info    = "#2b6cb0"
    warning = "#cc8800"
    danger  = "#cc3333"
    danger_btn   = danger
    danger_hover = "#a32727"
    primary_hover = '#481878'

# ===== Optional deps =====
try:
    from Countdown import Countdown
except Exception:
    class Countdown:
        def __init__(self, h, m, s): pass
        def get_remaining_seconds(self): return 0
        def __str__(self): return "now"

# ===== Minimal log filter =====
MINIMAL_TAGS = (
    "[LOGIN]", "[API]", "[FOUND]", "[NONE]", "[ACTION]", "[HALT]", "[EXIT]", "[BOOT]",
    "[TIMER]", "[PRESS]", "[WATCH]", "[OK]", "[WARN]", "[ERR]"
)

def _is_important(line: str) -> bool:
    try:
        l = line.strip()
        return any(tag in l for tag in MINIMAL_TAGS)
    except Exception:
        return False


class App2(CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.node_proc = None
        self.start_delay = None
        self.countdown_job = None
        
        # أعلام العدّاد والحارس
        self.timer_armed = False
        self.timer_fired = False
        self.timer_target_ts = None   # وقت الهدف كـ timestamp (ثواني)
        self.watchdog_job = None      # after() الخاص بالحارس
        
        # وقت الإجراء (هنمرّره للـNode كـ START_AT_TS)
        self.pending_action_ts = None

        self.count = 0
        self.labels = []
        self.applicants = []
        self.workers = {}   # {email: subprocess.Popen}
        self.stop_all_event = threading.Event()

        # طابور وجدولة التشغيل المتوازي
        self.pending_accounts = collections.deque()  # طابور للحسابات الباقية
        self.MAX_PAR = 10     # حد أقصى للعمليات المتزامنة
        self.STAGGER_MS = 300 # فاصل زمني صغير بين الإطلاقات

        # ===== Layout =====
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Navigation
        self.navigation_frame = CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky='nsew')
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.navigation_frame_label = CTkLabel(
            self.navigation_frame, text='  ALMAVIVA',
            compound='left', font=CTkFont(size=15, weight='bold')
        )
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.home_button = CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                     text=render_text('الصفحة الرئيسية'), fg_color='transparent',
                                     text_color=('gray10', 'gray90'),
                                     hover_color=('gray70', 'gray30'),
                                     command=lambda: self.select_frame_by_name('home'))
        self.home_button.grid(row=1, column=0, sticky='ew')

        self.accounts_button = CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                         text=render_text('الحسابات'), fg_color='transparent',
                                         text_color=('gray10', 'gray90'),
                                         hover_color=('gray70', 'gray30'),
                                         command=lambda: self.select_frame_by_name('frame_4'))
        self.accounts_button.grid(row=2, column=0, sticky='ew')

        self.logs_button = CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                     text=render_text('التقارير'), fg_color='transparent',
                                     text_color=('gray10', 'gray90'),
                                     hover_color=('gray70', 'gray30'),
                                     command=lambda: self.select_frame_by_name('frame_5'))
        self.logs_button.grid(row=3, column=0, sticky='ew')

        # Pages
        # (تم التعديل) خلي الـ Home سكروابل
        self.home_frame   = CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')
        self.fourth_frame = CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')  # Accounts
        self.fifth_frame  = CTkScrollableFrame(self, corner_radius=0, fg_color='transparent')  # Logs

        # اربط عجلة الماوس للّوج (Windows)
        self._bind_scrollwheel_to_logs()
        # اربط الاسكرول لواجهة الـ Home برضه
        self._bind_scrollwheel_to(self.home_frame)

        # اختياري: اختصارات للتنقل في اللوج (Home/End/PageUp/PageDown) — robust canvas getter
        try:
            def _get_canvas():
                return getattr(self.fifth_frame, "_parent_canvas", None) or getattr(self.fifth_frame, "_canvas", None)
            self.bind_all("<End>",  lambda e: (_get_canvas() and _get_canvas().yview_moveto(1.0)))
            self.bind_all("<Home>", lambda e: (_get_canvas() and _get_canvas().yview_moveto(0.0)))
            self.bind_all("<Prior>", lambda e: (_get_canvas() and _get_canvas().yview_scroll(-1, "pages")))  # PageUp
            self.bind_all("<Next>",  lambda e: (_get_canvas() and _get_canvas().yview_scroll( 1, "pages")))  # PageDown
        except Exception:
            pass

        self.select_frame_by_name('home')

        for frame in [self.home_frame]:
            frame.grid_columnconfigure(0, weight=4, minsize=5)
            frame.grid_columnconfigure(1, weight=1)
            frame.grid_columnconfigure(2, weight=4)
        self.fifth_frame.grid_columnconfigure(0, weight=5)
        self.fourth_frame.grid_columnconfigure(0, weight=5)

        # ===== HOME (Login/Run) =====
        self.username_label = CTkLabel(self.home_frame, text=render_text('اسم المستخدم'))
        self.username_label.grid(row=0, column=2, sticky='nsew')
        # صندوق متعدد الأسطر لتجميع الميلات تحت بعض
        self.username_entry = CTkTextbox(self.home_frame, width=420, height=140)
        self.username_entry.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

        self.password_label = CTkLabel(self.home_frame, text=render_text('كلمة المرور'))
        self.password_label.grid(row=1, column=2, sticky='nsew')
        self.password_entry = CTkEntry(self.home_frame, show='*', width=170)
        self.password_entry.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)

        self.add_applicant_btn = CTkButton(self.home_frame, width=170, text=render_text('اضافة مستخدم'),
                                           command=lambda: self.add_applicant(self.username_entry.get("0.0", "end"),
                                                                              self.password_entry.get()))
        self.add_applicant_btn.grid(row=2, column=1, sticky='s', padx=5, pady=5)
        
        self.save_password_check  = StringVar(value='on')
        self.start_with_timer_check = StringVar(value='on')

        self.save_password = CTkCheckBox(self.home_frame, text=render_text('حفظ كلمة المرور'),
                                         variable=self.save_password_check, onvalue='on', offvalue='off')
        self.save_password.grid(row=2, column=0, sticky='s', padx=5, pady=5)

        self.start_with_timer_lbl = CTkLabel(self.home_frame, text=render_text('بدء الساعة المحددة بالأسفل'))
        self.start_with_timer_lbl.grid(row=6, column=2, sticky='s', padx=5, pady=5)
        self.start_with_timer_switch = CTkSwitch(self.home_frame, text='',
                                                 variable=self.start_with_timer_check, onvalue='on', offvalue='off')
        self.start_with_timer_switch.grid(row=6, column=1, sticky='s', padx=5, pady=5)
        self.start_with_timer_switch.configure(command=self._on_timer_switch)
        self._on_timer_switch()

        self.office_id_lbl = CTkLabel(self.home_frame, text=render_text('المكتب'))
        self.office_id_lbl.grid(row=3, column=2, sticky='s', padx=5, pady=5)
        self.office_id_option = CTkOptionMenu(self.home_frame, values=['Cairo', 'Alexandria'], width=170)
        self.office_id_option.set('Cairo')
        self.office_id_option.grid(row=3, column=1, sticky='s', padx=5, pady=5)

        self.visa_price_lbl = CTkLabel(self.home_frame, text=render_text('سعر الفيزا'))
        self.visa_price_lbl.grid(row=4, column=2, sticky='s', padx=5, pady=5)
        self.visa_price_options = CTkOptionMenu(self.home_frame,
                                                values=['Standard - EGP 1750', 'Vip - EGP 3810'],
                                                width=170)
        self.visa_price_options.set('Standard - EGP 1750')
        self.visa_price_options.grid(row=4, column=1, sticky='s', padx=5, pady=5)

        # Visa type (UI فقط)
        self.visa_options = {
            "Family Reunion Visa for spouses (D)": 18,
            "Business Visa (C)": 5,
            "Family Reunion Visa for children (D)": 20,
            "Study Visa (D)": 8,
            "Tourism Visa (C)": 1,
            "Re-entry Visa (D)": 4,
            "Family Reunion Visa for parents, (D)": 19,
            "Study Visa (C)": 9,
            "Employment Visa (D)": 3
        }
        self.visa_type_lbl = CTkLabel(self.home_frame, text=render_text('نوع الفيزا'))
        self.visa_type_lbl.grid(row=7, column=2, sticky='s', padx=5, pady=5)
        self.visa_type_option = CTkOptionMenu(self.home_frame, values=list(self.visa_options.keys()), width=170)
        self.visa_type_option.set("Employment Visa (D)")
        self.visa_type_option.grid(row=7, column=1, sticky='s', padx=5, pady=5)

        # Countdown inputs (وقت "الدخول/بدء التشغيل")
        self.start_time_hour_lbl = CTkLabel(self.home_frame, text=render_text('ساعة البدء'))
        self.start_time_hour_lbl.grid(row=8, column=2, sticky='s', padx=5, pady=5)
        self.start_time_hour_entry = CTkEntry(self.home_frame, width=70, placeholder_text='HH (0-23)')
        self.start_time_hour_entry.grid(row=8, column=1, sticky='w', padx=2, pady=5)
        self.start_time_hour_entry.insert(0, "08")

        self.start_time_min_lbl = CTkLabel(self.home_frame, text=render_text('دقيقة البدء'))
        self.start_time_min_lbl.grid(row=9, column=2, sticky='s', padx=5, pady=5)
        self.start_time_min_entry = CTkEntry(self.home_frame, width=50, placeholder_text='MM')
        self.start_time_min_entry.grid(row=9, column=1, sticky='w', padx=2, pady=5)
        self.start_time_min_entry.insert(0, "58")

        self.start_time_sec_lbl = CTkLabel(self.home_frame, text=render_text('ثانية البدء'))
        self.start_time_sec_lbl.grid(row=10, column=2, sticky='s', padx=5, pady=5)
        self.start_time_sec_entry = CTkEntry(self.home_frame, width=50, placeholder_text='SS')
        self.start_time_sec_entry.grid(row=10, column=1, sticky='w', padx=2, pady=5)
        self.start_time_sec_entry.insert(0, "00")

        # --- Action time (وقت الإجراء بعد اللوجين) ---
        self.action_time_hour_lbl = CTkLabel(self.home_frame, text=render_text('ساعة الإجراء'))
        self.action_time_hour_lbl.grid(row=8, column=0, sticky='s', padx=5, pady=5)
        self.action_time_hour_entry = CTkEntry(self.home_frame, width=70, placeholder_text='HH (0-23)')
        self.action_time_hour_entry.grid(row=8, column=0, sticky='w', padx=2, pady=5)
        self.action_time_hour_entry.insert(0, "08")

        self.action_time_min_lbl = CTkLabel(self.home_frame, text=render_text('دقيقة الإجراء'))
        self.action_time_min_lbl.grid(row=9, column=0, sticky='s', padx=5, pady=5)
        self.action_time_min_entry = CTkEntry(self.home_frame, width=50, placeholder_text='MM')
        self.action_time_min_entry.grid(row=9, column=0, sticky='w', padx=2, pady=5)
        self.action_time_min_entry.insert(0, "59")

        self.action_time_sec_lbl = CTkLabel(self.home_frame, text=render_text('ثانية الإجراء'))
        self.action_time_sec_lbl.grid(row=10, column=0, sticky='s', padx=5, pady=5)
        self.action_time_sec_entry = CTkEntry(self.home_frame, width=50, placeholder_text='SS')
        self.action_time_sec_entry.grid(row=10, column=0, sticky='w', padx=2, pady=5)
        self.action_time_sec_entry.insert(0, "50")

        # Countdown label
        self.countdown_label = CTkLabel(self.home_frame, text=render_text('العدّاد: --:--:--'))
        self.countdown_label.grid(row=12, column=1, sticky='w', padx=5, pady=5)

        # Arm countdown button
        self.arm_countdown_btn = CTkButton(self.home_frame, text=render_text('تفعيل البدء مع العدّاد'), command=self._arm_countdown)
        self.arm_countdown_btn.grid(row=11, column=2, sticky='s', padx=5, pady=5)

        # Mode (UI فقط)
        self.mode_lbl = CTkLabel(self.home_frame, text=render_text('الوضع'))
        self.mode_lbl.grid(row=5, column=2, sticky='s', padx=5, pady=5)
        self.mode_option = CTkOptionMenu(self.home_frame,
                                         values=[render_text('استكمال حجز'), render_text('البحث عن حجز')],
                                         width=170)
        self.mode_option.set(render_text('البحث عن حجز'))
        self.mode_option.grid(row=5, column=1, sticky='s', padx=5, pady=5)

        # City & Trip date
        self.city_label = CTkLabel(self.home_frame, text=render_text('المدينة (City)'))
        self.city_label.grid(row=13, column=2, sticky='nsew', padx=5, pady=5)
        self.city_entry = CTkEntry(self.home_frame, width=170, placeholder_text='مثال: milano')
        self.city_entry.grid(row=13, column=1, sticky='nsew', padx=5, pady=5)

        self.date_label = CTkLabel(self.home_frame, text=render_text('تاريخ الرحلة (DD/MM/YYYY)'))
        self.date_label.grid(row=14, column=2, sticky='nsew', padx=5, pady=5)
        self.date_entry = CTkEntry(self.home_frame, width=170, placeholder_text='DD/MM/YYYY')
        self.date_entry.grid(row=14, column=1, sticky='nsew', padx=5, pady=5)

        # Switches (hunt-only)
        self.auto_check_var   = StringVar(value='on')
        self.auto_proceed_var = StringVar(value='off')
        self.halt_on_found_var= StringVar(value='on')
        self.beep_var         = StringVar(value='on')
        self.alert_var        = StringVar(value='on')

        self.auto_check_sw = CTkSwitch(self.home_frame, text=render_text('اضغط Check تلقائيًا'),
                                       variable=self.auto_check_var, onvalue='on', offvalue='off')
        self.auto_check_sw.grid(row=15, column=2, sticky='s', padx=5, pady=2)

        self.auto_proceed_sw = CTkSwitch(self.home_frame, text=render_text('اضغط Proceed تلقائيًا'),
                                         variable=self.auto_proceed_var, onvalue='on', offvalue='off')
        self.auto_proceed_sw.grid(row=15, column=1, sticky='s', padx=5, pady=2)

        self.halt_sw = CTkSwitch(self.home_frame, text=render_text('إيقاف عند أوّل ميعاد'),
                                 variable=self.halt_on_found_var, onvalue='on', offvalue='off')
        self.halt_sw.grid(row=16, column=2, sticky='s', padx=5, pady=2)

        self.beep_sw = CTkSwitch(self.home_frame, text=render_text('صوت عند العثور'),
                                 variable=self.beep_var, onvalue='on', offvalue='off')
        self.beep_sw.grid(row=16, column=1, sticky='s', padx=5, pady=2)

        self.alert_sw = CTkSwitch(self.home_frame, text=render_text('تنبيه في اللوج'),
                                  variable=self.alert_var, onvalue='on', offvalue='off')
        self.alert_sw.grid(row=17, column=2, sticky='s', padx=5, pady=2)

        # Days ahead
        self.days_label = CTkLabel(self.home_frame, text=render_text('أيام بحث للأمام'))
        self.days_label.grid(row=18, column=2, sticky='nsew', padx=5, pady=5)
        self.days_entry = CTkEntry(self.home_frame, width=90, placeholder_text='مثال: 14')
        self.days_entry.insert(0, "14")
        self.days_entry.grid(row=18, column=1, sticky='w', padx=5, pady=5)

        # ===== Rate (RPS) =====
        self.rps_label = CTkLabel(self.home_frame, text=render_text('سرعة الطلبات (RPS)'))
        self.rps_label.grid(row=18, column=0, sticky='nsew', padx=5, pady=5)
        self.rps_option = CTkOptionMenu(self.home_frame, values=['2','3','4','5','6','8','10'], width=90)
        self.rps_option.set('6')
        self.rps_option.grid(row=18, column=0, sticky='w', padx=5, pady=5)

        # Start / Stop
        self.start_program_button = CTkButton(self.home_frame, text=render_text('بدء البرنامج'),
                                              command=self.start_execution)
        self.start_program_button.grid(row=19, column=2, sticky='s', padx=5, pady=5)

        self.home_disable_btn = CTkButton(self.home_frame, text=render_text('تعطيل البرنامج'),
                                          command=self.stop_execution, state='normal')
        self.home_disable_btn.grid(row=19, column=0, sticky='s', padx=5, pady=5)

        # ===== Accounts (frame_4) =====
        self.run_all_seq_btn = CTkButton(
            self.fourth_frame,
            text=render_text('تشغيل كل الحسابات (وراء بعض)'),
            command=self.start_sequential,
        )
        self.run_all_seq_btn.grid(row=0, column=0, sticky='nsew', padx=5, pady=8)

        self.run_all_par_btn = CTkButton(
            self.fourth_frame,
            text=render_text('تشغيل كل الحسابات (مع بعض)'),
            command=self.start_parallel,
        )
        self.run_all_par_btn.grid(row=1, column=0, sticky='nsew', padx=5, pady=8)

        self.stop_all_btn = CTkButton(
            self.fourth_frame,
            text=render_text('إيقاف كل العمليات'),
            command=self.stop_all_parallel,
            fg_color=danger_btn, hover_color=danger_hover
        )
        self.stop_all_btn.grid(row=2, column=0, sticky='nsew', padx=5, pady=8)

        # ===== Logs (frame_5) =====
        self.home_frame.grid_rowconfigure(12, weight=1)

        for frame in [self.home_frame]:
            for child in frame.winfo_children():
               if isinstance(child, (CTkEntry, CTkTextbox)):
                    child.bind('<Button-3>', self.right_click_event)

    # =================== Node runner helpers ===================

    def append_log(self, msg: str, color=info):
        self.print_in_log(msg, color=color)

    def _pump_node_stdout(self):
        """قراءة لوج العملية الأساسية مع فلترة للتاجات المهمة فقط."""
        code = None
        try:
            if not self.node_proc or not self.node_proc.stdout:
                self.append_log("[ERR] no node stdout to read", color=danger)
                return
            # اقرأ سطر-بسطر لتفادي مشاكل البفر على ويندوز
            for line in iter(self.node_proc.stdout.readline, ''):
                if not line:
                    break
                line = line.rstrip("\n")
                if _is_important(line):
                    self.append_log(line)
        except Exception as e:
            self.append_log(f"[ERR] log reader: {e}", color=danger)
        finally:
            try:
                code = self.node_proc.poll()
            except Exception:
                code = None
            # اطبع EXIT فقط لو العملية فعلاً خلصت (مش None)
            if code is not None:
                self.append_log(f"[EXIT] node process finished with code {code}", color=warning)

    # ======== (تم تعديلها) ربط الاسكرول للّوج بحيث يشتغل على جميع إصدارات CTk ========
    def _bind_scrollwheel_to_logs(self):
        """
        يربط عجلة الماوس بالـ Logs على ويندوز بشكل مضمون.
        يدعم اختلاف اسم الـcanvas الداخلي بين الإصدارات (_parent_canvas أو _canvas).
        ويربط كمان على الـframe نفسه + bind_all كشبكة أمان.
        """
        canvas = getattr(self.fifth_frame, "_parent_canvas", None) or getattr(self.fifth_frame, "_canvas", None)
        if canvas is None:
            return

        def _on_mousewheel(event):
            step = int(-event.delta / 120) if event.delta else 0
            if step != 0:
                canvas.yview_scroll(step, "units")
            return "break"

        # اربط على مستوى الـframe والـcanvas
        try:
            self.fifth_frame.bind("<MouseWheel>", _on_mousewheel, add="+")
        except Exception:
            pass
        try:
            canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        except Exception:
            pass
        try:
            self.bind_all("<MouseWheel>", _on_mousewheel)
        except Exception:
            pass

        # فعل/عطّل الربط حسب دخول/خروج المؤشر من اللوج
        def _enter(_):
            try:
                canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
            except Exception:
                pass

        def _leave(_):
            try:
                canvas.unbind("<MouseWheel>")
            except Exception:
                pass

        try:
            self.fifth_frame.bind("<Enter>", _enter, add="+")
            self.fifth_frame.bind("<Leave>", _leave, add="+")
        except Exception:
            pass

    # ======== (جديدة) ربط الاسكرول لأي ScrollableFrame عام ========
    def _bind_scrollwheel_to(self, sframe):
        """
        يربط عجلة الماوس بأي CTkScrollableFrame (ويندوز).
        بيحاول يمسك الـcanvas الداخلي سواء اسمه _parent_canvas أو _canvas.
        """
        canvas = getattr(sframe, "_parent_canvas", None) or getattr(sframe, "_canvas", None)
        if canvas is None:
            return

        def _on_mousewheel(event):
            step = int(-event.delta / 120) if event.delta else 0
            if step:
                canvas.yview_scroll(step, "units")
            return "break"

        try: sframe.bind("<MouseWheel>", _on_mousewheel, add="+")
        except Exception: pass
        try: canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        except Exception: pass
        try: self.bind_all("<MouseWheel>", _on_mousewheel)
        except Exception: pass

    def _logs_autoscroll_if_needed(self):
        try:
            canvas = getattr(self.fifth_frame, "_parent_canvas", None) or getattr(self.fifth_frame, "_canvas", None)
            if not canvas:
                return
            first, last = canvas.yview()
            at_bottom = (abs(last - 1.0) < 0.02)
            if at_bottom:
                canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _pump_proc_filtered(self, proc, email, found_flag):
        """فلترة اللوج للتشغيل المتسلسل (لكل حساب)"""
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                line = line.rstrip("\n")
                if _is_important(line):
                    self.append_log(f"[{email}] {line}", color=info)
                if "[FOUND]" in line:
                    found_flag["hit"] = True
        except Exception as e:
            self.append_log(f"[ERR] log reader: {e}", color=danger)
        finally:
            try:
                code = proc.poll()
            except Exception:
                code = None
            self.append_log(f"[EXIT] node process finished with code {code}", color=warning)

    def _parallel_reader(self, proc, email):
        """يقرا لوج العملية ويوقف الكل لو لقط [FOUND]."""
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                line = line.rstrip("\n")
                if _is_important(line):
                    self.append_log(f"[{email}] {line}", color=info)
                if "[FOUND]" in line and not self.stop_all_event.is_set():
                    self.stop_all_event.set()
                    self.append_log(f"[HIT] {email} لقط مواعيد — إيقاف كل الحسابات الآن…", color=success)
                    try:
                        self.after(0, self.stop_all_parallel)
                    except Exception:
                        pass
        except Exception as e:
            self.append_log(f"[ERR] parallel log reader: {e}", color=danger)
        finally:
            try:
                code = proc.poll()
            except Exception:
                code = None
            self.append_log(f"[EXIT] node process finished for {email} with code {code}", color=warning)

    def _arm_countdown(self):
        try:
            self.start_with_timer_check.set('on')
            self.timer_armed = True
            self.timer_fired = False
            self.print_in_log('تم تفعيل البدء مع العدّاد', color=info)
        except Exception:
            pass

    def _on_timer_switch(self):
        """تشغيل/تعطيل زر التفعيل وإلغاء المؤقتات لو السويتش اتقفل."""
        is_on = (self.start_with_timer_check.get() == 'on')
        try:
            self.arm_countdown_btn.configure(state=('normal' if is_on else 'disabled'))
        except Exception:
            pass
        if not is_on:
            try:
                if self.start_delay is not None:
                    self.after_cancel(self.start_delay); self.start_delay = None
            except Exception:
                pass
        try:
            if self.countdown_job is not None:
                self.after_cancel(self.countdown_job); self.countdown_job = None
        except Exception:
            pass
        try:
            if self.watchdog_job is not None:
                self.after_cancel(self.watchdog_job); self.watchdog_job = None
        except Exception:
            pass
        self.timer_target_ts = None
        self.timer_armed = False
        the_timer_fired_backup = False
        self.timer_fired = False
        self.pending_action_ts = None
        try:
            self.countdown_label.configure(text=render_text('العدّاد: --:--:--'))
        except Exception:
            pass
        self.append_log("[TIMER] disabled (switch OFF) — will start immediately when you press Start", color=warning)

    def _compute_login_and_action(self):
        try:
            # Login time
            L_h = int(self.start_time_hour_entry.get() or 8)
            L_m = int(self.start_time_min_entry.get() or 59)
            L_s = int(self.start_time_sec_entry.get() or 50)
            # Action time
            A_h = int(self.action_time_hour_entry.get() or L_h)
            A_m = int(self.action_time_min_entry.get() or L_m)
            A_s = int(self.action_time_sec_entry.get() or L_s)
        except ValueError:
            L_h, L_m, L_s = 8, 58, 0
            A_h, A_m, A_s = 8, 59, 50

        now = datetime.now()
        login_dt  = now.replace(hour=L_h, minute=L_m, second=L_s, microsecond=0)
        action_dt = now.replace(hour=A_h, minute=A_m, second=A_s, microsecond=0)
        if login_dt <= now:  login_dt  += timedelta(days=1)
        if action_dt <= now: action_dt += timedelta(days=1)
        # الإجراء لازم يكون بعد اللوجين
        if action_dt <= login_dt:
            action_dt += timedelta(days=1)
        return login_dt, action_dt
    # 👆👆

    # مُشغّل موحّد يمنع التكرار
    def _on_countdown_fire(self):
        if not self.timer_armed or self.timer_fired:
            return
        # أوقفي المؤقّتات والحارس قبل البدء
        try:
            if self.countdown_job is not None:
                self.after_cancel(self.countdown_job)
                self.countdown_job = None
        except Exception:
            pass
        try:
            if self.start_delay is not None:
                self.after_cancel(self.start_delay)
                self.start_delay = None
        except Exception:
            pass
        try:
            if self.watchdog_job is not None:
                self.after_cancel(self.watchdog_job)
                self.watchdog_job = None
        except Exception:
            pass

        self.timer_fired = True
        self.timer_armed = False
        self.timer_target_ts = None

        self.append_log("[TIMER] reached target — starting now", color=success)
        # لو في حسابات محفوظة: ابدأ البالك (جدولة متوازية)
        if self.applicants:
            self.append_log("[TIMER] bulk mode: starting all accounts in parallel…", color=info)
            if self._prepare_bulk_queue() == 0:
                return 
            threading.Thread(target=self._par_scheduler, daemon=True).start()
            return
        # لو محددين وقت إجراء، شغّلي مع تمريره؛ غير كده ابدئي عادي
        if self.pending_action_ts:
            self._start_with_action_deadline(self.pending_action_ts)
        else:
            self.start_node()

    def _tick_countdown(self, _cd_ignored):
        """يحدّث النص المعروض بناءً على timestamp مطلق، ويطلق عند الصفر."""
        try:
            if not self.timer_target_ts:
                return
            rem = int(self.timer_target_ts - time.time())
            if rem < 0:
                rem = 0
            h = rem // 3600
            m = (rem % 3600) // 60
            s = rem % 60
            self.countdown_label.configure(text=render_text(f'العدّاد: {h:02d}:{m:02d}:{s:02d}'))
        except Exception:
            pass

        if self.timer_armed and not self.timer_fired and self.timer_target_ts is not None:
            if time.time() >= float(self.timer_target_ts):
                self._on_countdown_fire()
                return

        self.countdown_job = self.after(1000, self._tick_countdown, None)

    # --- الحارس (watchdog) ---
    def _watchdog_tick(self):
        """حارس مستقل: يتأكد إننا بدأنا عند أو بعد وقت الهدف حتى لو after فات."""
        try:
            if self.timer_armed and not self.timer_fired and self.timer_target_ts is not None:
                if time.time() >= float(self.timer_target_ts):
                    self.append_log("[WD] watchdog fired — forcing start", color=warning)
                    self._on_countdown_fire()
                    return
        except Exception:
            pass
        self.watchdog_job = self.after(250, self._watchdog_tick)  # أسرع شوية

    def _make_env_for(self, email, pwd, force_halt=False):
        office  = (self.office_id_option.get() or "").strip()
        pricing_ui = (self.visa_price_options.get() or "").strip()
        pricing = "Vip" if ("Vip" in pricing_ui or "3810" in pricing_ui) else "Standard"

        visa    = (self.visa_type_option.get() or "").strip()
        city    = (self.city_entry.get() or "").strip()
        trip    = (self.date_entry.get() or "").strip()
        days_ahead = (self.days_entry.get().strip() if hasattr(self, "days_entry") else "14")

        # NEW: RPS من الواجهة
        rps_raw = (self.rps_option.get().strip() if hasattr(self, "rps_option") else "2")
        try:
            rps_val = max(1, min(10, int(rps_raw)))  # سقف آمن 1..10
        except Exception:
            rps_val = 2

        AUTO_CHECK     = '1' if self.auto_check_var.get()   == 'on' else '0'
        AUTO_PROCEED   = '1' if self.auto_proceed_var.get() == 'on' else '0'
        BEEP_ON_FOUND  = '1' if self.beep_var.get()         == 'on' else '0'
        ALERT_ON_FOUND = '1' if self.alert_var.get()        == 'on' else '0'
        HALT_ON_FOUND  = '1' if (force_halt or self.halt_on_found_var.get() == 'on') else '0'

        env = os.environ.copy()
        env.update({
            "APP_EMAIL":    email,
            "APP_PASS":     pwd,
            "OFFICE_NAME":  office,
            "PRICING_NAME": pricing,
            "VISA_NAME":    visa,
            "CITY":         city,
            "TRIP_DATE":    trip,
            "DAYS_AHEAD":   days_ahead,
            "MAX_RPS":      str(rps_val),
            "HUNT_SECONDS":   os.environ.get("HUNT_SECONDS",   "25"),
            "MAX_CHECKS":     os.environ.get("MAX_CHECKS",     "60"),
          "BACKOFF_429_MS": os.environ.get("BACKOFF_429_MS", "3000"),

            "MAX_BURST":      os.environ.get("MAX_BURST",      "2"),
            "PRINT_429":      os.environ.get("PRINT_429",      "0"),
            "AUTO_CHECK":     AUTO_CHECK,
            "AUTO_PROCEED":   AUTO_PROCEED,
            "BEEP_ON_FOUND":  BEEP_ON_FOUND,
            "ALERT_ON_FOUND": ALERT_ON_FOUND,
            "HALT_ON_FOUND":  HALT_ON_FOUND,
            
        })
               # ========= Proxy preference =========
        # لو PROXY_SERVER متعرفة، استخدمها مباشرة (أولوية أعلى من rotate_proxy)
        if os.getenv("PROXY_SERVER"):
            server = os.getenv("PROXY_SERVER")
            if not server.startswith("http://"):
                server = "http://" + server
            env["PROXY_SERVER"] = server
            env["PROXY_USER"]   = os.getenv("PROXY_USER", "")
            env["PROXY_PASS"]   = os.getenv("PROXY_PASS", "")
        else:
            # لو مفيش PROXY_SERVER، جرّب rotate_proxy (بناءً على PROXY_HOST/PORT…)
            try:
                proxy_str = rotate_proxy(async_session=True)  # "socks5://user:pass@host:port"
            except Exception:
                proxy_str = None
            if proxy_str:
                env["PROXY_SERVER"] = proxy_str.split("@")[-1] if "@" in proxy_str else proxy_str
                if not env["PROXY_SERVER"].startswith("http://"):
                    env["PROXY_SERVER"] = "http://" + env["PROXY_SERVER"]
                env["PROXY_USER"]   = os.getenv("PROXY_USER", "")
                env["PROXY_PASS"]   = os.getenv("PROXY_PASS", "")


        return env

    def _get_single_email_from_textbox(self) -> str:
        """يرجع أول بريد صالح من صندوق الميلات متعدد الأسطر."""
        import re
        text = (self.username_entry.get("0.0", "end") or "").strip()
        m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return m.group(0) if m else ""

    def _start_with_action_deadline(self, action_ts: int):
        """نبدأ Node ونمرر له وقت الإجراء START_AT_TS."""
        email = self._get_single_email_from_textbox()
        pwd   = (self.password_entry.get() or "").strip()
        if not email or not pwd:
            self.append_log("[ERR] missing credentials — إلغاء بدء الدخول", color=danger)
            self.enbale_home_data()
            return

        if not os.path.isfile(SCRIPT):
            self.append_log(f"[ERR] visa-bot.js not found at: {SCRIPT}", color=danger)
            self.enbale_home_data()
            return

        env = self._make_env_for(email, pwd, force_halt=False)
        env["START_AT_TS"] = str(int(action_ts))  # <-- المهم

        # ======= إضافة: ملف لوج خفيف + CMD tail =======
        base_dir = os.path.dirname(SCRIPT)
        logs_dir_v1 = os.path.join(base_dir, "visa-bot", "light-logs")  # المسار الذي يستخدمه النود
        logs_dir_v2 = os.path.join(base_dir, "light-logs")              # المسار القديم

        for _p in (logs_dir_v1, logs_dir_v2):
            try:
                os.makedirs(_p, exist_ok=True)
            except Exception:
                pass

        safe_email = email.replace("@", "_at_").replace(":", "_").replace("\\", "_").replace("/", "_")
        light_log = os.path.join(logs_dir_v1, f"{safe_email}.log")
        env["EXTRA_LOG"] = light_log

        # افتحي CMD tail على ويندوز
        try:
            if os.name == "nt":
                title = f'VB-Monitor - {email}'
                CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                subprocess.Popen(
                    [
                        "cmd", "/c", "start", title,
                        "powershell", "-NoProfile", "-NoExit", "-Command",
                        (
                            f'$Host.UI.RawUI.WindowTitle="{title}"; '
                            f'Write-Host "Monitoring {safe_email}.log..."; '
                            f'Get-Content -Path "{light_log}" -Wait -Tail 50'
                        )
                    ],
                    creationflags=CREATE_NEW_CONSOLE,
                    cwd=os.path.dirname(SCRIPT) or None
                )
                self.append_log(f"[MON] opened CMD tail for {email}", color=info)
        except Exception:
            # fallback بسيط لو PowerShell مش متاح
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", f'VB-Monitor - {email}', "cmd", "/k", f'type \"{light_log}\"'],
                    creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010),
                    cwd=os.path.dirname(SCRIPT) or None
                )
            except Exception:
                pass

        # ==============================================

        self.append_log(f"[BOOT] login now, action at ts={env['START_AT_TS']}", color=info)
        try:
            self.node_proc = subprocess.Popen(
                [NODE, "--", SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=os.path.dirname(SCRIPT) or None,
                bufsize=1,
            )
            threading.Thread(target=self._pump_node_stdout, daemon=True).start()
        except Exception as e:
            self.append_log(f"[ERR] failed to start node: {e}", color=danger)
            self.enbale_home_data()

    def start_node(self):
        # تشغيل حساب واحد من إدخالات الصفحة الرئيسية (من غير START_AT_TS)
        email = self._get_single_email_from_textbox()
        pwd   = (self.password_entry.get() or "").strip()

        if not email or not pwd:
            self.append_log("[ERR] missing credentials (username/password) — not starting", color=danger)
            messagebox.showerror(title='خطأ', message='برجاء إدخال اسم المستخدم وكلمة المرور')
            self.select_frame_by_name('home')
            self.enbale_home_data()
            return

        if not os.path.isfile(SCRIPT):
            self.append_log(f"[ERR] visa-bot.js not found at: {SCRIPT}", color=danger)
            self.enbale_home_data()
            return

        env = self._make_env_for(email, pwd, force_halt=False)

        # ======= إضافة: ملف لوج خفيف + CMD tail =======
        base_dir = os.path.dirname(SCRIPT)
        logs_dir_v1 = os.path.join(base_dir, "visa-bot", "light-logs")
        logs_dir_v2 = os.path.join(base_dir, "light-logs")

        for _p in (logs_dir_v1, logs_dir_v2):
            try:
                os.makedirs(_p, exist_ok=True)
            except Exception:
                pass

        safe_email = email.replace("@", "_at_").replace(":", "_").replace("\\", "_").replace("/", "_")
        light_log = os.path.join(logs_dir_v1, f"{safe_email}.log")
        env["EXTRA_LOG"] = light_log

        # افتحي CMD tail على ويندوز
        try:
            if os.name == "nt":
                title = f'VB-Monitor - {email}'
                CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                subprocess.Popen(
                    [
                        "cmd", "/c", "start", title,
                        "powershell", "-NoProfile", "-NoExit", "-Command",
                        (
                            f'$Host.UI.RawUI.WindowTitle="{title}"; '
                            f'Write-Host "Monitoring {safe_email}.log..."; '
                            f'Get-Content -Path "{light_log}" -Wait -Tail 50'
                        )
                    ],
                    creationflags=CREATE_NEW_CONSOLE,
                    cwd=os.path.dirname(SCRIPT) or None
                )
                self.append_log(f"[MON] opened CMD tail for {email}", color=info)
        except Exception:
            # fallback بسيط لو PowerShell مش متاح
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", f'VB-Monitor - {email}', "cmd", "/k", f'type \"{light_log}\"'],
                    creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010),
                    cwd=os.path.dirname(SCRIPT) or None
                )
            except Exception:
                pass

        # ==============================================

        self.append_log(f"[BOOT] launching Node: {NODE} {SCRIPT}", color=info)
        try:
            self.node_proc = subprocess.Popen(
                [NODE, "--", SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=os.path.dirname(SCRIPT) or None
            )
            threading.Thread(target=self._pump_node_stdout, daemon=True).start()
        except Exception as e:
            self.append_log(f"[ERR] failed to start node: {e}", color=danger)
            self.enbale_home_data()

    def _run_node_once(self, email, pwd):
        """يشغّل Node لهذا الحساب ويعيد كود الخروج؛ 900 = تم العثور على مواعيد.
           اتّبع حالة سويتش 'إيقاف عند أوّل ميعاد' بدل الإجبار على الوقف.
        """
        if not os.path.isfile(SCRIPT):
            self.append_log(f"[ERR] visa-bot.js not found at: {SCRIPT}", color=danger)
            return -1

        force = (self.halt_on_found_var.get() == 'on')
        env = self._make_env_for(email, pwd, force_halt=force)

        # إعداد light log + فتح tail (كان ناقص في التسلسلي)
        base_dir = os.path.dirname(SCRIPT)
        logs_dir = os.path.join(base_dir, "visa-bot", "light-logs")
        try:
            os.makedirs(logs_dir, exist_ok=True)
        except Exception:
            pass
        safe_email = email.replace("@","_at_").replace(":","_").replace("\\","_").replace("/","_")
        light_log = os.path.join(logs_dir, f"{safe_email}.log")
        env["EXTRA_LOG"] = light_log

        try:
            if os.name == "nt":
                title = f'VB-Monitor - {email}'
                CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
                subprocess.Popen(
                    [
                        "cmd", "/c", "start", title,
                        "powershell", "-NoProfile", "-NoExit", "-Command",
                        (
                            f'$Host.UI.RawUI.WindowTitle="{title}"; '
                            f'Write-Host "Monitoring {os.path.basename(light_log)}..."; '
                            f'Get-Content -Path "{light_log}" -Wait -Tail 50'
                        )
                    ],
                    creationflags=CREATE_NEW_CONSOLE,
                    cwd=os.path.dirname(SCRIPT) or None
                )
                self.append_log(f"[MON] opened CMD tail for {email}", color=info)
        except Exception:
            pass

        self.append_log(f"[SEQ] ENV => HALT_ON_FOUND={env.get('HALT_ON_FOUND')} "
                        f"AUTO_CHECK={env.get('AUTO_CHECK')} AUTO_PROCEED={env.get('AUTO_PROCEED')}", color=info)

        try:
            proc = subprocess.Popen(
                [NODE, "--", SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=os.path.dirname(SCRIPT) or None,
                bufsize=1
            )

            found_flag = {"hit": False}

            t = threading.Thread(target=self._pump_proc_filtered,
                                 args=(proc, email, found_flag),
                                 daemon=True)
            t.start()
            code = proc.wait()
            return 900 if found_flag["hit"] else code

        except Exception as e:
            self.append_log(f"[ERR] failed to start node: {e}", color=danger)
            return -1

    def _start_one_for_parallel(self, email, pwd):
        """يشغّل Node لحساب واحد بالتوازي (بدون wait) ويرجّع الـproc."""
        if not os.path.isfile(SCRIPT):
            self.append_log(f"[ERR] visa-bot.js not found at: {SCRIPT}", color=danger)
            return None

        env = self._make_env_for(email, pwd, force_halt=(self.halt_on_found_var.get() == 'on'))
        if (self.timer_armed or self.timer_fired) and self.pending_action_ts:
            env["START_AT_TS"] = str(int(self.pending_action_ts))

        # لوج خفيف + tail زي start_node
        base_dir = os.path.dirname(SCRIPT)
        logs_dir = os.path.join(base_dir, "visa-bot", "light-logs")
        try:
            os.makedirs(logs_dir, exist_ok=True)
        except Exception:
            pass
        safe_email = email.replace("@","_at_").replace(":","_").replace("\\","_").replace("/","_")
        env["EXTRA_LOG"] = os.path.join(logs_dir, f"{safe_email}.log")

        try:
            proc = subprocess.Popen(
                [NODE, "--", SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=os.path.dirname(SCRIPT) or None, bufsize=1
            )
            threading.Thread(
                target=self._parallel_reader,
                args=(proc, email),
                daemon=True
            ).start()
            return proc
        except Exception as e:
            self.append_log(f"[ERR] failed to start node for {email}: {e}", color=danger)
            return None

    def start_sequential(self):
        if not self.applicants:
            messagebox.showerror(title='خطأ', message='أضف حسابات أولاً من التبويب: الحسابات')
            return
        self.select_frame_by_name('frame_5')
        self.append_log("[SEQ] بدء التشغيل المتسلسل لكل الحسابات…", color=info)
        threading.Thread(target=self._sequential_worker, daemon=True).start()

    def start_parallel(self):
        """يشغّل كل الحسابات باستخدام جدولة: حد أقصى متوازٍ، وكلما عملية تخلص نبدأ اللي بعدها من الطابور."""
        if not self.applicants:
            messagebox.showerror(title='خطأ', message='أضف حسابات أولاً من التبويب: الحسابات')
            return

        self.select_frame_by_name('frame_5')

        # مهم: ابدأ جولة جديدة
        try:
            self.stop_all_event.clear()
        except Exception:
            pass

        # جهّز الطابور (فلترة الحسابات الغلط + تجنّب المكررات شغّالة)
        self.pending_accounts.clear()
        for acc in list(self.applicants):
            email, pwd = acc.get_applicant_data()

            # فلترة الحسابات الناقصة بدل ما نطلق نود يخرج فورًا
            if not email or not pwd:
                self.append_log(f"[PAR] تخطّي حساب بدون بيانات مكتملة: {email or '[بدون بريد]'}", color=warning)
                continue

            # لو نفس الإيميل شغال بالفعل، نتخطّاه
            if email in self.workers and self.workers[email] and self.workers[email].poll() is None:
                self.append_log(f"[PAR] {email} يعمل بالفعل — تخطّي", color=warning)
                continue

            self.pending_accounts.append((email, pwd))

        if not self.pending_accounts:
            self.append_log("[PAR] لا يوجد ما يمكن تشغيله.", color=warning)
            return

        self.append_log(f"[PAR] جدولة {len(self.pending_accounts)} حسابًا. الحد المتوازي = {self.MAX_PAR}.", color=info)
        if self.start_with_timer_check.get() == 'on':
            login_dt, action_dt = self._compute_login_and_action()
            now = datetime.now()
            secs_to_login = max(0, int((login_dt - now).total_seconds()))
            self.pending_action_ts = int(action_dt.timestamp())  # مهم لحقن START_AT_TS لكل عملية

            # سلّح العدّاد + الحارس + شاشة العدّ التنازلي
            self.timer_target_ts = login_dt.timestamp()
            self.timer_armed = True
            self.timer_fired = False
            self.append_log(f"[PAR][TIMER] armed: login={login_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                            f"action={action_dt.strftime('%Y-%m-%d %H:%M:%S')}", color=info)
            try:
                if self.countdown_job is not None: self.after_cancel(self.countdown_job); self.countdown_job = None
                if self.start_delay is not None: self.after_cancel(self.start_delay); self.start_delay = None
                if self.watchdog_job is not None: self.after_cancel(self.watchdog_job); self.watchdog_job = None
            except Exception:
                pass

            # شغّل عدّاد العرض والحارس
            self._tick_countdown(None)
            self.watchdog_job = self.after(250, self._watchdog_tick)

            # عند لحظة اللوجين، نشغّل الـ Scheduler بدل التشغيل الفوري
            self.start_delay = self.after(
                secs_to_login * 1000,
                lambda: threading.Thread(target=self._par_scheduler, daemon=True).start()
            )
            # (مهم) ما نبدأش الـ Scheduler دلوقتي
            return

        # ابدأ ثريد الجدولة فورًا لو المؤقّت مغلق
        threading.Thread(target=self._par_scheduler, daemon=True).start()

    # ======= دوال المساعدة + الجدولــــة (نسخة واحدة فقط) =======
    def _count_live_workers(self):
        n = 0
        for p in list(self.workers.values()):
            try:
                if p and p.poll() is None:
                    n += 1
            except Exception:
                pass
        return n

    def _compact_workers(self):
        removed = 0
        for email, proc in list(self.workers.items()):
            try:
                if (proc is None) or (proc.poll() is not None):
                    self.workers.pop(email, None)
                    removed += 1
            except Exception:
                self.workers.pop(email, None)
                removed += 1
        if removed:
            self.append_log(f"[PAR] تنظيف: أزلنا {removed} عملية منتهية.", color=info)
    
    def _prepare_bulk_queue(self):
        """يملأ طابور التشغيل الجماعي من self.applicants مع بعض الفلاتر."""
        try:
            self.stop_all_event.clear()
        except Exception:
            pass

        self.pending_accounts.clear()
        seen = set()
        for acc in list(self.applicants):
            email, pwd = acc.get_applicant_data()

            if not email or not pwd:
                self.append_log(f"[PAR] تخطّي حساب بدون بيانات مكتملة: {email or '[بدون بريد]'}", color=warning)
                continue

            if email in seen:
                continue

            if email in self.workers and self.workers[email] and self.workers[email].poll() is None:
                self.append_log(f"[PAR] {email} يعمل بالفعل — تخطّي", color=warning)
                continue

            seen.add(email)
            self.pending_accounts.append((email, pwd))

        if not self.pending_accounts:
            self.append_log("[PAR] لا يوجد ما يمكن تشغيله.", color=warning)
        else:
            self.append_log(f"[PAR] جدولة {len(self.pending_accounts)} حسابًا.", color=info)

        return len(self.pending_accounts)

    def _par_scheduler(self):
        self.append_log("[PAR] Scheduler بدأ العمل…", color=info)
        try:
            while True:
                if self.stop_all_event.is_set():
                    self.append_log("[PAR] Scheduler توقّف بسبب إشارة الإيقاف.", color=warning)
                    break

                # نظّف العمليات المنتهية واحسب الحية
                self._compact_workers()
                live = self._count_live_workers()

                # لو لا طابور ولا عمليات حية — انتهى
                if not self.pending_accounts and live == 0:
                    self.append_log("[PAR] Scheduler انتهى: لا طابور ولا عمليات حية.", color=success)
                    break

                # افتح سعة للانطلاقات الجديدة
                slots = max(0, self.MAX_PAR - live)
                if slots <= 0:
                    time.sleep(0.15)
                    continue

                started_now = 0
                while slots > 0 and self.pending_accounts and not self.stop_all_event.is_set():
                    email, pwd = self.pending_accounts.popleft()

                    # لو الحساب شغّال بالفعل — تخطّي
                    if email in self.workers and self.workers[email] and self.workers[email].poll() is None:
                        self.append_log(f"[PAR] {email} يعمل بالفعل — تخطّي", color=warning)
                        continue

                    proc = self._start_one_for_parallel(email, pwd)
                    if proc:
                        self.workers[email] = proc
                        started_now += 1
                        slots -= 1
                        try:
                            time.sleep(self.STAGGER_MS / 1000.0)
                        except Exception:
                            pass
                    else:
                        self.append_log(f"[PAR] فشل إطلاق {email} — متابعة.", color=warning)

                if started_now:
                    self.append_log(
                        f"[PAR] Scheduler أطلق {started_now} عملية جديدة. "
                        f"حاليًا حية={self._count_live_workers()}, متبقٍ بالطابور={len(self.pending_accounts)}.",
                        color=info
                    )

                time.sleep(0.1)

        except Exception as e:
            self.append_log(f"[ERR] Scheduler exception: {e}", color=danger)
        finally:
            if self.stop_all_event.is_set():
                try:
                    self.master.protocol("WM_DELETE_WINDOW", self._on_close)
                except Exception:
                    pass


    def stop_all_parallel(self):
        """يوقف كل العمليات المتوازية (تُستدعى تلقائيًا عند أول FOUND أو يدويًا من الزر)."""
        if (not self.workers or all((p is None or p.poll() is not None) for p in self.workers.values())) and (not self.pending_accounts):
            self.append_log("[PAR] لا توجد عمليات متوازية قيد التشغيل.", color=warning)
            return

        self.append_log("[PAR] إيقاف كل العمليات…", color=warning)

        # علّم إننا في وضع الإيقاف
        try:
            self.stop_all_event.set()
        except Exception:
            pass

        # فضّي الطابور
        try:
            self.pending_accounts.clear()
        except Exception:
            pass

        # أوقف الجاري
        for email, proc in list(self.workers.items()):
            try:
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
                self.append_log(f"[PAR] أُوقِف {email}", color=warning)
            except Exception:
                pass
            finally:
                self.workers.pop(email, None)

        # رسالة ختامية
        if self.stop_all_event.is_set():
            self.append_log("[PAR] تم إيقاف الجميع بنجاح.", color=success)
        else:
            self.append_log("[PAR] تم الإيقاف.", color=info)

    def _sequential_worker(self):
        any_found = False
        for acc in list(self.applicants):
            email, pwd = acc.get_applicant_data()
            code = self._run_node_once(email, pwd)
            if code == 900:
                any_found = True
                self.append_log(f"[SEQ] تم العثور على مواعيد مع الحساب: {email} — إيقاف الباقي.", color=primary_hover)
                break
            try:
                time.sleep(0.2)
            except Exception:
                pass

        if not any_found:
            self.append_log("[SEQ] انتهى المرور على كل الحسابات بدون لقط مواعيد.", color=warning)
        self.append_log("[SEQ] انتهى المرور على كل الحسابات.", color=info)

    def stop_node(self):
        if self.node_proc and self.node_proc.poll() is None:
            self.append_log("[STOP] terminating node…", color=warning)
            try:
                self.node_proc.terminate()
                self.node_proc.wait(timeout=3)
            except Exception:
                try:
                    self.node_proc.kill()
                except Exception:
                    pass
            finally:
                self.append_log("[STOP] node stopped", color=warning)
                self.node_proc = None

    # =================== UI helpers / actions ===================

    def select_frame_by_name(self, name):
        self.home_button.configure(fg_color=('gray75', 'gray25') if name == 'home' else 'transparent')
        self.accounts_button.configure(fg_color=('gray75', 'gray25') if name == 'frame_4' else 'transparent')
        self.logs_button.configure(fg_color=('gray75', 'gray25') if name == 'frame_5' else 'transparent')

        if name == 'home':
            self.home_frame.grid(row=0, column=1, sticky='nsew')
        else:
            self.home_frame.grid_forget()
        if name == 'frame_4':
            self.fourth_frame.grid(row=0, column=1, sticky='nsew')
        else:
            self.fourth_frame.grid_forget()
        if name == 'frame_5':
            self.fifth_frame.grid(row=0, column=1, sticky='nsew')
        else:
            self.fifth_frame.grid_forget()

    def add_applicant(self, account_name, account_password):
        # دعم لستة إيميلات مرة واحدة (سطر/فواصل/سيمي كولون/مسافات)
        if not account_name or not account_password:
            messagebox.showerror(title='خطأ', message='برجاء إدخال المستخدم وكلمة المرور')
            return
        import re
        raw = account_name.strip()
        pwd = account_password.strip()
        candidates = re.split(r'[\s,;]+', raw)
        emails = [c.strip() for c in candidates if c.strip() and "@" in c]

        if not emails:
            messagebox.showerror(title='خطأ', message='لم يتم العثور على أي بريد إلكتروني صالح')
            return

        existing = {acc.name for acc in self.applicants}
        added = 0
        for email in emails:
            if email in existing:
                self.print_in_log(f'تخطّي {email} (مضاف سابقًا)', color=warning)
                continue
            account = AccountFrame(email, pwd, False, self.fourth_frame)
            account.grid(row=len(self.applicants) + 3, column=0, sticky='nsew', padx=5, pady=5)
            self.applicants.append(account)
            existing.add(email)
            added += 1

        if added:
            self.print_in_log(f'تم حفظ {added} حساب/حسابات بنجاح', color=info)
        else:
            self.print_in_log('لا حسابات جديدة لإضافتها', color=warning)

        # لا تمسح الميلات من الواجهة بعد الإضافة (عشان تراجعها براحتك)
        # self.username_entry.delete("0.0", "end")
        if self.save_password_check.get() == 'off':
            self.password_entry.delete(0, 'end')
        self.username_entry.focus()
        self.select_frame_by_name('frame_4')

    def print_in_log(self, text, color=info, url=''):
        current_time = datetime.now().strftime('%H:%M:%S')
        label = CTkLabel(self.fifth_frame, text=render_text(f'[{current_time}] - {text}'),
                         text_color=color, font=CTkFont(size=14, weight='bold'))
        if self.count > 500 and self.labels:
            self.labels[0].destroy()
            self.labels.pop(0)
        label.grid(row=self.count, column=0, sticky='e', padx=0, pady=0)
        self.count += 1
        self.labels.append(label)
        if url:
            label.configure(cursor='hand2')
            label.bind('<Button-1>', lambda e: webbrowser.open(url))
        try:
            self.fifth_frame.after(10, self._logs_autoscroll_if_needed)
        except Exception:
            pass

    def disable_home_data(self):
        for child in self.home_frame.winfo_children():
            if isinstance(child, (CTkEntry, CTkTextbox, CTkButton, CTkSwitch, CTkCheckBox, CTkOptionMenu)):
                try:
                    child.configure(state='disabled')
                except Exception:
                    pass
        self.home_disable_btn.configure(state='normal')

    def enbale_home_data(self):
        for child in self.home_frame.winfo_children():
           if isinstance(child, (CTkEntry, CTkTextbox, CTkButton, CTkSwitch, CTkCheckBox, CTkOptionMenu)):
                try:
                    child.configure(state='normal')
                except Exception:
                    pass
        self.home_disable_btn.configure(state='disabled')

    def stop_execution(self):
        # ألغِ المؤقّتات
        try:
            if self.start_delay is not None:
                self.after_cancel(self.start_delay)
                self.start_delay = None
        except Exception:
            pass
        try:
            if self.countdown_job is not None:
                self.after_cancel(self.countdown_job)
                self.countdown_job = None
        except Exception:
            pass
        try:
            if self.watchdog_job is not None:
                self.after_cancel(self.watchdog_job)
                self.watchdog_job = None
        except Exception:
            pass
        self.timer_target_ts = None
        self.timer_armed = False
        self.timer_fired = False
        self.pending_action_ts = None

        # إيقاف النود
        self.stop_node()
        self.print_in_log('تم ايقاف البرنامج', color=warning)
        self.enbale_home_data()
        try:
            self.countdown_label.configure(text=render_text('العدّاد: --:--:--'))
        except Exception:
            pass
    def _on_close(self):
        try:
            self.stop_all_parallel()
        except Exception:
            pass
        try:
            self.stop_node()
        except Exception:
            pass
        try:
            self.master.destroy()
        except Exception:
            pass
        try:
            self.stop_all_parallel()
        except Exception:
            pass

    def start_execution(self):
        emails_text = (self.username_entry.get("0.0", "end") or "").strip()
        pwd = (self.password_entry.get() or "").strip()

        if not self.applicants and not (emails_text and pwd):
            messagebox.showerror(title='خطأ', message='برجاء إدخال اسم المستخدم وكلمة المرور')
            self.select_frame_by_name('home')
            return

    # اجمع الإيميلات من الصندوق لو لسه مااتعملتش Add
        if not self.applicants and emails_text and pwd:
            import re
            for e in [x.strip() for x in re.split(r'[\s,;]+', emails_text) if x.strip() and "@" in x]:
                acc = AccountFrame(e, pwd, False, self.fourth_frame)
                acc.grid(row=len(self.applicants) + 3, column=0, sticky='nsew', padx=5, pady=5)
                self.applicants.append(acc)

        self.disable_home_data()
        self.select_frame_by_name('frame_5')

        if self.start_with_timer_check.get() == 'on':
            login_dt, action_dt = self._compute_login_and_action()
            now = datetime.now()
            secs_to_login = max(0, int((login_dt - now).total_seconds()))
            self.pending_action_ts = int(action_dt.timestamp())  # مهم علشان نحقن START_AT_TS لكل عملية

        # تسليح العدّاد + الحارس
            self.timer_target_ts = login_dt.timestamp()
            self.timer_armed = True
            self.timer_fired = False
            self.append_log(
                f"[TIMER] armed: target={login_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                f"action={action_dt.strftime('%Y-%m-%d %H:%M:%S')}", color=info
        )

        # عدّاد مرئي + one-shot + watchdog
            try:
                if self.countdown_job is not None: self.after_cancel(self.countdown_job)
                if self.start_delay  is not None: self.after_cancel(self.start_delay)
                if self.watchdog_job is not None: self.after_cancel(self.watchdog_job)
            except Exception:
                pass

            self._tick_countdown(None)
            self.start_delay = self.after(secs_to_login * 1000, self._on_countdown_fire)
            self.watchdog_job = self.after(250, self._watchdog_tick)

        # ملاحظة: عند لحظة الإطلاق `self._on_countdown_fire()` هتبدأ
        #       كل الإيميلات في وضع البالك تلقائيًا (موجودة عندك بالفعل).
            return

    # ======= المؤقّت مغلق: نبدأ فورًا =======
    # لو عندك حسابات محفوظة — شغّل الكل بالبلاك
        if self.applicants:
            self.append_log("[BOOT] bulk mode (no timer) — starting all accounts now…", color=info)
            if self._prepare_bulk_queue() == 0:
                self.enbale_home_data()
                return
            threading.Thread(target=self._par_scheduler, daemon=True).start()
            return

    # لو مفيش غير بريد واحد (من غير قائمة حسابات) — شغّله زي المعتاد
        self.print_in_log('بدء فوري…', color=warning)
        self.append_log("[BOOT] launching WITHOUT timer", color=info)
        self.start_node()


    def right_click_event(self, event):
        try:
            clipboard_content = event.widget.clipboard_get().strip()
            event.widget.insert('insert', clipboard_content)
        except Exception:
            pass
        return 'break'


class AccountFrame(CTkFrame):
    def __init__(self, name, password, hidden=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.password = password
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform='column')
        self.account_name = CTkLabel(self, text=name, font=CTkFont(size=12))
        self.account_password = CTkLabel(self, text=password, font=CTkFont(size=12))
        self.account_name.grid(row=0, column=2, sticky='nsew', padx=25)
        self.account_password.grid(row=0, column=1, sticky='nsew', padx=25)
        if not hidden:
            self.delet_btn = CTkButton(self, text=render_text('حذف'),
                                       command=self.delete, font=CTkFont(size=12),
                                       fg_color=danger_btn, hover_color=danger_hover)
            self.delet_btn.grid(row=0, column=0, sticky='nsew', padx=50)

    def delete(self):
        self.master.master.master.master.applicants.remove(self)
        self.destroy()

    def get_applicant_data(self):
        return [self.name, self.password]
