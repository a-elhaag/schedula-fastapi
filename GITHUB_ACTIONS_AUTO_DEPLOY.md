# 🚀 GitHub Actions Auto-Deploy Setup

**Complete auto-deployment workflow for GitHub Pages documentation**

---

## ✅ What's Already Set Up

The GitHub Actions workflow file is **already created and ready**:

```
.github/workflows/deploy-docs.yml
```

This workflow automatically:
- ✅ Builds documentation when you push to `main`
- ✅ Deploys to GitHub Pages instantly
- ✅ Runs on every push to `docs/` directory
- ✅ Zero manual steps needed

---

## 🔧 Enable GitHub Pages (One-Time Setup)

### Step 1: Go to Repository Settings

1. Navigate to your GitHub repository
2. Click **Settings** (top right)
3. Scroll down to **Pages** section (left sidebar)

### Step 2: Configure Pages

In the **Pages** section:

| Setting | Value |
|---------|-------|
| Source | `GitHub Actions` |
| Branch | `main` |
| Folder | `/ (root)` |

**Screenshot Path:**
```
Settings → Pages → Source → Select "GitHub Actions"
```

### Step 3: Save

Click **Save**

---

## 📤 Deploy Documentation

### First Push (Initial Deployment)

```bash
# Make sure you're in the project root
cd /Users/anas/Projects/schedula-fastapi

# Stage the documentation files
git add docs/
git add .github/workflows/deploy-docs.yml

# Commit
git commit -m "docs: Add GitHub Pages documentation with auto-deploy"

# Push to main
git push origin main
```

### What Happens Next

1. **Push Triggered** → GitHub Actions starts automatically
2. **Build Runs** → Python, mkdocs, builds HTML (30-60 seconds)
3. **Deploy** → Pushed to GitHub Pages (10-30 seconds)
4. **Live** → Site goes live at `https://your-org.github.io/schedula-fastapi/`

**Total time:** ~2 minutes until live

### Check Deployment Status

1. Go to your GitHub repository
2. Click **Actions** tab
3. Look for `Deploy Docs to GitHub Pages` workflow
4. Watch the status (yellow = running, green = success, red = failed)

---

## 📡 How the Workflow Works

### Trigger Events

The workflow runs automatically when:

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'docs/**'           # Any file in docs/
      - '.github/workflows/deploy-docs.yml'
```

**In plain English:** When you push to `main` branch and change files in `docs/` directory.

### Build Steps

```yaml
1. Checkout code from GitHub
2. Set up Python 3.12
3. Install mkdocs and dependencies
4. Build static site (docs/site/)
5. Upload as artifact
6. Deploy to GitHub Pages
```

### Duration

| Step | Time |
|------|------|
| Setup | 10s |
| Build | 20-30s |
| Deploy | 10-20s |
| **Total** | **~2 min** |

---

## 📝 Update Documentation

After initial setup, updating is **automatic**:

### Edit & Push Workflow

```bash
# 1. Edit documentation
nano docs/index.md

# 2. Stage changes
git add docs/

# 3. Commit
git commit -m "docs: Update API documentation"

# 4. Push
git push origin main

# 5. GitHub Actions automatically rebuilds and deploys
# → Check Actions tab to see progress
# → Site updates in ~2 minutes
```

**No manual build steps!** GitHub Actions handles everything.

---

## 🔍 Workflow File Details

### Location
```
.github/workflows/deploy-docs.yml
```

### Key Sections

#### Trigger (When to run)
```yaml
on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - '.github/workflows/deploy-docs.yml'
```

#### Environment Setup
```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.12'
```

#### Install Dependencies
```yaml
- name: Install dependencies
  run: |
    pip install mkdocs mkdocs-material pymdown-extensions
```

#### Build Documentation
```yaml
- name: Build docs
  run: |
    cd docs
    mkdocs build
```

#### Deploy to Pages
```yaml
- name: Deploy to GitHub Pages
  uses: actions/deploy-pages@v2
  if: github.ref == 'refs/heads/main'
```

---

## 🎯 Your First Deployment Checklist

- [ ] **Enable GitHub Pages**
  - Settings → Pages
  - Source: GitHub Actions
  - Save

- [ ] **Push to main**
  ```bash
  git add docs/ .github/workflows/deploy-docs.yml
  git commit -m "docs: Add GitHub Pages"
  git push origin main
  ```

- [ ] **Check Actions tab**
  - Watch workflow run
  - Confirm success (green checkmark)

- [ ] **Visit live site**
  - Wait 2 minutes
  - Go to `https://your-org.github.io/schedula-fastapi/`
  - Verify documentation displays

- [ ] **Share with team**
  - Send the link
  - Everyone can access

---

## 🚨 Troubleshooting

### Workflow Doesn't Run

**Problem:** Pushed to `main` but workflow didn't start

**Solutions:**
1. Check you're on `main` branch: `git branch`
2. Check you pushed docs files: `git log --oneline -5`
3. Go to repo → Actions → Check for errors
4. Verify GitHub Pages is enabled in Settings

### Build Fails

**Problem:** GitHub Actions shows red X

**Solutions:**
1. Click on workflow run to see error details
2. Common errors:
   - Missing mkdocs.yml (check `docs/mkdocs.yml` exists)
   - Missing index.md (check `docs/index.md` exists)
   - Python syntax error in markdown
3. Fix locally first:
   ```bash
   pip install mkdocs mkdocs-material
   cd docs
   mkdocs build
   ```

### Pages Not Updating

**Problem:** Site is live but changes don't appear

**Solutions:**
1. Verify workflow succeeded (green checkmark in Actions)
2. Hard refresh browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
3. Clear browser cache
4. Check if you're looking at the right URL
5. Wait full 2 minutes after push

### Wrong Site URL

**Problem:** Can't find the site at the right URL

**Solutions:**
1. URL should be: `https://your-org.github.io/schedula-fastapi/`
2. Check Settings → Pages for actual URL
3. Verify repository is public (private repos need specific setup)

---

## 📊 Monitor Deployments

### View All Deployments

1. Go to repository → **Actions** tab
2. Filter by workflow: **Deploy Docs to GitHub Pages**
3. See all past deployments

### Check Specific Deployment

1. Click on workflow run
2. See build logs
3. See deployment status
4. Share link with team

---

## 🎨 Advanced: Customize Deployment

### Change Build Command

If you need custom build steps, edit `.github/workflows/deploy-docs.yml`:

```yaml
- name: Build docs
  run: |
    cd docs
    mkdocs build -f custom-config.yml
```

### Add Notifications

Send Slack/email on deployment:

```yaml
- name: Notify Slack
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -d '{"text":"Docs deployed!"}'
```

### Custom Domain

After deployment, add custom domain:

1. Settings → Pages → Custom domain
2. Enter: `docs.schedula.dev`
3. GitHub automatically manages SSL

---

## 🔐 Permissions & Security

### Workflow Permissions

The workflow uses minimal permissions:

```yaml
permissions:
  contents: read         # Read repository content
  pages: write          # Write to GitHub Pages
  id-token: write       # For OIDC token
```

**Safe & secure!** No access to secrets or sensitive data.

### No Manual Intervention Needed

- GitHub Actions runs automatically
- No SSH keys needed
- No manual FTP uploads
- No server access required

---

## 📋 Full Workflow Overview

```
Your Push to main
        ↓
GitHub detects push to docs/
        ↓
Workflow Triggered (automatic)
        ↓
├─ Checkout repository
├─ Set up Python 3.12
├─ Install mkdocs + theme
├─ Build static HTML
├─ Upload artifact
└─ Deploy to GitHub Pages
        ↓
Site Updated (live in 2 min)
        ↓
Team sees latest docs
```

---

## ✨ Features Enabled by This Workflow

✅ **Automatic Deployments**
- No manual build steps
- No manual FTP uploads
- Fully automated pipeline

✅ **Version Control**
- Every deployment tracked in Actions tab
- Easy rollback if needed
- Clear deployment history

✅ **Always Up-to-Date**
- Push changes to main
- Automatically deployed
- Live in ~2 minutes

✅ **CI/CD Integration**
- Part of GitHub's Actions ecosystem
- Integrates with other workflows
- Professional DevOps practice

✅ **Zero Cost**
- Free for public repositories
- No build servers to maintain
- GitHub-hosted runners included

---

## 🎯 Next Steps

### Immediate (Now)
1. Enable GitHub Pages (Settings → Pages)
2. Push to main
3. Watch Actions tab

### Short Term (Today)
1. Verify site goes live
2. Share link with team
3. Get feedback

### Ongoing (Weekly)
1. Update docs as needed
2. Push changes to main
3. Automatic deployment happens
4. Team sees updates

---

## 📞 Support

### Check GitHub Actions Docs
- [GitHub Actions](https://docs.github.com/en/actions)
- [Deploy Pages Action](https://github.com/actions/deploy-pages)

### Check MkDocs Docs
- [MkDocs](https://www.mkdocs.org/)
- [Material Theme](https://squidfunk.github.io/mkdocs-material/)

### Troubleshoot Workflow
1. Go to repo → Actions
2. Click failed workflow
3. See detailed error logs
4. Fix issues locally
5. Re-push to main

---

## 🎉 You're Done!

Your documentation is now:

✅ Automatically built on every push
✅ Automatically deployed to GitHub Pages
✅ Live at `https://your-org.github.io/schedula-fastapi/`
✅ Updated automatically whenever you push
✅ Zero manual steps needed

Just push to main and everything happens automatically! 🚀

---

**Workflow File:** `.github/workflows/deploy-docs.yml`
**Status:** ✅ Active & Ready
**Deployment Time:** ~2 minutes
**Cost:** Free

**Next: Push to main and watch it deploy!**
