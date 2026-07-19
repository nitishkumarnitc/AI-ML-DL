# 🚀 Quick Start: Push to GitHub

## ⚡ 3-Minute Setup

### Step 1: Get Your Token (2 minutes)
1. Open this URL: **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Name it: `AI-ML-DL Access`
4. Check: ✅ **repo** (this gives you push access)
5. Click **"Generate token"**
6. **COPY THE TOKEN** → Looks like: `ghp_ABC123...`

---

### Step 2: Push Your Code (1 minute)

**Option A: Use the Script (Easiest)**
```bash
cd "/Users/nitishkumar/Documents/IITK AI-ML"
./PUSH_TO_GITHUB.sh
```
When prompted, paste your token.

**Option B: Manual Commands**
```bash
cd "/Users/nitishkumar/Documents/IITK AI-ML"

# Stage and commit
git add .
git commit -m "Enhanced 4 DL notebooks"

# Push (will ask for credentials)
git push -u origin main
```

When prompted:
- **Username:** `nitishkumarnitc@gmail.com`
- **Password:** `<PASTE YOUR TOKEN>`

---

## ✅ Done!

Your enhanced notebooks are now on GitHub: 
**https://github.com/nitishkumarnitc/AI-ML-DL**

---

## 🔧 If It Doesn't Work

**Error: "branch main doesn't exist"**
```bash
git push -u origin master
```

**Error: "authentication failed"**
- Make sure you pasted the TOKEN (not your GitHub password)
- Token should start with `ghp_`
- Check token has `repo` permission

**Need help?**
- See full guide: `GITHUB_SETUP_GUIDE.md`
- Or just ask me! 😊

---

## 💡 After First Push

Git will remember your token! Next time just:
```bash
git add .
git commit -m "Your message"
git push
```

No token needed again! 🎉
