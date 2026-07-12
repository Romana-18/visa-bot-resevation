# Install Dependencies

Your Python packages are missing. Run these commands:

## Step 1: Install Python packages (one at a time)

```powershell
# Install each package separately (slower but more reliable)
pip install customtkinter
pip install playwright  
pip install requests
pip install python-bidi
```

## Step 2: Install Playwright browsers

```powershell
playwright install chromium
```

## Step 3: Test the bot

```powershell
# Test the time extraction logic
node test-time-extraction.mjs

# Run the GUI
python login_gui.py
```

## If pip is slow

Try using a faster mirror:

```powershell
pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple customtkinter
pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple playwright
pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple requests
pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple python-bidi
```

## What you need

- ✅ customtkinter - GUI framework
- ✅ playwright - Browser automation  
- ✅ requests - HTTP client
- ✅ python-bidi - Arabic text support

The `awesometkinter` package has dependency issues with your Python version, but it's optional - the bot will work without it (just without some Arabic text rendering features).
