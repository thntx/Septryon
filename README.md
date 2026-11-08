# Web Markdown Typer

A lightweight, serverless, distraction-free Markdown editor built for seamless auto-saving and instant deployment on **GitHub Pages**.

The editor uses the bundled XSF Didona 2.003 font, with XSF ligatures and kerning enabled.
The default text size is 3rem (48px at the standard browser setting), with compact heading
ratios and smaller syntax markers so the script remains readable on desktop and mobile.
Inline code inherits it; Markdown delimiters remain in a system monospace font so the
literal formatting syntax stays readable. Font checksums are in `fonts/manifest.json`.

### XSF Line Wrapping

Spaceless XSF text wraps at syllable boundaries without inserting spaces, hyphens,
soft hyphens or invisible characters into the document. Copying and saving retain
the original text. `xsf-syllables.js` runs locally and does not call a translator
or require the original Catalan words.

The segmenter uses XSF's explicit vowel nuclei (`a e i o u x`), semivowels
(`y w 6 2`), codas and Catalan complex onsets. Two written vowels remain a hiatus;
it does not guess a diphthong from Catalan spelling. Tonic `+`, quality accents,
gemination markers and punctuation stay attached. Word boundaries cannot be
recovered uniquely after spaces have been removed: this is conservative phonetic
resyllabification, not restoration of the original words or their morphology.

Every candidate break is checked against the font's actual composition rules:
CV-first then VC in KIB; left-to-right CV/VC in BKK and KTB. A syllable boundary
inside a ligature is suppressed, keeping adjacent syllables together. Minimes,
mode switches, double-space resets and numeral multipliers are also protected.

The rendered groups are ordinary inline spans with non-wrapping contents. CSS
allows wrapping between them while keeping shaping continuous across element
boundaries. This preserves kerning and persistent font modes, unlike `<wbr>` in
the tested browser. There is no text mutation or width-dependent reformatting.

References: [IEC syllabification](https://giec.iec.cat/textgramatica/codi/2.2),
[IEC vowels and glides](https://giec.iec.cat/textgramatica/codi/2.5),
[CSS shaping across element boundaries](https://www.w3.org/TR/css-text-3/#boundary-shaping).

Run the dependency-free unit tests with `node --test xsf-syllables.test.cjs`.
The parent XSF workspace also keeps `vectors/check_typer_syllables.py` (real
HarfBuzz cluster checks) and `vectors/check_typer_wrapping.py` (browser layout,
font modes, editing, IME, selection, formatting, autosave and mobile checks).

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

---

## ✨ Features

- ⚡ **100% Serverless**: No Node.js backend required. Runs directly in any modern browser.
- 💾 **Real-Time Auto-Save (`localStorage`)**: Automatically saves your document to `localStorage` 500ms after you stop typing.
- 📁 **Direct Local File Auto-Save (File System Access API)**: Link your document to a local `.md` file on your computer and automatically save changes directly to your disk in real time.
- 🎨 **Live Markdown Formatting**: Real-time styling for headers (`#`), blockquotes (`>`), lists (`-`, `*`, `1.`), bold (`**`), italic (`*`), code (`` ` ``), and strikethrough (`~~`) without jumping caret position.
- 📊 **Live Document Statistics**: Real-time word and character counter in the header.
- ⬇️ **Import & Export**: Open existing `.md` files or download your notes anytime with a single click.
- 🌙 **Distraction-Free Dark Mode**: Clean, accessible, modern typography tuned for focused writing.

---

## 🚀 Live Demo

Access the live web application here:  
👉 **[https://thntx.github.io/web-markdown-typer/](https://thntx.github.io/web-markdown-typer/)**

---

## 💻 How It Works

### Auto-Saving Modes

1. **`localStorage` (Default)**:
   Every keystroke triggers a debounced (500ms) save to your browser's local storage. Your content persists across page reloads and browser sessions.

2. **Local File Link (File System Access API)**:
   Click **`💾 Vincular fitxer local` / `Link Local File`** to select or create a `.md` file on your computer. When linked, every auto-save automatically updates the file on your hard drive (supported in Chromium browsers: Chrome, Edge, Brave, Opera).

---

## 🛠️ Local Development & Deployment

### Running Locally
Since the application is purely static HTML, CSS, and JavaScript, you can open `index.html` directly in your browser or serve it using any static web server:

```bash
# Using python
python -m http.server 8000

# Or using npx
npx serve .
```

### Deploying to GitHub Pages

1. Push your changes to the `main` branch:
   ```bash
   git add .
   git commit -m "Update README and project documentation"
   git push origin main
   ```
2. In your GitHub repository settings, navigate to **Settings** > **Pages**.
3. Under **Build and deployment**, select `Deploy from a branch` and set the branch to `main` and path to `/ (root)`.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
