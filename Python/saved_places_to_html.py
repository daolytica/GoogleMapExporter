#!/usr/bin/env python3
import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_latlon_from_url(url: str) -> Optional[Tuple[float, float]]:
    if not url:
        return None

    # Try ?q=lat,lon
    m = re.search(r"[?&]q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", url)
    if m:
        try:
            lat = float(m.group(1))
            lon = float(m.group(2))
            return lat, lon
        except ValueError:
            pass

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    q_vals = qs.get("q")
    if not q_vals:
        return None

    q_raw = q_vals[0]
    q_text = unquote(q_raw.replace("+", " ")).strip()

    m2 = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", q_text)
    if m2:
        try:
            lat = float(m2.group(1))
            lon = float(m2.group(2))
            return lat, lon
        except ValueError:
            return None

    return None


def extract_lat_lon(feature: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    geom = feature.get("geometry") or {}
    props = feature.get("properties") or {}

    # 1) geometry.coordinates
    if isinstance(geom, dict) and geom.get("type") == "Point":
        coords = geom.get("coordinates")
        if (
            isinstance(coords, list)
            and len(coords) >= 2
            and coords[0] is not None
            and coords[1] is not None
        ):
            lon, lat = float(coords[0]), float(coords[1])
            if not (abs(lat) < 1e-12 and abs(lon) < 1e-12):
                return lat, lon

    # 2) google_maps_url
    url = props.get("google_maps_url") or props.get("Google Maps URL")
    if isinstance(url, str):
        parsed = parse_latlon_from_url(url)
        if parsed:
            return parsed

    return None


def derive_name_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    q_vals = qs.get("q")
    if not q_vals:
        return None

    q_raw = q_vals[0]
    q_text = unquote(q_raw.replace("+", " ")).strip()

    # skip pure coords
    if re.match(r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$", q_text):
        return None

    if q_text.lower().startswith("m,"):
        q_text = q_text[2:].strip()

    return q_text or None


def extract_name(feature: Dict[str, Any], idx: int) -> str:
    props = feature.get("properties") or {}
    loc = props.get("location") or {}

    # 1) location.name
    if isinstance(loc, dict) and loc.get("name"):
        return str(loc["name"])

    # 2) from URL q=
    url = props.get("google_maps_url") or props.get("Google Maps URL")
    if isinstance(url, str):
        n = derive_name_from_url(url)
        if n:
            return n

    # 3) other label-ish fields
    for key in ("name", "Name", "title", "Title", "label", "Label"):
        if key in props and props[key]:
            return str(props[key])

    # 4) fallback
    return f"Saved Place {idx}"


def json_to_entries(data: Dict[str, Any]) -> List[Dict[str, str]]:
    features = data.get("features") or []
    rows: List[Dict[str, str]] = []

    for i, feat in enumerate(features, start=1):
        latlon = extract_lat_lon(feat)
        if latlon is None:
            continue
        lat, lon = latlon
        name = extract_name(feat, i)
        props = feat.get("properties") or {}
        date = props.get("date", "")
        url = props.get("google_maps_url") or props.get("Google Maps URL") or ""

        rows.append(
            {
                "name": name,
                "lat": f"{lat:.8f}",
                "lon": f"{lon:.8f}",
                "date": date,
                "gmaps_url": url,
            }
        )

    return rows


def entries_to_html(entries: List[Dict[str, str]], title: str = "Saved Places Launcher") -> str:
    lines: List[str] = []
    lines.append("<!DOCTYPE html>")
    lines.append("<html>")
    lines.append("<head>")
    lines.append(f"<meta charset='utf-8'>")
    lines.append(f"<title>{html.escape(title)}</title>")
    lines.append("<style>")
    lines.append("body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }")
    lines.append("table { border-collapse: collapse; width: 100%; }")
    lines.append("th, td { border: 1px solid #ccc; padding: 4px 8px; }")
    lines.append("th { background: #f0f0f0; }")
    lines.append("a { text-decoration: none; }")
    lines.append("</style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append(f"<h1>{html.escape(title)}</h1>")
    lines.append("<table>")
    lines.append("<tr><th>#</th><th>Name</th><th>Open in Apple Maps</th><th>Google Maps URL</th><th>Date</th></tr>")

    for idx, e in enumerate(entries, start=1):
        name = html.escape(e["name"])
        lat = e["lat"]
        lon = e["lon"]
        date = html.escape(e["date"])
        gmaps_url = html.escape(e["gmaps_url"])

        # Apple Maps URL: maps:// works on macOS & iOS, fallback to https
        maps_url = f"https://maps.apple.com/?ll={lat},{lon}&q={name}"

        lines.append("<tr>")
        lines.append(f"<td>{idx}</td>")
        lines.append(f"<td>{name}</td>")
        lines.append(f"<td><a href='{maps_url}' target='_blank'>Open in Apple Maps</a></td>")
        lines.append(
            f"<td><a href='{gmaps_url}' target='_blank'>{'Google link' if gmaps_url else ''}</a></td>"
        )
        lines.append(f"<td>{date}</td>")
        lines.append("</tr>")

    lines.append("</table>")
    lines.append("<p>Click a link in the “Open in Apple Maps” column, then use “Add to Favorites” or “Add to Guide” in Apple Maps.</p>")
    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Convert Google Saved Places JSON to an HTML launcher for Apple Maps.")
    parser.add_argument("input", type=Path, help="Input JSON (e.g. 'Labeled places.json').")
    parser.add_argument("output", type=Path, help="Output HTML (e.g. 'saved_places.html').")
    args = parser.parse_args()

    data = load_json(args.input)
    entries = json_to_entries(data)
    html_doc = entries_to_html(entries, title="Saved Places → Apple Maps")

    args.output.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()
