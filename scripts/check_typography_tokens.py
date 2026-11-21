#!/usr/bin/env python3
"""Typography & Dual-Surface Ergonomics Drift Linter.

Mechanically asserts zero drift across frontend-dashboard/src:
1. Perceptual OKLCH dual-surface ink tokens (:root and .lens-surface-light) in typography.css.
2. Metric-matched @font-face fallback overrides in globals.css.
3. Continuous variable font axes in layout.tsx.
4. Tailwind config token parity (ink.*, modular fontSize, preserved legacy namespaces).
5. Zero bg-black / #000000 canvas tokens and zero unguarded text-white glare tokens.
6. Zero negative tracking (tracking-tight / tracking-tighter) on micro-data elements.
7. Zero em-dash (U+2014) characters in frontend source files.
8. Zero raw hex colours in utility classes (tokens only).
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend-dashboard"
SRC_DIR = FRONTEND_DIR / "src"

ERRORS: list[str] = []

REQUIRED_INK_TOKENS = [
    "--ink-primary",
    "--ink-secondary",
    "--ink-muted",
    "--ink-faint",
    "--ink-statutory",
    "--ink-numeric",
    "--ink-crimson",
    "--ink-amber",
    "--ink-emerald",
    "--ink-cobalt",
]

REQUIRED_SCALE_TOKENS = [
    "display-lg",
    "display-md",
    "heading-sm",
    "body-default",
    "body-dense",
    "mono-data",
    "caption-mono",
]


def check_typography_css() -> None:
    css_path = SRC_DIR / "styles" / "typography.css"
    if not css_path.exists():
        ERRORS.append(f"Missing required stylesheet: {css_path}")
        return

    content = css_path.read_text(encoding="utf-8")

    # Verify :root and .lens-surface-light blocks exist
    if ":root" not in content or ".lens-surface-light" not in content:
        ERRORS.append(f"{css_path}: Must define both :root and .lens-surface-light blocks.")

    # Verify every --ink-* token is defined in both surfaces using perceptual oklch()
    for token in REQUIRED_INK_TOKENS:
        matches = re.findall(rf"{re.escape(token)}\s*:\s*([^;]+);", content)
        if len(matches) < 2:
            ERRORS.append(
                f"{css_path}: Token {token} must be defined in both :root and .lens-surface-light (found {len(matches)})."
            )
        for val in matches:
            if not val.strip().startswith("oklch("):
                ERRORS.append(
                    f"{css_path}: Token {token} value '{val.strip()}' must use perceptual oklch() notation."
                )

    for utility in (".tabular-nums", ".tabular-currency", ".statutory-cite"):
        if utility not in content:
            ERRORS.append(f"{css_path}: Missing required utility class '{utility}'.")

    for scale in REQUIRED_SCALE_TOKENS:
        if f".type-{scale}" not in content:
            ERRORS.append(f"{css_path}: Missing modular scale utility '.type-{scale}'.")


def check_fallback_metrics() -> None:
    globals_path = SRC_DIR / "app" / "globals.css"
    content = globals_path.read_text(encoding="utf-8")
    for family in ("Inter Fallback", "JetBrains Mono Fallback"):
        if family not in content:
            ERRORS.append(f"{globals_path}: Missing @font-face fallback definition for '{family}'.")
    for prop in ("size-adjust:", "ascent-override:", "descent-override:", "line-gap-override:"):
        if prop not in content:
            ERRORS.append(f"{globals_path}: Missing fallback metric override '{prop}'.")


def check_variable_font_loading() -> None:
    layout_path = SRC_DIR / "app" / "layout.tsx"
    content = layout_path.read_text(encoding="utf-8")
    for axis_sig in (
        "Inter:opsz,wght@14..32,300..800",
        "JetBrains+Mono:wght@300..700",
        "Newsreader:ital,opsz,wght@",
    ):
        if axis_sig not in content:
            ERRORS.append(f"{layout_path}: Missing variable font axis range '{axis_sig}'.")


def check_tailwind_config() -> None:
    tw_path = FRONTEND_DIR / "tailwind.config.ts"
    content = tw_path.read_text(encoding="utf-8")
    for legacy_ns in ("canvas:", "terminal:", "cobalt:", "status:", "nightmare:", "slate:", "ink:"):
        if legacy_ns not in content:
            ERRORS.append(f"{tw_path}: Missing required Tailwind color namespace '{legacy_ns}'.")
    for scale in REQUIRED_SCALE_TOKENS:
        if f'"{scale}"' not in content and f"'{scale}'" not in content:
            ERRORS.append(f"{tw_path}: Missing modular fontSize token '{scale}'.")


def check_source_file(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO_ROOT)

    for line_no, line in enumerate(content.splitlines(), 1):
        # 1. Ban bg-black / dark:bg-black canvas tokens
        if re.search(r"\b(?:dark:)?bg-black(?:/\d+)?\b", line):
            ERRORS.append(f"{rel}:{line_no}: Forbidden 'bg-black' canvas token. Use 'bg-canvas-dark'.")

        # 2. Ban text-white on terminal surfaces (solid buttons should use text-canvas-stone)
        if re.search(r"\b(?:dark:|hover:|dark:hover:)?text-white\b", line):
            ERRORS.append(
                f"{rel}:{line_no}: Forbidden 'text-white' token. Use 'text-ink-primary' or 'text-canvas-stone'."
            )

        # 3. Ban negative tracking on micro-data elements (< 14px)
        if re.search(
            r"(?:text-\[?(?:8|9|10|11)px\]?|text-xs|type-mono-data|type-caption-mono)[^>]*\btracking-tight(?:er)?\b",
            line,
        ) or re.search(
            r"\btracking-tight(?:er)?\b[^>]*(?:text-\[?(?:8|9|10|11)px\]?|text-xs|type-mono-data|type-caption-mono)",
            line,
        ):
            ERRORS.append(
                f"{rel}:{line_no}: Negative tracking applied to micro-data. Dark mode requires positive tracking."
            )

        # 4. Ban raw hex colours in utility classes (use the tailwind.config.ts tokens)
        if path.suffix in (".tsx", ".ts") and re.search(r"[a-z]-\[#[0-9A-Fa-f]{3,8}\]", line):
            ERRORS.append(
                f"{rel}:{line_no}: Raw hex colour in a utility class. Use a token (terminal-*, canvas-*, ink-*)."
            )

        # 5. Ban em-dash character
        if "\u2014" in line:
            ERRORS.append(f"{rel}:{line_no}: Prohibited em-dash character (\\u2014) detected.")


def main() -> int:
    check_typography_css()
    check_fallback_metrics()
    check_variable_font_loading()
    check_tailwind_config()

    for ext in ("*.tsx", "*.ts", "*.css"):
        for file_path in sorted(SRC_DIR.rglob(ext)):
            check_source_file(file_path)

    if ERRORS:
        print(f"FAILED: {len(ERRORS)} typography governance error(s) detected:\n")
        for err in ERRORS:
            print(f"  - {err}")
        return 1

    print("PASSED: 100% typography token, OKLCH dual-surface, and ergonomics compliance verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
