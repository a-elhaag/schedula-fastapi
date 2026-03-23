# Schedula Solver API - Documentation

This directory contains the complete API documentation for the Schedula Solver.

## Local Development

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Install dependencies
pip install mkdocs mkdocs-material pymdown-extensions

# Run local server
mkdocs serve
```

The documentation will be available at `http://localhost:8000`

### Build Static Site

```bash
mkdocs build
```

This generates a `site/` directory with the static HTML.

## Deployment

Documentation is automatically deployed to GitHub Pages when you push to `main`.

The workflow:
1. Push changes to `docs/` directory
2. GitHub Actions builds the documentation
3. Site is deployed to GitHub Pages automatically

**Access the live site:** `https://your-org.github.io/schedula-fastapi/`

## File Structure

```
docs/
├── index.md              # Main page with tabs
├── mkdocs.yml           # MkDocs configuration
├── README.md            # This file
├── css/
│   └── custom.css       # Custom styles (optional)
└── assets/
    └── ...              # Images, diagrams, etc.
```

## Content Files

- `index.md` - Main documentation with tabs for different use cases

## Customization

### Change Theme Colors
Edit `mkdocs.yml`:
```yaml
theme:
  palette:
    primary: blue
    accent: blue
```

### Add More Pages
1. Create new `.md` file in `docs/`
2. Add to `nav` section in `mkdocs.yml`

### Custom CSS
Create `docs/css/custom.css` and reference in `mkdocs.yml`:
```yaml
extra_css:
  - css/custom.css
```

## Building for Production

```bash
# Install build tools
pip install mkdocs mkdocs-material

# Build static site
mkdocs build

# Site is ready in docs/site/
# Deploy to any static host (GitHub Pages, Netlify, etc.)
```

## Live Site

Once deployed:
- **Main:** `https://your-org.github.io/schedula-fastapi/`
- **Tabs:** Top navigation shows Setup, Integration, API Reference, etc.
- **Search:** Built-in search across all documentation
- **Mobile:** Fully responsive design

## Support

- **MkDocs Docs:** https://www.mkdocs.org/
- **Material Theme:** https://squidfunk.github.io/mkdocs-material/
- **GitHub Pages:** https://pages.github.com/

---

**Version:** 0.1.0
**Last Updated:** 2026-03-23
