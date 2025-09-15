# Watashino LaTeX Bot

Watashino LaTeX Bot renders your LaTeX into crisp PNGs and vector PDFs right inside Discord. It supports slash commands, buttons, modals, and even rendering directly from chat messages.

### How to write direct latex code to bot's dm:

<p>
	<img alt="x^2" width="420" src="/assets/howtowritecodedirectlyinbotsdm.png" />
</p>

### How to write inline code if you prefer to:
<img alt="x^2 repeated" width="420" src="/assets/inlineExpressionsusage.png" />

### How your full document render will look like:
<img alt="x^2 repeated" width="420" src="/assets/renderedEquations.png" />

## Discord bot usage

A beautiful website demonstrating commands and usage is available at [this website](https://atrajit-sarkar.github.io/Watashino-Latex-Bot/) in the root folder. You can open it locally in your browser or host it anywhere.

Prerequisites:
- Python 3.9+
- Ghostscript installed and available on PATH (on Windows: gswin64c or gswin32c)
- A Discord bot token (create at https://discord.com/developers, invite with applications.commands scope)
- Optional: to render messages you just type in chat (like the original Telegram flow), enable the "Message Content Intent" in the Developer Portal and set `DISCORD_ENABLE_MESSAGE_CONTENT=true` in `.env`.

Setup:
1. Install dependencies

```
pip install -r requirements.txt
```

2. Configure environment via `.env`

Copy `.env.example` to `.env` and fill values:

```
copy .env.example .env
notepad .env
```

3. Run the bot

```
python main.py
```

Slash commands:
- `/start` — welcome and quick usage guide
- `/latex code:"$x^2$"` — render to PNG and PDF
- `/overleaf` — open a modal with a large code editor-style input to write LaTeX and render
- `/tex2html` — open a modal that converts LaTeX to an HTML website using TeX Live (htlatex); optional `format` choice (e.g., `html5`, `html5+mathjax`, `xhtml`, `odt`, `epub`)
- `/settings` — configure caption, DPI, and edit preamble
- `/sethtmlformat` — set your preferred HTML format for `/tex2html`
- `/setdpi 300` — set rendering DPI (100-1000)
- `/getmypreamble` — show your current preamble
- `/getdefaultpreamble` — show default preamble
- `/setcustompreamble` — open a modal to set your preamble

### Render by just typing in chat

Besides `/latex`, you can simply type LaTeX in DMs or in servers (if `DISCORD_ENABLE_MESSAGE_CONTENT=true`):

- Inline math: type `$x^2 + \alpha$`
- Display math: type `\[\int_0^1 x^2\,dx\]`
- Full documents: paste anything containing `\documentclass{...}`
- Code fences: use ```latex ... ``` and the bot will render the code inside

If you type LaTeX-like content without delimiters (e.g., `\frac{a}{b}`), the bot will auto-wrap it: single-line becomes inline `$...$`; multi-line or block-like becomes display `\[...\]`.

### Overleaf-like modal editor

Prefer a focused editor experience? Use `/overleaf`:

- Opens a modal with a large multi-line input for LaTeX
- Paste a full document (with `\documentclass`) or just an expression
- On submit, you’ll receive both PNG and PDF, same as `/latex`

### PDF margins and layout

- For standalone expressions (not full documents), the bot produces a tightly-cropped PDF with comfortable padding around the content.
	- Default padding is 24pt on each side. You can change it via environment variable `LATEXBOT_PDF_MARGIN_PT` (value in PostScript points; 72pt = 1 inch).
	- Example: set `LATEXBOT_PDF_MARGIN_PT=36` for 0.5 inch padding.
- If your input includes a full LaTeX document (`\documentclass{...}`), the bot preserves the document’s own page size and margins (no cropping applied), similar to Overleaf output.

### Convert LaTeX to an HTML website

Use `/tex2html` to generate a small website from your LaTeX:

- Opens a modal to paste a full document or just an expression
- Uses TeX Live’s TeX4ht tool (`htlatex`, or `make4ht` if available)
- Output format can be selected via the command option or environment variable `LATEXBOT_HTML_FORMAT` (default `html5`). Supported: `html5`, `html5+mathjax`, `xhtml`, `odt`, `epub`.
- Advanced users: pass extra `make4ht` arguments via the `make4ht_args` text option on `/tex2html`. Example: `-c config.cfg -d outdir`. Note: arguments are space-split and lightly sanitized.
- Returns a ZIP file; unzip and open `index.html`

Temporary previews (optional):

- The bot can also serve a temporary preview URL for your generated site, so you can click and view without downloading the ZIP.
- An internal aiohttp web server is started automatically on startup; if running, `/tex2html` replies will include a “Temporary preview” link that expires after a configured TTL (default 60 minutes).
- The preview is served from a tokenized URL like `http://HOST:PORT/site/<token>/` that maps to the conversion’s output directory.

Configure preview hosting via environment variables:

- `HTML_HOST` — bind address for the preview server (default `127.0.0.1`). Set `0.0.0.0` to listen on all interfaces.
- `HTML_PORT` — port for the preview server (default `8088`).
- `HTML_BASE_URL` — public base URL used in links (defaults to `http://{HTML_HOST}:{HTML_PORT}`). If you run behind a reverse proxy or tunnel, set this to the externally reachable URL.
- `HTML_TTL_SECONDS` — how long previews live before being cleaned up (default `3600`).

Notes:

- If `HTML_HOST` is left as `127.0.0.1`, the preview link will only work from the same machine the bot runs on. For remote access, bind to `0.0.0.0` and set `HTML_BASE_URL` to your public URL.
- The server cleans up expired preview directories automatically.

Additional prerequisites for this feature:
- TeX Live installed with TeX4ht components (`htlatex` or `make4ht`) available on PATH
 - For TikZ/graphics in HTML, `dvisvgm` must be available (we default to SVG output + hashed names)

## Customization
The main feature of the bot is the customizable preamble used in the document into which your expression will be inserted:
```latex

\documentclass{article}
\usepackage[T1]{fontenc}
...
%You can modify everything above this comment
\begin{document}
<your expression goes here>
\end{document}
```
This means you can include the packages that you need or define your own expressions and commands which will afterwards be available when rendering. The bot works with a standard LaTeX installation (TeX Live or MiKTeX) and Ghostscript.

Additionally, it is possible to change how the messages will look like after they've been sent, i.e. include the raw expression in the caption of the image or not, or set the resolution of the picture to control its size.

The customization applies both to slash commands and chat message rendering.

### Per-user HTML format preference

You can set your own default HTML output format used by `/tex2html`:

- Use `/sethtmlformat` to pick one of the supported formats
- Or open `/settings` and use the “Select HTML format (for /tex2html)” dropdown
- The slash command’s `format` option overrides the saved preference for a single run

## Notes
- Preamble length in the modal is limited to 4000 characters for safety.
- Rendering dependencies: `pdflatex` and Ghostscript must be available on PATH.
- For HTML conversion, TeX4ht tools (`make4ht` is preferred; falls back to `htlatex`) must be available on PATH. Use `/diagnose` to see what is detected.
 - Debugging TeX4ht: set `LATEXBOT_KEEP_HTML_TEMP=true` to keep temporary HTML build folders under `build/`.
 - We enable SVG output by default via `svg` + `dvisvgm_hashes` make4ht extensions. Ensure `dvisvgm` is on PATH; `/diagnose` now reports it.
 - TikZ/SVG images: the bot enables the `dvisvgm_hashes` extension automatically for HTML formats to produce safe SVG filenames and avoid broken image links. If your documents are heavy, you can increase the TeX4ht timeout with `LATEXBOT_HTML_TIMEOUT` (seconds).

## Assets
- Example images used above are located under `resources/test/`.
- You can replace or add your own examples and reference them in this README.
