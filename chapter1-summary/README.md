# Chapters 1–8 + Appendix study page

`index.html` is a **self-contained** study page for chapters 1–8 and the appendix of `../C__MUL~2.PDF` (Miloš Ljumović, *C++ Multithreading Cookbook*, Packt 2014).

It contains:

- section-by-section summaries of chapters 1–8 (book pp. 7–380) and the appendix (book pp. 381–396);
- **46 figures** from the PDF, embedded as data URIs (2 + 12 + 3 + 0 + 1 + 1 + 4 + 4 + 19);
- **161 code/setup cards** — 160 code listings from the eight chapters plus one verbatim card holding the appendix's URLs, paths and switches;
- twenty-four browser demos, covering the full book from UI responsiveness through synchronisation, .NET threading, concurrent-design bugs, thread pools and remote threading to the appendix's setup recipes and compiler switches.

## View it

Open `index.html` directly, or serve the folder:

```bash
python3 -m http.server 8000 --bind 0.0.0.0 --directory chapter1-summary
```

## Rebuild

The page is generated from `template.html` plus text/images extracted from the PDF:

```bash
python3 -m venv ../.venv-doc
../.venv-doc/bin/pip install pymupdf pillow
../.venv-doc/bin/python build.py
```

`code_lines.json`, `code_ch2.json` … `code_ch8.json` and `code_app.json` cache the extracted Courier-font lines so the listing index ranges in `build.py` stay stable if PDF tooling changes.
