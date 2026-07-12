# Fix: Appointment Times Not Showing Correctly

## Problem
The bot is finding appointment slots but not displaying the actual times correctly. This happens because the Almaviva API response structure might be different than expected.

## Solution

### Step 1: Run the Diagnostic Script

First, let's see what the API actually returns:

```bash
# Windows (PowerShell)
$env:APP_EMAIL="your-email@example.com"
$env:APP_PASS="your-password"
node diagnose-slots-api.mjs

# Windows (CMD)
set APP_EMAIL=your-email@example.com
set APP_PASS=your-password
node diagnose-slots-api.mjs

# Linux/Mac
export APP_EMAIL="your-email@example.com"
export APP_PASS="your-password"
node diagnose-slots-api.mjs
```

### Step 2: Analyze the Output

The diagnostic script will show you:
1. ✅ The exact JSON structure of slot objects
2. 📋 All available fields in each slot
3. ⏰ Which fields contain time information
4. 📅 All available appointment times

Look for output like:
```json
{
  "id": 12345,
  "startTime": "2025-01-15T09:00:00Z",
  "endTime": "2025-01-15T09:30:00Z",
  "officeId": 1,
  ...
}
```

### Step 3: Update the Code

Based on what you find, the improved code in `--- visa-bot.js` will now:

1. **Log the actual slot structure** when slots are found
2. **Try multiple field names** in order:
   - `startTime` (most common)
   - `start`
   - `slotStartTime`
   - `time`
   - `dateTime`
   - `slotTime`
   - `from`
   - `startDate`
   - `appointmentTime`
   - Nested fields like `slot.startTime`

3. **Handle different time formats**:
   - ISO strings: `"2025-01-15T09:00:00Z"`
   - Time-only strings: `"09:00:00"` or `"09:00"`
   - Timestamps: `1705312800000`

4. **Use Cairo timezone** for correct time display

### Step 4: Common Issues & Fixes

#### Issue 1: Times show as "null" or empty
**Cause**: The field name is different than expected

**Fix**: Look at the diagnostic output and update the field order in `getTimeFromSlot()`:
```javascript
const candidates = [
  s.YOUR_ACTUAL_FIELD_NAME,  // Add this based on diagnostic
  s.startTime,
  s.start,
  // ... rest
];
```

#### Issue 2: Times show wrong timezone
**Cause**: Not using Cairo timezone

**Fix**: Already fixed in the updated code with:
```javascript
d.toLocaleTimeString("en-GB", { 
  timeZone: "Africa/Cairo", 
  hour: "2-digit", 
  minute: "2-digit",
  hour12: false 
});
```

#### Issue 3: Times show as full ISO strings
**Cause**: Not extracting just HH:MM

**Fix**: Already fixed with regex extraction:
```javascript
const timeMatch = v.match(/(\d{2}:\d{2}(?::\d{2})?)/);
if (timeMatch) return timeMatch[1].slice(0, 5); // Returns HH:MM
```

### Step 5: Test the Fix

Run your bot normally:
```bash
# From Python GUI
python login_gui.py

# Or directly with Node
node "--- visa-bot.js"
```

Look for these log messages:
```
[DEBUG] First slot structure: { ... }
[DEBUG] All slot keys: [ 'id', 'startTime', 'endTime', ... ]
[DEBUG] Trying to extract time from fields: [ ... ]
[SLOTS] 2025-01-15: total=5 → 09:00, 09:30, 10:00, 10:30, 11:00
```

### Step 6: If Still Not Working

If times still don't show:

1. Check the `[DEBUG]` logs in your output
2. Look for `[WARN] Could not extract time from slot:`
3. Copy the JSON structure shown
4. Update the `candidates` array in the code with the correct field name

## Example: Real Almaviva API Response

Based on typical visa booking systems, the response likely looks like:

```json
[
  {
    "id": 123456,
    "startTime": "2025-01-15T09:00:00+02:00",
    "endTime": "2025-01-15T09:30:00+02:00",
    "officeId": 1,
    "visaId": 3,
    "serviceLevelId": 1,
    "available": true,
    "capacity": 1
  },
  {
    "id": 123457,
    "startTime": "2025-01-15T09:30:00+02:00",
    "endTime": "2025-01-15T10:00:00+02:00",
    "officeId": 1,
    "visaId": 3,
    "serviceLevelId": 1,
    "available": true,
    "capacity": 1
  }
]
```

The key field is usually `startTime` with an ISO 8601 timestamp.

## Quick Reference: Time Field Names by System

Different booking systems use different field names:

| System Type | Common Field Names |
|------------|-------------------|
| Almaviva (likely) | `startTime`, `start`, `dateTime` |
| VFS Global | `slotTime`, `appointmentTime` |
| TLS Contact | `time`, `from`, `to` |
| BLS International | `slotStartTime`, `slotEndTime` |

## Need More Help?

If you're still having issues:

1. Run the diagnostic script
2. Copy the full output
3. Look for the `[DEBUG] First slot structure:` section
4. Share that JSON structure to get specific help

The updated code now has extensive logging to help diagnose exactly what the API returns!
