# Documentation Deployment Guide

## Quick Deploy Command

To deploy/redeploy the documentation to GitHub Pages:

```bash
cd /Users/yogendraraghuvanshi/Personal_Space/universal_bi/ubi-connector
python3 -m mkdocs gh-deploy
```

## Deployment Steps

1. **Build and Deploy:**
   ```bash
   python3 -m mkdocs gh-deploy
   ```

2. **With Custom Message:**
   ```bash
   python3 -m mkdocs gh-deploy --message "Your deployment message"
   ```

3. **Build Only (for testing):**
   ```bash
   python3 -m mkdocs build
   ```

4. **Serve Locally (for preview):**
   ```bash
   python3 -m mkdocs serve
   ```
   Then visit: http://127.0.0.1:8000

## What Happens During Deployment

1. Cleans the site directory
2. Builds documentation from `docs/` directory
3. Copies built site to `gh-pages` branch
4. Pushes to GitHub
5. Documentation becomes available at: https://setupranali.github.io/setupranali.github.io/

## When to Redeploy

- After making changes to documentation files in `docs/`
- After updating `mkdocs.yml` configuration
- After modifying `docs/stylesheets/extra.css`
- After adding/removing pages
- After updating theme settings

## Troubleshooting

If deployment fails:
1. Check git status: `git status`
2. Ensure you're on the correct branch: `git branch`
3. Verify mkdocs is installed: `python3 -m mkdocs --version`
4. Check for build errors: `python3 -m mkdocs build`

## Notes

- Deployment automatically commits to `gh-pages` branch
- No need to manually commit before deploying
- Changes appear on the live site within 1-2 minutes
- The `gh-pages` branch is automatically created/updated
