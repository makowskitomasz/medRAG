#!/usr/bin/env python3
"""
Convert inline TikZ figures in thesis chapters to external PNG files.

For each \begin{figure}...\end{figure} block that contains a tikzpicture:
  1. Extracts the label and TikZ content
  2. Compiles as a standalone PDF
  3. Converts to PNG at 300 dpi
  4. Replaces the inline TikZ with \includegraphics in the chapter file

Usage:
    cd thesis-latex && uv run python ../scripts/tikz_to_png.py
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

THESIS = Path(__file__).parent.parent / "thesis-latex"
FIGURES = THESIS / "figures"
FIGURES.mkdir(exist_ok=True)

CHAPTERS = [
    THESIS / "chapters" / "ch2_background.tex",
    THESIS / "chapters" / "ch3_rare_rag.tex",
    THESIS / "chapters" / "ch4_system_design.tex",
]

PREAMBLE = r"""\documentclass[border=8pt]{standalone}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usetikzlibrary{
  arrows.meta, positioning, shapes.geometric, shapes.misc,
  fit, backgrounds, decorations.pathreplacing, calc, trees, mindmap
}
\setlength{\textwidth}{14cm}
\setlength{\linewidth}{14cm}
\newcommand{\rarerag}{\textsc{rare-rag}}
\newcommand{\medrag}{\textit{medRAG}}
\begin{document}
"""

POSTAMBLE = "\n\\end{document}\n"


def extract_figures(text: str) -> list[dict]:
    """Extract all figure environments containing tikzpicture."""
    figures = []
    i = 0
    while i < len(text):
        start = text.find(r"\begin{figure}", i)
        if start == -1:
            break
        end = text.find(r"\end{figure}", start)
        if end == -1:
            break
        end += len(r"\end{figure}")
        block = text[start:end]

        # only process figures that contain tikzpicture
        if r"\begin{tikzpicture}" not in block:
            i = end
            continue

        # extract label
        label_match = re.search(r"\\label\{([^}]+)\}", block)
        label = label_match.group(1) if label_match else None

        # extract caption
        caption_match = re.search(r"\\caption\{(.+?)(?=\\label|\\end\{figure\})", block, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else ""

        # extract the figure options (htbp, p, etc.)
        options_match = re.search(r"\\begin\{figure\}\[([^\]]*)\]", block)
        options = options_match.group(1) if options_match else "htbp"

        figures.append(
            {
                "start": start,
                "end": end,
                "block": block,
                "label": label,
                "caption": caption,
                "options": options,
            }
        )
        i = end

    return figures


def extract_tikz_body(block: str) -> str:
    """
    Extract TikZ content to put in standalone doc.
    Unwraps \resizebox if present, returns tikzpicture (or full content).
    """
    # remove resizebox wrapper if present
    resizebox = re.search(
        r"\\resizebox\{[^}]*\}\{[^}]*\}\{%?\s*(\n?)(\\begin\{tikzpicture\}.*?\\end\{tikzpicture\})\s*\}",
        block,
        re.DOTALL,
    )
    if resizebox:
        return resizebox.group(2).strip()

    # plain tikzpicture
    tikz = re.search(r"(\\begin\{tikzpicture\}.*?\\end\{tikzpicture\})", block, re.DOTALL)
    if tikz:
        return tikz.group(1).strip()

    return ""


def label_to_filename(label: str) -> str:
    """Convert \label text to safe filename: fig:rag_timeline → tikz_rag_timeline"""
    name = label.replace("fig:", "tikz_").replace(":", "_").replace("/", "_")
    return name


def compile_tikz_to_png(tikz_body: str, output_name: str) -> Path | None:
    """Compile TikZ body to PNG, return path or None on failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        src = tmp / "fig.tex"
        src.write_text(PREAMBLE + tikz_body + POSTAMBLE, encoding="utf-8")

        # compile
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "fig.tex"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        pdf = tmp / "fig.pdf"
        if not pdf.exists():
            print(f"  ✗ pdflatex failed for {output_name}")
            # show last error lines
            for line in result.stdout.splitlines()[-15:]:
                if line.startswith("!") or "Error" in line:
                    print(f"    {line}")
            return None

        # convert PDF → PNG via pdftoppm
        png_base = tmp / "fig"
        subprocess.run(
            ["pdftoppm", "-r", "300", "-png", "-singlefile", str(pdf), str(png_base)],
            check=True,
            capture_output=True,
        )
        png_src = tmp / "fig.png"
        if not png_src.exists():
            print(f"  ✗ pdftoppm produced no PNG for {output_name}")
            return None

        # copy to thesis figures dir
        dest = FIGURES / f"{output_name}.png"
        shutil.copy(png_src, dest)
        print(f"  ✓ {dest.name}")
        return dest


def make_replacement(label: str, caption: str, options: str, filename: str) -> str:
    """Build replacement figure environment using \includegraphics."""
    return (
        f"\\begin{{figure}}[{options}]\n"
        f"\\centering\n"
        f"\\includegraphics[width=\\linewidth]{{figures/{filename}.png}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        f"\\end{{figure}}"
    )


def process_chapter(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    figures = extract_figures(text)
    if not figures:
        return

    print(f"\n{path.name}: {len(figures)} TikZ figure(s)")
    replacements = []  # (start, end, new_text)

    for fig in figures:
        label = fig["label"] or "fig_unknown"
        filename = label_to_filename(label)
        print(f"  → {label}")

        tikz_body = extract_tikz_body(fig["block"])
        if not tikz_body:
            print(f"  ✗ could not extract tikz body for {label}")
            continue

        png_path = compile_tikz_to_png(tikz_body, filename)
        if png_path is None:
            continue

        new_fig = make_replacement(label, fig["caption"], fig["options"], filename)
        replacements.append((fig["start"], fig["end"], new_fig))

    # apply replacements in reverse order to preserve offsets
    for start, end, new_text in sorted(replacements, key=lambda x: x[0], reverse=True):
        text = text[:start] + new_text + text[end:]

    path.write_text(text, encoding="utf-8")
    print(f"  → {path.name} updated")


if __name__ == "__main__":
    for chapter in CHAPTERS:
        process_chapter(chapter)
    print("\nDone. Run pdflatex to verify.")
