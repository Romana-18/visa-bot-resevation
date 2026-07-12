# GitHub Push Guide

## Your Project is Ready for GitHub!

All sensitive files are protected and example files are created.

## Quick Push Commands

```bash
# 1. Add all files (sensitive ones are automatically excluded)
git add -A

# 2. Check what will be committed
git status

# 3. Commit
git commit -m "Initial commit: Almaviva Visa Bot with web interface"

# 4. Create GitHub repo (on github.com)
# - Go to github.com
# - Click "New repository"
# - Name it: almaviva-visa-bot
# - Don't initialize with README (we have one)
# - Create repository

# 5. Add remote and push
git remote add origin https://github.com/YOUR-USERNAME/almaviva-visa-bot.git
git branch -M main
git push -u origin main
```

## What's Protected (Won't Be Pushed)

These files are in `.gitignore` and contain sensitive data:

- `config.json` - Has emails: naglaaelfakhrany@outlook.com, etc.
- `data/config.json` - Has password: Egypt123!
- `secretvars.py` - Has database credentials
- `cookies.txt` - Session data
- `open_id_config.json` - OAuth config
- All `.log` files
- `light-logs/` folder

## What Will Be Pushed (Safe)

- Source code (`.js`, `.mjs`, `.py` files)
- Web interface (`public/` folder)
- Documentation (`.md` files)
- Example files (`.example.*`)
- `package.json` and dependencies list
- `.gitignore` and `LICENSE`

## After Pushing

Users who clone your repo will need to:

1. Copy example files:
```bash
cp .env.example .env
cp config.example.json config.json
```

2. Edit with their own credentials

3. Install and run:
```bash
npm install
USE_CHROME=1 npm start
```

## Verify Before Pushing

Run this command to double-check:

```bash
git status
```

Should NOT see:
- config.json
- data/config.json  
- secretvars.py
- cookies.txt
- Any files with "Egypt123!" or email addresses

## Ready to Push?

If everything looks good, run:

```bash
git add -A
git commit -m "Initial commit: Almaviva Visa Bot"
# Then create GitHub repo and push
```
