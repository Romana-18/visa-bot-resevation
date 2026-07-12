# Proxy Setup Guide

## How to Use Proxy with the Bot

### Option 1: Via Web Interface (Recommended)
1. Open http://localhost:3000
2. Scroll down to "Proxy Settings (Optional)"
3. Fill in:
   - **Proxy Server**: `http://your-proxy.com:8080` or `socks5://your-proxy.com:1080`
   - **Proxy Username**: (if required)
   - **Proxy Password**: (if required)
4. Click "Start Bot"

### Option 2: Via Environment Variables
Set these before starting the server:

```bash
export PROXY_SERVER="http://proxy.example.com:8080"
export PROXY_USER="username"
export PROXY_PASS="password"
USE_CHROME=1 npm start
```

## Proxy Format Examples

### HTTP Proxy
```
http://proxy.example.com:8080
```

### HTTPS Proxy
```
https://proxy.example.com:8443
```

### SOCKS5 Proxy
```
socks5://proxy.example.com:1080
```

### With Authentication
```
http://username:password@proxy.example.com:8080
```

## Common Proxy Providers

### Bright Data (Luminati)
```
Server: http://brd.superproxy.io:22225
Username: your-username
Password: your-password
```

### Smartproxy
```
Server: http://gate.smartproxy.com:7000
Username: your-username
Password: your-password
```

### Oxylabs
```
Server: http://pr.oxylabs.io:7777
Username: your-username
Password: your-password
```

## Troubleshooting

### Proxy Not Working?
1. Check the proxy format (must start with `http://` or `socks5://`)
2. Verify credentials are correct
3. Test proxy with curl:
   ```bash
   curl -x http://proxy:port https://api.ipify.org
   ```
4. Check logs for proxy errors

### Logs Show "launching WITHOUT proxy"
- Make sure you filled in the Proxy Server field
- The field must not be empty
- Format must be correct (e.g., `http://proxy.com:8080`)

## All Logs Now Visible

The web interface now shows **ALL** logs from the bot, including:
- `[BOOT]` - Bot startup messages
- `[LOGIN]` - Authentication steps
- `[API]` - API requests and responses
- `[FOUND]` - Appointment slots found
- `[NONE]` - No slots available
- `[ACTION]` - Button clicks and actions
- `[HALT]` - Bot stopped
- `[EXIT]` - Process finished
- `[TIMER]` - Countdown events
- `[PRESS]` - Button press events
- `[WATCH]` - Monitoring events
- `[OK]` - Success messages
- `[WARN]` - Warnings
- `[ERR]` - Errors

Logs are color-coded:
- 🟢 Green = Success/Found
- 🔵 Blue = Info/Status
- 🟡 Yellow = Warning
- 🔴 Red = Error

Logs update every second and auto-scroll to the bottom.
