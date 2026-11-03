"""Build the profile-card SVGs used at the top of the README.

The card is a single SVG because GitHub sanitises READMEs: no custom CSS, no
layout, no hover states. Everything visual therefore lives in the image, while
the real, clickable links stay in the markdown below it.

Four variants are emitted so the card follows the reader's theme *and* screen
size. The README picks between them with `<source media>` queries, which GitHub
keeps in the sanitised HTML:

    assets/profile-card-dark.svg            wide, 900 x 1010
    assets/profile-card-light.svg           wide, 900 x 1010
    assets/profile-card-mobile-dark.svg     portrait, 720 x 1712
    assets/profile-card-mobile-light.svg    portrait, 720 x 1712

The wide card is the desktop design. At phone width it scales down to a ~360px
thumbnail and its text becomes unreadable, so the portrait card reflows the same
content into one column with type that still holds up at 360px.

Run from the repository root:

    python scripts/build_profile_card.py
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
AVATAR = ASSETS / "avatar.png"
OUT_DARK = ASSETS / "profile-card-dark.svg"
OUT_LIGHT = ASSETS / "profile-card-light.svg"
OUT_MOBILE_DARK = ASSETS / "profile-card-mobile-dark.svg"
OUT_MOBILE_LIGHT = ASSETS / "profile-card-mobile-light.svg"

W, H = 900, 1010
MW, MH = 720, 1712
FONT = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)

THEMES = {
    "dark": {
        "canvas": "#0d1117",
        "glow": "#ffffff",
        "glass1": "#ffffff",
        "glass2": "#ffffff",
        "glass1_op": "0.065",
        "glass2_op": "0.018",
        "edge1": "#ffffff",
        "edge2": "#ffffff",
        "edge1_op": "0.16",
        "edge2_op": "0.045",
        "ink": "#e6edf3",
        "muted": "#9aa5b1",
        "faint": "#6b7684",
        "icon": "#c9d1d9",
        "thumb": "#0b1017",
        "thumb_bar": "#161d26",
        "thumb_edge": "#ffffff1f",
        "accent_a": "#58a6ff",
        "accent_b": "#3fb950",
        "accent_c": "#bc8cff",
        "shadow": "#000000",
        "shadow_op": "0.55",
        "cta_bg": "#e6edf3",
        "cta_fg": "#0d1117",
        "tools": {
            "react": "#61dafb",
            "typescript": "#3178c6",
            "nextdotjs": "#e6edf3",
            "nodedotjs": "#5fa04e",
            "mongodb": "#47a248",
            "tailwindcss": "#38bdf8",
        },
    },
    "light": {
        "canvas": "#f6f8fa",
        "glow": "#ffffff",
        "glass1": "#ffffff",
        "glass2": "#f7f9fb",
        "glass1_op": "1",
        "glass2_op": "1",
        "edge1": "#d0d7de",
        "edge2": "#e6eaef",
        "edge1_op": "1",
        "edge2_op": "1",
        "ink": "#1f2328",
        "muted": "#59636e",
        "faint": "#8c959f",
        "icon": "#424a53",
        "thumb": "#ffffff",
        "thumb_bar": "#f0f3f6",
        "thumb_edge": "#d8dee4",
        "accent_a": "#0969da",
        "accent_b": "#1a7f37",
        "accent_c": "#8250df",
        "shadow": "#1f2328",
        "shadow_op": "0.16",
        "cta_bg": "#1f2328",
        "cta_fg": "#ffffff",
        "tools": {
            "react": "#087ea4",
            "typescript": "#3178c6",
            "nextdotjs": "#1f2328",
            "nodedotjs": "#3c873a",
            "mongodb": "#3f8f3f",
            "tailwindcss": "#0ea5e9",
        },
    },
}

ICONS = {
    "github": "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12",
    "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
    "gmail": "M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z",
    "figma": "M15.852 8.981h-4.588V0h4.588c2.476 0 4.49 2.014 4.49 4.49s-2.014 4.491-4.49 4.491zM12.735 7.51h3.117c1.665 0 3.019-1.355 3.019-3.019s-1.355-3.019-3.019-3.019h-3.117V7.51zm0 1.471H8.148c-2.476 0-4.49-2.014-4.49-4.49S5.672 0 8.148 0h4.588v8.981zm-4.587-7.51c-1.665 0-3.019 1.355-3.019 3.019s1.354 3.02 3.019 3.02h3.117V1.471H8.148zm4.587 15.019H8.148c-2.476 0-4.49-2.014-4.49-4.49s2.014-4.49 4.49-4.49h4.588v8.98zM8.148 8.981c-1.665 0-3.019 1.355-3.019 3.019s1.355 3.019 3.019 3.019h3.117V8.981H8.148zM8.172 24c-2.489 0-4.515-2.014-4.515-4.49s2.014-4.49 4.49-4.49h4.588v4.441c0 2.503-2.047 4.539-4.563 4.539zm-.024-7.51a3.023 3.023 0 0 0-3.019 3.019c0 1.665 1.365 3.019 3.044 3.019 1.705 0 3.093-1.376 3.093-3.068v-2.97H8.148zm7.704 0h-.098c-2.476 0-4.49-2.014-4.49-4.49s2.014-4.49 4.49-4.49h.098c2.476 0 4.49 2.014 4.49 4.49s-2.014 4.49-4.49 4.49zm-.097-7.509c-1.665 0-3.019 1.355-3.019 3.019s1.355 3.019 3.019 3.019h.098c1.665 0 3.019-1.355 3.019-3.019s-1.355-3.019-3.019-3.019h-.098z",
    "react": "M14.23 12.004a2.236 2.236 0 0 1-2.235 2.236 2.236 2.236 0 0 1-2.236-2.236 2.236 2.236 0 0 1 2.235-2.236 2.236 2.236 0 0 1 2.236 2.236zm2.648-10.69c-1.346 0-3.107.96-4.888 2.622-1.78-1.653-3.542-2.602-4.887-2.602-.41 0-.783.093-1.106.278-1.375.793-1.683 3.264-.973 6.365C1.98 8.917 0 10.42 0 12.004c0 1.59 1.99 3.097 5.043 4.03-.704 3.113-.39 5.588.988 6.38.32.187.69.275 1.102.275 1.345 0 3.107-.96 4.888-2.624 1.78 1.654 3.542 2.603 4.887 2.603.41 0 .783-.09 1.106-.275 1.374-.792 1.683-3.263.973-6.365C22.02 15.096 24 13.59 24 12.004c0-1.59-1.99-3.097-5.043-4.032.704-3.11.39-5.587-.988-6.38-.318-.184-.688-.277-1.092-.278zm-.005 1.09v.006c.225 0 .406.044.558.127.666.382.955 1.835.73 3.704-.054.46-.142.945-.25 1.44-.96-.236-2.006-.417-3.107-.534-.66-.905-1.345-1.727-2.035-2.447 1.592-1.48 3.087-2.292 4.105-2.295zm-9.77.02c1.012 0 2.514.808 4.11 2.28-.686.72-1.37 1.537-2.02 2.442-1.107.117-2.154.298-3.113.538-.112-.49-.195-.964-.254-1.42-.23-1.868.054-3.32.714-3.707.19-.09.4-.127.563-.132zm4.882 3.05c.455.468.91.992 1.36 1.564-.44-.02-.89-.034-1.345-.034-.46 0-.915.01-1.36.034.44-.572.895-1.096 1.345-1.565zM12 8.1c.74 0 1.477.034 2.202.093.406.582.802 1.203 1.183 1.86.372.64.71 1.29 1.018 1.946-.308.655-.646 1.31-1.013 1.95-.38.66-.773 1.288-1.18 1.87-.728.063-1.466.098-2.21.098-.74 0-1.477-.035-2.202-.093-.406-.582-.802-1.204-1.183-1.86-.372-.64-.71-1.29-1.018-1.946.303-.657.646-1.313 1.013-1.954.38-.66.773-1.286 1.18-1.868.728-.064 1.466-.098 2.21-.098zm-3.635.254c-.24.377-.48.763-.704 1.16-.225.39-.435.782-.635 1.174-.265-.656-.49-1.31-.676-1.947.64-.15 1.315-.283 2.015-.386zm7.26 0c.695.103 1.365.23 2.006.387-.18.632-.405 1.282-.66 1.933-.2-.39-.41-.783-.64-1.174-.225-.392-.465-.774-.705-1.146zm3.063.675c.484.15.944.317 1.375.498 1.732.74 2.852 1.708 2.852 2.476-.005.768-1.125 1.74-2.857 2.475-.42.18-.88.342-1.355.493-.28-.958-.646-1.956-1.1-2.98.45-1.017.81-2.01 1.085-2.964zm-13.395.004c.278.96.645 1.957 1.1 2.98-.45 1.017-.812 2.01-1.086 2.964-.484-.15-.944-.318-1.37-.5-1.732-.737-2.852-1.706-2.852-2.474 0-.768 1.12-1.742 2.852-2.476.42-.18.88-.342 1.356-.494zm11.678 4.28c.265.657.49 1.312.676 1.948-.64.157-1.316.29-2.016.39.24-.375.48-.762.705-1.158.225-.39.435-.788.636-1.18zm-9.945.02c.2.392.41.783.64 1.175.23.39.465.772.705 1.143-.695-.102-1.365-.23-2.006-.386.18-.63.406-1.282.66-1.933zM17.92 16.32c.112.493.2.968.254 1.423.23 1.868-.054 3.32-.714 3.708-.147.09-.338.128-.563.128-1.012 0-2.514-.807-4.11-2.28.686-.72 1.37-1.536 2.02-2.44 1.107-.118 2.154-.3 3.113-.54zm-11.83.01c.96.234 2.006.415 3.107.532.66.905 1.345 1.727 2.035 2.446-1.595 1.483-3.092 2.295-4.11 2.295-.22-.005-.406-.05-.553-.132-.666-.38-.955-1.834-.73-3.703.054-.46.142-.944.25-1.438zm4.56.64c.44.02.89.034 1.345.034.46 0 .915-.01 1.36-.034-.44.572-.895 1.095-1.345 1.565-.455-.47-.91-.993-1.36-1.565z",
    "typescript": "M1.125 0C.502 0 0 .502 0 1.125v21.75C0 23.498.502 24 1.125 24h21.75c.623 0 1.125-.502 1.125-1.125V1.125C24 .502 23.498 0 22.875 0zm17.363 9.75c.612 0 1.154.037 1.627.111a6.38 6.38 0 0 1 1.306.34v2.458a3.95 3.95 0 0 0-.643-.361 5.093 5.093 0 0 0-.717-.26 5.453 5.453 0 0 0-1.426-.2c-.3 0-.573.028-.819.086a2.1 2.1 0 0 0-.623.242c-.17.104-.3.229-.393.374a.888.888 0 0 0-.14.49c0 .196.053.373.156.529.104.156.252.304.443.444s.423.276.696.41c.273.135.582.274.926.416.47.197.892.407 1.266.628.374.222.695.473.963.753.268.279.472.598.614.957.142.359.214.776.214 1.253 0 .657-.125 1.21-.373 1.656a3.033 3.033 0 0 1-1.012 1.085 4.38 4.38 0 0 1-1.487.596c-.566.12-1.163.18-1.79.18a9.916 9.916 0 0 1-1.84-.164 5.544 5.544 0 0 1-1.512-.493v-2.63a5.033 5.033 0 0 0 3.237 1.2c.333 0 .624-.03.872-.09.249-.06.456-.144.623-.25.166-.108.29-.234.373-.38a1.023 1.023 0 0 0-.074-1.089 2.12 2.12 0 0 0-.537-.5 5.597 5.597 0 0 0-.807-.444 27.72 27.72 0 0 0-1.007-.436c-.918-.383-1.602-.852-2.053-1.405-.45-.553-.676-1.222-.676-2.005 0-.614.123-1.141.369-1.582.246-.441.58-.804 1.004-1.089a4.494 4.494 0 0 1 1.47-.629 7.536 7.536 0 0 1 1.77-.201zm-15.113.188h9.563v2.166H9.506v9.646H6.789v-9.646H3.375z",
    "nextdotjs": "M18.665 21.978C16.758 23.255 14.465 24 12 24 5.377 24 0 18.623 0 12S5.377 0 12 0s12 5.377 12 12c0 3.583-1.574 6.801-4.067 9.001L9.219 7.2H7.2v9.596h1.615V9.251l9.85 12.727Zm-3.332-8.533 1.6 2.061V7.2h-1.6v6.245Z",
    "nodedotjs": "M11.998,24c-0.321,0-0.641-0.084-0.922-0.247l-2.936-1.737c-0.438-0.245-0.224-0.332-0.08-0.383 0.585-0.203,0.703-0.25,1.328-0.604c0.065-0.037,0.151-0.023,0.218,0.017l2.256,1.339c0.082,0.045,0.197,0.045,0.272,0l8.795-5.076 c0.082-0.047,0.134-0.141,0.134-0.238V6.921c0-0.099-0.053-0.192-0.137-0.242l-8.791-5.072c-0.081-0.047-0.189-0.047-0.271,0 L3.075,6.68C2.99,6.729,2.936,6.825,2.936,6.921v10.15c0,0.097,0.054,0.189,0.139,0.235l2.409,1.392 c1.307,0.654,2.108-0.116,2.108-0.89V7.787c0-0.142,0.114-0.253,0.256-0.253h1.115c0.139,0,0.255,0.112,0.255,0.253v10.021 c0,1.745-0.95,2.745-2.604,2.745c-0.508,0-0.909,0-2.026-0.551L2.28,18.675c-0.57-0.329-0.922-0.945-0.922-1.604V6.921 c0-0.659,0.353-1.275,0.922-1.603l8.795-5.082c0.557-0.315,1.296-0.315,1.848,0l8.794,5.082c0.57,0.329,0.924,0.944,0.924,1.603 v10.15c0,0.659-0.354,1.273-0.924,1.604l-8.794,5.078C12.643,23.916,12.324,24,11.998,24z M19.099,13.993 c0-1.9-1.284-2.406-3.987-2.763c-2.731-0.361-3.009-0.548-3.009-1.187c0-0.528,0.235-1.233,2.258-1.233 c1.807,0,2.473,0.389,2.747,1.607c0.024,0.115,0.129,0.199,0.247,0.199h1.141c0.071,0,0.138-0.031,0.186-0.081 c0.048-0.054,0.074-0.123,0.067-0.196c-0.177-2.098-1.571-3.076-4.388-3.076c-2.508,0-4.004,1.058-4.004,2.833 c0,1.925,1.488,2.457,3.895,2.695c2.88,0.282,3.103,0.703,3.103,1.269c0,0.983-0.789,1.402-2.642,1.402 c-2.327,0-2.839-0.584-3.011-1.742c-0.02-0.124-0.126-0.215-0.253-0.215h-1.137c-0.141,0-0.254,0.112-0.254,0.253 c0,1.482,0.806,3.248,4.655,3.248C17.501,17.007,19.099,15.91,19.099,13.993z",
    "mongodb": "M17.193 9.555c-1.264-5.58-4.252-7.414-4.573-8.115-.28-.394-.53-.954-.735-1.44-.036.495-.055.685-.523 1.184-.723.566-4.438 3.682-4.74 10.02-.282 5.912 4.27 9.435 4.888 9.884l.07.05A73.49 73.49 0 0111.91 24h.481c.114-1.032.284-2.056.51-3.07.417-.296.604-.463.85-.693a11.342 11.342 0 003.639-8.464c.01-.814-.103-1.662-.197-2.218zm-5.336 8.195s0-8.291.275-8.29c.213 0 .49 10.695.49 10.695-.381-.045-.765-1.76-.765-2.405z",
    "tailwindcss": "M12.001,4.8c-3.2,0-5.2,1.6-6,4.8c1.2-1.6,2.6-2.2,4.2-1.8c0.913,0.228,1.565,0.89,2.288,1.624 C13.666,10.618,15.027,12,18.001,12c3.2,0,5.2-1.6,6-4.8c-1.2,1.6-2.6,2.2-4.2,1.8c-0.913-0.228-1.565-0.89-2.288-1.624 C16.337,6.182,14.976,4.8,12.001,4.8z M6.001,12c-3.2,0-5.2,1.6-6,4.8c1.2-1.6,2.6-2.2,4.2-1.8c0.913,0.228,1.565,0.89,2.288,1.624 c1.177,1.194,2.538,2.576,5.512,2.576c3.2,0,5.2-1.6,6-4.8c-1.2,1.6-2.6,2.2-4.2,1.8c-0.913-0.228-1.565-0.89-2.288-1.624 C10.337,13.382,8.976,12,6.001,12z",
}

TOOL_NAMES = [
    ("react", "React"),
    ("typescript", "TypeScript"),
    ("nextdotjs", "Next.js"),
    ("nodedotjs", "Node.js"),
    ("mongodb", "MongoDB"),
    ("tailwindcss", "Tailwind"),
]

SOCIALS = ["github", "linkedin", "mail", "figma", "globe"]


def avatar_data_uri() -> str:
    image = Image.open(AVATAR).convert("RGB")
    image = image.resize((236, 236), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90, optimize=True, progressive=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def txt(
    x: float,
    y: float,
    value: str,
    size: float,
    color: str,
    weight: int = 400,
    anchor: str = "start",
    spacing: float | None = None,
) -> str:
    attrs = [
        f'x="{x}"',
        f'y="{y}"',
        f'font-family="{FONT}"',
        f'font-size="{size}"',
        f'font-weight="{weight}"',
        f'fill="{color}"',
    ]
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    return f"<text {' '.join(attrs)}>{value}</text>"


def icon(name: str, x: float, y: float, size: float, color: str) -> str:
    if name == "globe":
        scale = size / 24
        return (
            f'<g transform="translate({x} {y}) scale({scale:.5f})" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round">'
            '<circle cx="12" cy="12" r="9.2"/>'
            '<ellipse cx="12" cy="12" rx="4.1" ry="9.2"/>'
            '<path d="M2.8 12h18.4M4.6 7.4h14.8M4.6 16.6h14.8"/>'
            "</g>"
        )
    if name == "mail":
        scale = size / 24
        return (
            f'<g transform="translate({x} {y}) scale({scale:.5f})" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="2.6" y="4.8" width="18.8" height="14.4" rx="2.6"/>'
            '<path d="M3.8 7.2 12 13.2l8.2-6"/>'
            "</g>"
        )
    scale = size / 24
    return (
        f'<g transform="translate({x} {y}) scale({scale:.5f})">'
        f'<path d="{ICONS[name]}" fill="{color}"/>'
        "</g>"
    )


def panel(x: float, y: float, w: float, h: float, r: float = 24) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        'fill="url(#glass)" stroke="url(#edge)" stroke-width="1"/>'
    )


def pill(cx: float, cy: float, w: float, label: str, rot: float, t: dict) -> str:
    return (
        f'<g transform="translate({cx} {cy}) rotate({rot})">'
        f'<rect x="{-w / 2:.1f}" y="-13" width="{w}" height="26" rx="13" '
        'fill="url(#glass)" stroke="url(#edge)" stroke-width="1"/>'
        + txt(
            0,
            1,
            label,
            10,
            t["ink"],
            500,
            "middle",
            0.1,
        ).replace("<text ", '<text dominant-baseline="middle" ')
        + "</g>"
    )


def work_sawn(t: dict) -> str:
    faint = t["faint"]
    return f"""
      <rect width="240" height="148" fill="{t['thumb']}"/>
      <rect width="240" height="24" fill="{t['thumb_bar']}"/>
      <circle cx="12" cy="12" r="3" fill="{faint}" opacity=".55"/>
      <circle cx="22" cy="12" r="3" fill="{faint}" opacity=".4"/>
      <circle cx="32" cy="12" r="3" fill="{faint}" opacity=".28"/>
      <rect y="24" width="38" height="124" fill="{t['thumb_bar']}" opacity=".55"/>
      <rect x="10" y="40" width="18" height="3" rx="1.5" fill="{faint}" opacity=".75"/>
      <rect x="10" y="50" width="14" height="3" rx="1.5" fill="{faint}" opacity=".45"/>
      <rect x="10" y="60" width="20" height="3" rx="1.5" fill="{faint}" opacity=".45"/>
      <rect x="10" y="70" width="12" height="3" rx="1.5" fill="{faint}" opacity=".45"/>
      <rect x="52" y="40" width="46" height="4" rx="2" fill="{t['accent_c']}" opacity=".85"/>
      <rect x="104" y="40" width="58" height="4" rx="2" fill="{faint}" opacity=".4"/>
      <rect x="62" y="54" width="82" height="4" rx="2" fill="{faint}" opacity=".4"/>
      <rect x="62" y="68" width="52" height="4" rx="2" fill="{t['accent_a']}" opacity=".8"/>
      <rect x="120" y="68" width="34" height="4" rx="2" fill="{faint}" opacity=".4"/>
      <rect x="62" y="82" width="66" height="4" rx="2" fill="{faint}" opacity=".4"/>
      <rect x="72" y="96" width="90" height="4" rx="2" fill="{faint}" opacity=".3"/>
      <rect x="72" y="110" width="44" height="4" rx="2" fill="{t['accent_b']}" opacity=".75"/>
      <rect x="52" y="124" width="2" height="10" fill="{t['accent_a']}"/>
      <rect x="176" y="30" width="48" height="18" rx="9" fill="{t['accent_c']}" opacity=".16"/>
      {txt(200, 43, "AI", 8, t["accent_c"], 600, "middle", 0.4)}
    """


def work_flowdesk(t: dict) -> str:
    faint = t["faint"]
    return f"""
      <rect width="240" height="148" fill="{t['thumb']}"/>
      <rect width="34" height="148" fill="{t['thumb_bar']}"/>
      <circle cx="17" cy="20" r="4" fill="{t['accent_b']}" opacity=".8"/>
      <rect x="11" y="36" width="12" height="3" rx="1.5" fill="{faint}" opacity=".5"/>
      <rect x="11" y="46" width="16" height="3" rx="1.5" fill="{faint}" opacity=".3"/>
      <rect x="11" y="56" width="10" height="3" rx="1.5" fill="{faint}" opacity=".3"/>
      <rect x="11" y="66" width="15" height="3" rx="1.5" fill="{faint}" opacity=".3"/>
      <rect x="46" y="24" width="86" height="44" rx="8" fill="{t['thumb_bar']}" stroke="{t['thumb_edge']}"/>
      <rect x="56" y="34" width="24" height="3" rx="1.5" fill="{faint}" opacity=".5"/>
      <rect x="56" y="46" width="40" height="7" rx="3.5" fill="{t['ink']}" opacity=".8"/>
      <rect x="56" y="58" width="18" height="2.5" rx="1.25" fill="{t['accent_b']}" opacity=".8"/>
      <rect x="142" y="24" width="86" height="44" rx="8" fill="{t['thumb_bar']}" stroke="{t['thumb_edge']}"/>
      <rect x="152" y="34" width="24" height="3" rx="1.5" fill="{faint}" opacity=".5"/>
      <rect x="152" y="46" width="28" height="7" rx="3.5" fill="{t['ink']}" opacity=".8"/>
      <rect x="152" y="58" width="22" height="2.5" rx="1.25" fill="{t['accent_a']}" opacity=".8"/>
      <rect x="46" y="78" width="182" height="54" rx="8" fill="{t['thumb_bar']}" stroke="{t['thumb_edge']}"/>
      <polyline points="56,120 74,108 90,114 108,96 124,102 142,86 160,92 178,80 196,86 214,74"
        fill="none" stroke="{t['accent_b']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="214" cy="74" r="2.6" fill="{t['accent_b']}"/>
      <line x1="56" y1="88" x2="218" y2="88" stroke="{t['thumb_edge']}" stroke-width="1"/>
      <line x1="56" y1="104" x2="218" y2="104" stroke="{t['thumb_edge']}" stroke-width="1"/>
    """


def work_figma(t: dict) -> str:
    faint = t["faint"]
    return f"""
      <rect width="240" height="148" fill="{t['thumb']}"/>
      <rect width="64" height="148" fill="{t['thumb_bar']}"/>
      <circle cx="20" cy="30" r="8" fill="{t['accent_c']}" opacity=".85"/>
      <circle cx="42" cy="30" r="8" fill="{t['accent_a']}" opacity=".85"/>
      <circle cx="20" cy="52" r="8" fill="{t['accent_b']}" opacity=".85"/>
      <circle cx="42" cy="52" r="8" fill="{t['ink']}" opacity=".55"/>
      <rect x="12" y="80" width="40" height="3" rx="1.5" fill="{faint}" opacity=".55"/>
      <rect x="12" y="90" width="30" height="3" rx="1.5" fill="{faint}" opacity=".35"/>
      <rect x="12" y="100" width="36" height="3" rx="1.5" fill="{faint}" opacity=".35"/>
      <rect x="12" y="110" width="24" height="3" rx="1.5" fill="{faint}" opacity=".35"/>
      <rect x="82" y="24" width="66" height="44" rx="8" fill="{t['thumb_bar']}" stroke="{t['thumb_edge']}"/>
      <rect x="90" y="34" width="22" height="22" rx="6" fill="{t['accent_c']}" opacity=".7"/>
      <rect x="118" y="34" width="22" height="22" rx="6" fill="{t['accent_c']}" opacity=".3"/>
      <rect x="158" y="24" width="66" height="44" rx="8" fill="{t['thumb_bar']}" stroke="{t['thumb_edge']}"/>
      <rect x="166" y="34" width="22" height="22" rx="11" fill="{t['accent_a']}" opacity=".7"/>
      <rect x="194" y="34" width="22" height="22" rx="4" fill="{t['accent_a']}" opacity=".3"/>
      <rect x="82" y="78" width="142" height="54" rx="8" fill="{t['thumb_bar']}" stroke="{t['thumb_edge']}"/>
      <rect x="92" y="88" width="38" height="10" rx="5" fill="{t['ink']}" opacity=".7"/>
      <rect x="92" y="104" width="70" height="4" rx="2" fill="{faint}" opacity=".4"/>
      <rect x="92" y="114" width="52" height="4" rx="2" fill="{faint}" opacity=".3"/>
      <rect x="176" y="88" width="38" height="34" rx="6" fill="{t['accent_b']}" opacity=".22"/>
      <path d="M186 112l6-8 5 6 4-4 5 6" fill="none" stroke="{t['accent_b']}" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"/>
    """


def work_card(
    t: dict,
    x: float,
    y: float,
    angle: float,
    label: str,
    accent: str,
    body: str,
    clip_id: str,
) -> str:
    return f"""
    <g transform="translate({x} {y})">
      <g transform="rotate({angle} 120 90)" filter="url(#lift)">
        <rect width="240" height="180" rx="14" fill="{t['thumb']}" stroke="{t['thumb_edge']}" stroke-width="1"/>
        <g clip-path="url(#{clip_id})">{body}</g>
        <rect y="148" width="240" height="32" fill="{t['thumb_bar']}"/>
        <circle cx="18" cy="164" r="3.5" fill="{accent}"/>
        {txt(30, 168, label, 11, t["ink"], 500)}
        <path d="M213 159l6-6m0 0h-5m5 0v5" fill="none" stroke="{t['faint']}" stroke-width="1.5"
          stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </g>
    """


def build(theme_name: str) -> str:
    t = THEMES[theme_name]
    avatar = avatar_data_uri()

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-labelledby="cardTitle cardDesc">'
    )
    parts.append(
        '<title id="cardTitle">Tejas — Full-Stack Developer and UI/UX Designer</title>'
        '<desc id="cardDesc">Profile card with recent work, services, tools and contact details.</desc>'
    )

    # ---- defs -----------------------------------------------------------
    parts.append(
        f"""
  <defs>
    <linearGradient id="glass" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{t['glass1']}" stop-opacity="{t['glass1_op']}"/>
      <stop offset="1" stop-color="{t['glass2']}" stop-opacity="{t['glass2_op']}"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="0.4" y2="1">
      <stop offset="0" stop-color="{t['edge1']}" stop-opacity="{t['edge1_op']}"/>
      <stop offset="1" stop-color="{t['edge2']}" stop-opacity="{t['edge2_op']}"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{t['glow']}" stop-opacity="{0.07 if theme_name == 'dark' else 0.85}"/>
      <stop offset="1" stop-color="{t['glow']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="warm" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#7aa2ff" stop-opacity="{0.18 if theme_name == 'dark' else 0.12}"/>
      <stop offset="1" stop-color="#7aa2ff" stop-opacity="0"/>
    </radialGradient>
    <filter id="lift" x="-35%" y="-35%" width="170%" height="180%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="{t['shadow']}" flood-opacity="{t['shadow_op']}"/>
    </filter>
    <filter id="grain">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <clipPath id="avatarClip"><rect x="714" y="56" width="118" height="118" rx="20"/></clipPath>
    <clipPath id="clipA"><rect width="240" height="148" rx="14"/></clipPath>
    <clipPath id="clipB"><rect width="240" height="148" rx="14"/></clipPath>
    <clipPath id="clipC"><rect width="240" height="148" rx="14"/></clipPath>
  </defs>
"""
    )

    # ---- canvas ---------------------------------------------------------
    parts.append(f'<rect width="{W}" height="{H}" rx="28" fill="{t["canvas"]}"/>')
    parts.append(f'<rect width="{W}" height="{H}" rx="28" fill="url(#halo)"/>')
    parts.append('<ellipse cx="773" cy="120" rx="210" ry="170" fill="url(#warm)"/>')

    # ---- header ---------------------------------------------------------
    parts.append(panel(40, 40, 630, 150))
    parts.append(txt(76, 104, "Hey, I’m Tejas", 40, t["ink"], 600, spacing="-0.8"))
    parts.append(
        txt(76, 138, "Full-Stack Developer &amp; UI/UX Designer", 16.5, t["muted"], 400, spacing="0.1")
    )

    parts.append(panel(686, 40, 174, 150))
    parts.append(
        f'<image x="714" y="56" width="118" height="118" clip-path="url(#avatarClip)" '
        f'href="{avatar}" preserveAspectRatio="xMidYMid slice"/>'
    )
    parts.append(
        '<rect x="714" y="56" width="118" height="118" rx="20" fill="none" '
        f'stroke="{t["edge1"]}" stroke-opacity="0.35" stroke-width="1"/>'
    )

    # ---- social row -----------------------------------------------------
    tile_w = (820 - 4 * 16) / 5
    for i, name in enumerate(SOCIALS):
        x = 40 + i * (tile_w + 16)
        parts.append(panel(x, 208, tile_w, 118, 20))
        parts.append(icon(name, x + tile_w / 2 - 17, 257, 34, t["icon"]))

    # ---- recent works ---------------------------------------------------
    parts.append(panel(40, 344, 536, 362))
    parts.append(txt(76, 390, "Recent Works", 15, t["muted"], 500, spacing="0.2"))
    parts.append(
        f'<path d="M528 392l12-12m0 0h-9m9 0v9" fill="none" stroke="{t["muted"]}" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    parts.append(work_card(t, 64, 478, -10, "Sawn", t["accent_c"], work_sawn(t), "clipA"))
    parts.append(work_card(t, 190, 462, 2, "Flowdesk", t["accent_b"], work_flowdesk(t), "clipB"))
    parts.append(work_card(t, 310, 486, 11, "Figma DS", t["accent_a"], work_figma(t), "clipC"))

    # ---- services -------------------------------------------------------
    parts.append(panel(592, 344, 268, 362))
    parts.append(txt(628, 390, "Services", 15, t["muted"], 500, spacing="0.2"))
    parts.append(
        f'<ellipse cx="726" cy="540" rx="72" ry="76" fill="none" stroke="{t["faint"]}" '
        'stroke-opacity=".35" stroke-width="1" stroke-dasharray="2 6" transform="rotate(-12 726 540)"/>'
    )
    services = [
        (712, 470, 88, "AI Products", -7),
        (684, 512, 104, "Design Systems", 8),
        (776, 506, 96, "UI/UX Design", -8),
        (780, 548, 82, "Full-Stack", 6),
        (678, 566, 96, "Figma Plugins", -6),
        (726, 610, 90, "Performance", 4),
    ]
    for cx, cy, w, label, rot in services:
        parts.append(pill(cx, cy, w, label, rot, t))

    # ---- tools ----------------------------------------------------------
    parts.append(panel(40, 724, 296, 246))
    parts.append(txt(72, 786, "Tools I use", 15, t["muted"], 500, spacing="0.2"))
    for index, (key, label) in enumerate(TOOL_NAMES):
        col, row = index % 3, index // 3
        x = 79 + col * 77
        y = 806 + row * 72
        parts.append(panel(x, y, 64, 64, 16))
        parts.append(icon(key, x + 18, y + 11, 28, t["tools"][key]))
        parts.append(txt(x + 32, y + 52, label, 8, t["muted"], 500, "middle"))

    # ---- collab ---------------------------------------------------------
    parts.append(panel(352, 724, 508, 246))
    parts.append(txt(388, 790, "Let’s collab!", 30, t["ink"], 600, spacing="-0.5"))
    parts.append(txt(388, 826, "Let’s turn your idea into reality", 14, t["muted"]))
    parts.append(txt(388, 848, "with my design experience!", 14, t["muted"]))
    parts.append(
        f'<rect x="388" y="884" width="212" height="46" rx="23" fill="{t["cta_bg"]}"/>'
    )
    parts.append(txt(406, 912, "Send a message now!", 12.5, t["cta_fg"], 600))
    parts.append(
        f'<path d="M552 907h14m-5-5 5 5-5 5" fill="none" stroke="{t["cta_fg"]}" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # ---- grain ----------------------------------------------------------
    parts.append(
        f'<rect width="{W}" height="{H}" rx="28" filter="url(#grain)" opacity="'
        f'{0.035 if theme_name == "dark" else 0.02}"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def pill_m(cx: float, cy: float, w: float, label: str, rot: float, t: dict) -> str:
    """A services pill sized for the portrait card (larger than the wide one)."""
    h = 46
    return (
        f'<g transform="translate({cx} {cy}) rotate({rot})">'
        f'<rect x="{-w / 2:.1f}" y="{-h / 2}" width="{w}" height="{h}" rx="{h / 2}" '
        'fill="url(#glass)" stroke="url(#edge)" stroke-width="1"/>'
        + txt(0, 0, label, 22, t["ink"], 500, "middle", 0.1).replace(
            "<text ", '<text dominant-baseline="middle" '
        )
        + "</g>"
    )


def build_mobile(theme_name: str) -> str:
    """The portrait card shown on phones, where the wide card is unreadable."""
    t = THEMES[theme_name]
    avatar = avatar_data_uri()

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {MW} {MH}" width="{MW}" height="{MH}" '
        f'role="img" aria-labelledby="cardTitle cardDesc">'
    )
    parts.append(
        '<title id="cardTitle">Tejas — Full-Stack Developer and UI/UX Designer</title>'
        '<desc id="cardDesc">Profile card with recent work, services, tools and contact details.</desc>'
    )

    parts.append(
        f"""
  <defs>
    <linearGradient id="glass" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{t['glass1']}" stop-opacity="{t['glass1_op']}"/>
      <stop offset="1" stop-color="{t['glass2']}" stop-opacity="{t['glass2_op']}"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="0.4" y2="1">
      <stop offset="0" stop-color="{t['edge1']}" stop-opacity="{t['edge1_op']}"/>
      <stop offset="1" stop-color="{t['edge2']}" stop-opacity="{t['edge2_op']}"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{t['glow']}" stop-opacity="{0.07 if theme_name == 'dark' else 0.85}"/>
      <stop offset="1" stop-color="{t['glow']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="warm" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#7aa2ff" stop-opacity="{0.18 if theme_name == 'dark' else 0.12}"/>
      <stop offset="1" stop-color="#7aa2ff" stop-opacity="0"/>
    </radialGradient>
    <filter id="grain">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <clipPath id="avatarClip"><rect x="572" y="64" width="104" height="104" rx="24"/></clipPath>
    <clipPath id="clipA"><rect width="240" height="148" rx="14"/></clipPath>
    <clipPath id="clipB"><rect width="240" height="148" rx="14"/></clipPath>
    <clipPath id="clipC"><rect width="240" height="148" rx="14"/></clipPath>
  </defs>
"""
    )

    # ---- canvas ---------------------------------------------------------
    parts.append(f'<rect width="{MW}" height="{MH}" rx="28" fill="{t["canvas"]}"/>')
    parts.append(f'<rect width="{MW}" height="{MH}" rx="28" fill="url(#halo)"/>')
    parts.append('<ellipse cx="560" cy="96" rx="230" ry="180" fill="url(#warm)"/>')

    # ---- header ---------------------------------------------------------
    parts.append(panel(32, 32, 512, 168))
    parts.append(txt(64, 108, "Hey, I’m Tejas", 46, t["ink"], 600, spacing="-0.8"))
    parts.append(txt(64, 146, "Full-Stack Developer", 26, t["muted"]))
    parts.append(txt(64, 178, "&amp; UI/UX Designer", 26, t["muted"]))
    parts.append(panel(560, 32, 128, 168))
    parts.append(
        f'<image x="572" y="64" width="104" height="104" clip-path="url(#avatarClip)" '
        f'href="{avatar}" preserveAspectRatio="xMidYMid slice"/>'
    )
    parts.append(
        '<rect x="572" y="64" width="104" height="104" rx="24" fill="none" '
        f'stroke="{t["edge1"]}" stroke-opacity="0.35" stroke-width="1"/>'
    )

    # ---- social row -----------------------------------------------------
    tile_w = (656 - 4 * 14) / 5
    for i, name in enumerate(SOCIALS):
        x = 32 + i * (tile_w + 14)
        parts.append(panel(x, 228, tile_w, 112, 20))
        parts.append(icon(name, x + tile_w / 2 - 19, 265, 38, t["icon"]))

    # ---- recent works (one row per project) -----------------------------
    parts.append(panel(32, 368, 656, 486))
    parts.append(txt(64, 418, "Recent Works", 24, t["muted"], 500, spacing="0.2"))
    parts.append(
        f'<path d="M636 414l12-12m0 0h-9m9 0v9" fill="none" stroke="{t["muted"]}" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    works = [
        ("Sawn", "AI code editor", t["accent_c"], work_sawn(t), "clipA"),
        ("Flowdesk", "Productivity OS", t["accent_b"], work_flowdesk(t), "clipB"),
        ("Figma DS", "Figma plugin", t["accent_a"], work_figma(t), "clipC"),
    ]
    for i, (label, note, accent, art, clip) in enumerate(works):
        y = 446 + i * 116
        parts.append(
            f'<g transform="translate(64 {y}) scale(0.64)">'
            f'<rect width="240" height="148" rx="14" fill="{t["thumb"]}"/>'
            f'<g clip-path="url(#{clip})">{art}</g>'
            f'<rect width="240" height="148" rx="14" fill="none" stroke="{t["thumb_edge"]}"/>'
            "</g>"
        )
        parts.append(f'<circle cx="256" cy="{y + 38}" r="5" fill="{accent}"/>')
        parts.append(txt(272, y + 46, label, 28, t["ink"], 600))
        parts.append(txt(272, y + 76, note, 20, t["muted"]))
        parts.append(
            f'<path d="M628 {y + 40}l14-14m0 0h-10m10 0v10" fill="none" '
            f'stroke="{t["faint"]}" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round"/>'
        )

    # ---- services -------------------------------------------------------
    parts.append(panel(32, 886, 656, 246))
    parts.append(txt(64, 936, "Services", 24, t["muted"], 500, spacing="0.2"))
    for cx, cy, w, label, rot in [
        (147, 990, 150, "AI Products", -5),
        (347, 990, 210, "Design Systems", 4),
        (557, 990, 175, "UI/UX Design", -4),
        (165, 1062, 150, "Full-Stack", 4),
        (352, 1062, 185, "Figma Plugins", -4),
        (547, 1062, 165, "Performance", 3),
    ]:
        parts.append(pill_m(cx, cy, w, label, rot, t))

    # ---- tools ----------------------------------------------------------
    parts.append(panel(32, 1168, 656, 214))
    parts.append(txt(64, 1216, "Tools I use", 24, t["muted"], 500, spacing="0.2"))
    for index, (key, label) in enumerate(TOOL_NAMES):
        x = 42 + index * 108
        y = 1240
        parts.append(panel(x, y, 96, 96, 18))
        parts.append(icon(key, x + 28, y + 22, 40, t["tools"][key]))
        parts.append(txt(x + 48, y + 84, label, 20, t["muted"], 500, "middle"))

    # ---- collab ---------------------------------------------------------
    parts.append(panel(32, 1418, 656, 262))
    parts.append(txt(64, 1498, "Let’s collab!", 44, t["ink"], 600, spacing="-0.5"))
    parts.append(txt(64, 1540, "Let’s turn your idea into reality", 26, t["muted"]))
    parts.append(txt(64, 1574, "with my design experience!", 26, t["muted"]))
    parts.append(f'<rect x="64" y="1602" width="360" height="62" rx="31" fill="{t["cta_bg"]}"/>')
    parts.append(txt(92, 1640, "Send a message now!", 24, t["cta_fg"], 600))
    parts.append(
        f'<path d="M356 1632h18m-7-7 7 7-7 7" fill="none" stroke="{t["cta_fg"]}" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # ---- grain ----------------------------------------------------------
    parts.append(
        f'<rect width="{MW}" height="{MH}" rx="28" filter="url(#grain)" opacity="'
        f'{0.035 if theme_name == "dark" else 0.02}"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    dark = build("dark")
    light = build("light")
    OUT_DARK.write_text(dark, encoding="utf-8")
    OUT_LIGHT.write_text(light, encoding="utf-8")
    OUT_MOBILE_DARK.write_text(build_mobile("dark"), encoding="utf-8")
    OUT_MOBILE_LIGHT.write_text(build_mobile("light"), encoding="utf-8")
    for path in (OUT_DARK, OUT_LIGHT, OUT_MOBILE_DARK, OUT_MOBILE_LIGHT):
        print(f"Wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
