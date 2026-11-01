# Contributing to Awesome Blender

Contributions are always welcome! Before opening a pull request, please review the guidelines below to keep **Awesome Blender** high-signal, well-organized, and easy to maintain.

---

## 🎯 Scope & Quality Standards

The purpose of this list is to curate the best add-ons, extensions, standalone tools, tutorials, and resources for **Blender** artists, hobbyists, developers, and researchers—with a strong focus on **open-source and free** tools.

### ✅ What We Accept

- **Open-source and free resources** that are actively maintained and compatible with modern Blender releases (**Blender 3.6 LTS / 4.x+**).
- **Official or community-verified extensions** listed on the [Blender Extensions Platform](https://extensions.blender.org/) or well-documented repositories with real releases and community adoption.
- **Paid add-ons or tools (`[$]`)** _only_ if they are widely recognized across the Blender/3D community or solve a major workflow problem with no comparable open-source alternative in the list.

### 🚫 What We Do Not Accept

1. **Day-0 or untested repositories:** Brand-new projects without releases, documentation, real-world testing, community adoption, or an approved [Blender Extensions](https://extensions.blender.org/) listing.
2. **Promotional / SaaS / SEO spam:** Generic web services, AI wrappers without a dedicated Blender integration, affiliate/referral links, or paid services submitted primarily for backlinks.
3. **Obsolete or abandoned tools:** Legacy Blender 2.79 / early 2.80 scripts that no longer work on modern Blender versions.
4. **Trivial single-operator scripts:** Minor one-off scripts or paid micro-assets that do not offer broad utility.

---

## 📐 Formatting & Style Rules

### 1. General Entry Format

Every entry must be a single line starting with a capital letter in its description—**do not** start descriptions with filler phrases like `is a...`, `is an...`, or `this add-on...`, and avoid marketing buzzwords (`"revolutionary"`, `"ultimate"`, `"best"`):

```markdown
- [Tool Name](https://example.com) : Concise, neutral description starting with a capital letter.
```

### 2. Copy-Paste Templates (Badges & Symbols)

Always use the exact reference badge syntax (`[![][repo]](url)`, `[![market]](url)`, `![][gpl]`, `![][mit]`, `![][zero]`) at the end of the line:

```markdown
# Open-source add-on (Website + GitHub Repo + License):
- [Tool Name](https://example.com) : Concise description starting with a capital letter. [![][repo]](https://github.com/user/repo) ![][gpl]

# Open-source add-on (Direct GitHub Repo + License):
- [Tool Name](https://github.com/user/repo) : Concise description starting with a capital letter. ![][mit]

# Paid add-on (with Superhive / Blender Market link):
- [Tool Name](https://gumroad.com/l/example) [$] : Concise description starting with a capital letter. [![market]](https://superhivemarket.com/products/example)

# Free CC0 resource:
- [Resource Name](https://example.com) : Concise description starting with a capital letter. [![][zero]](https://example.com/license)
```

### 3. Tutorials Format

Prefix tutorial links with the appropriate symbol (`▷` video, `☰` playlist, `☷` channel, `🧾` documentation) and avoid hardcoding Blender version numbers unless the tutorial is version-specific:

```markdown
- ▷[Tutorial Title by Creator.](https://www.youtube.com/watch?v=example)
- ☰[Playlist Title by Creator.](https://www.youtube.com/playlist?list=example)
```

---

## 🔄 Pull Request Checklist

- **One resource per PR:** Submit a separate pull request for each resource so it can be reviewed independently.
- **Edit `README.md` only:** Do **not** edit [`README_ZH.md`](README_ZH.md) in your pull request; translations are synchronized automatically by maintainers.
- **4-space indentation:** Use 4 spaces for nested sub-lists.
- **Verify links & formatting:** Every PR is automatically checked by **Prettier** (`npx prettier . --check`) and **Lychee** (broken-link checker). Ensure all URLs return `200 OK` without unnecessary tracking parameters.

---

## 📄 License

By contributing to **Awesome Blender**, you agree that your contributions will be licensed under [**CC0 1.0 Universal**](LICENSE).
