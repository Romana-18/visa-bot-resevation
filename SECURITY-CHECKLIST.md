# Security Checklist Before Pushing to GitHub

## Files That Should NEVER Be Committed

These files contain sensitive data and are in `.gitignore`:

- [ ] `config.json` - Contains emails and passwords
- [ ] `data/config.json` - Contains user credentials and proxy info
- [ ] `secretvars.py` - Contains database credentials
- [ ] `cookies.txt` - Contains session cookies
- [ ] `open_id_config.json` - OAuth configuration
- [ ] `watchdog.json` - Runtime data
- [ ] `data/queue.json` - User queue data
- [ ] `data/watchdog.json` - Monitoring data
- [ ] `.env` - Environment variables
- [ ] `light-logs/` - Contains email addresses in filenames
- [ ] `visa-bot/light-logs/` - Contains email addresses in filenames

## Files That SHOULD Be Committed

Example/template files (safe to commit):

- [x] `.env.example` - Template for environment variables
- [x] `config.example.json` - Template for config
- [x] `data/config.example.json` - Template for data config
- [x] `secretvars.example.py` - Template for secrets
- [x] `.gitignore` - Git ignore rules
- [x] `README.md` - Documentation
- [x] `LICENSE` - License file

## Pre-Push Checklist

Run these commands before pushing:

### 1. Verify .gitignore is working
```bash
git status
```
Should NOT show:
- config.json
- data/config.json
- secretvars.py
- cookies.txt
- Any .log files

### 2. Check for sensitive data in tracked files
```bash
git grep -i "password" -- ':!*.example.*' ':!*.md'
git grep -i "Egypt123"
git grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" -- ':!*.example.*' ':!*.md'
```

### 3. Verify example files exist
```bash
ls -la *.example.*
ls -la data/*.example.*
```

### 4. Test clean clone
```bash
cd /tmp
git clone <your-repo-url>
cd almaviva-visa-bot
npm install
# Should work without any config files
```

## What Users Need to Do After Cloning

1. Copy example files:
```bash
cp .env.example .env
cp config.example.json config.json
cp data/config.example.json data/config.json
cp secretvars.example.py secretvars.py
```

2. Edit files with their credentials

3. Start the bot

## Emergency: If You Accidentally Committed Secrets

### Remove from last commit (not pushed yet)
```bash
git reset HEAD~1
git add <only-safe-files>
git commit -m "Your message"
```

### Remove from history (already pushed)
```bash
# Use BFG Repo-Cleaner or git filter-branch
# Then force push (dangerous!)
# Better: Delete repo and recreate
```

### Rotate all credentials immediately
- Change all passwords
- Regenerate API keys
- Get new proxy credentials
- Update OAuth secrets

## Current Status

Run this to check:
```bash
echo "=== Sensitive files (should be gitignored) ==="
ls -la config.json data/config.json secretvars.py cookies.txt 2>/dev/null || echo "Good - files don't exist or are gitignored"

echo ""
echo "=== Git status (should not show sensitive files) ==="
git status --short

echo ""
echo "=== Example files (should exist) ==="
ls -la *.example.* data/*.example.* 2>/dev/null
```
