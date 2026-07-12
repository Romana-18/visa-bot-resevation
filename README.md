# Almaviva Visa Bot

A sophisticated visa appointment hunting bot for the Almaviva visa booking system. Features a modern web interface, proxy support, and intelligent rate limiting.

## Features

- Modern Web Interface - Clean dashboard with real-time monitoring
- Smart Rate Limiting - Configurable requests per second (2-10 RPS)
- Proxy Support - HTTP/HTTPS/SOCKS5 proxies with authentication
- Auto-Click - Automatic "Check" and "Proceed" button clicking
- Live Logs - Real-time color-coded log streaming
- Alerts - Beep and visual alerts when slots are found
- Multi-Office - Support for Cairo and Alexandria offices
- Pricing Options - Standard and VIP service levels
- Multiple Visa Types - Employment, Family Reunion, Tourism, Study, etc.
- Chrome Support - Use your installed Chrome or Playwright's Chromium

## Prerequisites

- Node.js 16+ 
- Python 3.8+ (for legacy GUI only)
- Chrome or Chromium browser

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/almaviva-visa-bot.git
cd almaviva-visa-bot
```

### 2. Install Node.js dependencies

```bash
npm install
```

### 3. Install Playwright browsers (if not using Chrome)

```bash
npx playwright install chromium
```

## Usage

### Web Interface (Recommended)

**1. Start the server:**

```bash
# Use your installed Chrome
USE_CHROME=1 npm start

# Or use Playwright's Chromium
npm start
```

**2. Open your browser:**

Navigate to: http://localhost:3000

**3. Configure the bot:**

- Enter your Almaviva credentials
- Select office, visa type, and preferences
- (Optional) Configure proxy settings
- Click "Start Bot"

**4. Monitor logs:**

Switch to the "Live Logs" tab to see real-time updates

### Python GUI (Legacy)

```bash
python3 login_gui.py
```

## Configuration

### Proxy Setup

The bot supports HTTP, HTTPS, and SOCKS5 proxies with optional authentication.

**In the web interface:**

```
Proxy Server: http://proxy.example.com:8080
Proxy Username: your-username (optional)
Proxy Password: your-password (optional)
```

**Recommended proxy providers:**
- [Bright Data](https://brightdata.com) - Residential proxies
- [Smartproxy](https://smartproxy.com) - Easy setup
- [Webshare](https://webshare.io) - Budget-friendly

See [PROXY-SETUP.md](PROXY-SETUP.md) for detailed instructions.

### Environment Variables

You can set these before starting the server:

```bash
export USE_CHROME=1              # Use installed Chrome instead of Chromium
export PROXY_SERVER="http://..."  # Default proxy server
export PROXY_USER="username"      # Default proxy username
export PROXY_PASS="password"      # Default proxy password
```

## Project Structure

```
almaviva-visa-bot/
├── server.mjs              # Express web server
├── visa-bot.js             # Main bot logic (Playwright)
├── public/                 # Web interface
│   ├── index.html          # Dashboard UI
│   ├── app.js              # Frontend JavaScript
│   └── style.css           # Styles
├── gui.py                  # Python GUI (legacy)
├── login_gui.py            # Python login interface
├── authenticator.py        # OAuth2/PKCE authentication
├── ai_guard.mjs            # AI-powered rate limiting
└── package.json            # Node.js dependencies
```

## Available Visa Types

- Employment Visa (D)
- Family Reunion Visa - Spouses (D)
- Family Reunion Visa - Children (D)
- Family Reunion Visa - Parents (D)
- Study Visa (D)
- Study Visa (C)
- Tourism Visa (C)
- Business Visa (C)
- Re-entry Visa (D)

## Troubleshooting

### Browser not found

```bash
npx playwright install chromium
```

Or use your installed Chrome:

```bash
USE_CHROME=1 npm start
```

### Proxy connection failed

- Verify proxy format: `http://ip:port`
- Check username/password are correct
- Try a different proxy from your provider
- Test without proxy first to isolate the issue

### No logs appearing

- Check the "Live Logs" tab
- Logs update every second
- All events are now visible (not filtered)

## Security Notes

**Never commit sensitive data:**
- Credentials are entered via web interface (not stored)
- Use `.env` files for default settings (gitignored)
- Proxy credentials are passed at runtime
- All sensitive files are in `.gitignore`

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This bot is for educational purposes. Use responsibly and in accordance with Almaviva's terms of service. The authors are not responsible for any misuse or violations.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- See [PROXY-SETUP.md](PROXY-SETUP.md) for proxy help

## Changelog

### v2.0.0 (Current)
- New web interface replacing Python GUI
- Proxy support with authentication
- Real-time log streaming
- Chrome browser support
- Modern dashboard design

### v1.0.0
- Initial release with Python GUI
- Basic appointment hunting
- Multi-account support
