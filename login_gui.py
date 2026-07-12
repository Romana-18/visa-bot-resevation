# login_gui.py — launcher بسيط لـ App2
import sys
import os
from customtkinter import CTk, set_appearance_mode, set_default_color_theme
try:
    import gui  # بيتوقع gui.py في نفس المجلد
except ImportError as e:
    print("ImportError:", e)
    raise

def main():
    set_appearance_mode("dark")
    set_default_color_theme("dark-blue")
    root = CTk()
    root.title("Almaviva — Hunt Mode")
    root.geometry("980x700")
    app = gui.App2(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    # تأكدي إنكي في نفس مجلد الملفات قبل التشغيل
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
