from datetime import datetime, timedelta
import math

class Countdown:
    def __init__(self, det_h=0, det_min=0, det_sec=0) -> None:
        # ثبّت كأعداد صحيحة
        self.det_h = int(det_h)
        self.det_min = int(det_min)
        self.det_sec = int(det_sec)

    def _target_time(self, now: datetime) -> datetime:
        """يبني توقيت الهدف لليوم أو لليوم التالي إذا كان فات."""
        target = now.replace(hour=self.det_h, minute=self.det_min, second=self.det_sec, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    def get_remaining_time(self):
        """
        يرجّع (hours, minutes, seconds) المتبقية بدقة،
        مع استخدام ceil لتفادي ضياع لحظة الصفر.
        """
        now = datetime.now()
        delta = self._target_time(now) - now
        total_secs = max(0, int(math.ceil(delta.total_seconds())))
        hours = total_secs // 3600
        minutes = (total_secs % 3600) // 60
        seconds = total_secs % 60
        return (hours, minutes, seconds)

    def time_to_start_program(self):
        """
        مللي ثانية متبقية (ceil) — لا ترجع قيم سالبة.
        """
        now = datetime.now()
        delta = self._target_time(now) - now
        return max(0, int(math.ceil(delta.total_seconds() * 1000)))

    def get_remaining_seconds(self):
        """
        ثوانٍ متبقية (ceil) — لا ترجع قيم سالبة.
        """
        now = datetime.now()
        delta = self._target_time(now) - now
        return max(0, int(math.ceil(delta.total_seconds())))

    def __repr__(self) -> str:
        # تمثيل موحّد HH:MM:SS
        return f'{self.det_h:02d}:{self.det_min:02d}:{self.det_sec:02d}'
