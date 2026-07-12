# Quick Start: Fix Appointment Times

## 🚀 3-Step Fix

### Step 1: Test the Logic (30 seconds)
```bash
node test-time-extraction.mjs
```

**Expected output:**
```
✅ Successfully extracted: 7/7
🎉 All tests passed!
```

### Step 2: Diagnose Your API (2 minutes)
```bash
# Windows PowerShell
$env:APP_EMAIL="your-email@example.com"
$env:APP_PASS="your-password"
node diagnose-slots-api.mjs

# Windows CMD
set APP_EMAIL=your-email@example.com
set APP_PASS=your-password
node diagnose-slots-api.mjs
```

**Look for:**
```
✅ FOUND 5 SLOTS!
[DEBUG] First slot structure: {
  "id": 123456,
  "startTime": "2025-01-15T09:00:00+02:00",  ← THIS IS THE KEY FIELD
  ...
}
```

### Step 3: Run Your Bot
```bash
python login_gui.py
```

**Look for in logs:**
```
[SLOTS] 2025-01-15: total=5 → 09:00, 09:30, 10:00, 10:30, 11:00
                                 ↑ TIMES SHOULD SHOW HERE
```

## ✅ Success Checklist

- [ ] Test script shows 7/7 passed
- [ ] Diagnostic shows slot structure with time field
- [ ] Bot logs show `[SLOTS]` with actual times (HH:MM format)
- [ ] Times are in correct timezone (Cairo)

## ❌ If Times Still Don't Show

### Problem: No times in `[SLOTS]` line

**Check logs for:**
```
[WARN] Found 5 slots but could not extract times!
[WARN] Sample slot: { ... }
```

**Solution:**
1. Look at the sample slot JSON
2. Find which field has the time (e.g., `"appointmentDateTime"`)
3. Open `--- visa-bot.js`
4. Find the `getTimeFromSlot` function (around line 865)
5. Add your field name at the top of `candidates` array:

```javascript
const candidates = [
  s.appointmentDateTime,  // ← ADD YOUR FIELD HERE
  s.startTime,
  s.start,
  // ... rest
];
```

### Problem: Times show wrong timezone

**Solution:**
In `--- visa-bot.js`, find `timeZone: "Africa/Cairo"` and change to your timezone:
```javascript
timeZone: "Europe/Rome"  // or "UTC", "Asia/Dubai", etc.
```

### Problem: Diagnostic script fails to login

**Check:**
- Email and password are correct
- Account is not locked
- No captcha is required
- Internet connection is stable

## 📚 Full Documentation

- `FIX-APPOINTMENT-TIMES.md` - Detailed guide
- `APPOINTMENT-TIME-FIX-SUMMARY.md` - Technical details
- `diagnose-slots-api.mjs` - Diagnostic tool
- `test-time-extraction.mjs` - Test tool

## 🆘 Still Need Help?

1. Run diagnostic: `node diagnose-slots-api.mjs`
2. Copy the output from `[DEBUG] First slot structure:`
3. Check if the time field is in the candidates list
4. Add it if missing

The code now has extensive logging - it will tell you exactly what's wrong!
