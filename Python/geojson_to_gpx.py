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

    # Look for ?q=lat,lon
    m = re.search(r"[?&]q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", url)
    if m:
        try:
            lat, lon = float(m.group(1)), float(m.group(2))
            return lat, lon
        except ValueError:
            pass

    # Fallback: parse query
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "q" not in qs:
        return None

    q_raw = qs["q"][0]
    q_text = unquote(q_raw.replace("+", " ")).strip()

    # Check for coords
    m2 = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", q_text)
    if m2:
        try:
            lat, lon = float(m2.group(1)), float(m2.group(2))
            return lat, lon
        except ValueError:
            return None

    return None


def extract_lat_lon(feature: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    geom = feature.get("geometry") or {}
    props = feature.get("properties") or {}

    # 1. geometry.coordinates
    if isinstance(geom, dict) and geom.get("type") == "Point":
        coords = geom.get("coordinates")
        if (
            isinstance(coords, list)
            and len(coords) >= 2
            and coords[0] is not None
            and coords[1] is not None
        ):
            lon, lat = float(coords[0]), float(coords[1])
            # Skip 0,0 placeholder
            if not (abs(lat) < 1e-12 and abs(lon) < 1e-12):
                return lat, lon

    # 2. google_maps_url
    url = props.get("google_maps_url") or props.get("Google Maps URL")
    if isinstance(url, str):
        parsed = parse_latlon_from_url(url)
        if parsed:
            return parsed

    return None


def derive_name_from_url(url: str) -> Optional[str]:
    """
    Extract a human-readable name from q=<text> in the URL,
    but only if q is NOT coordinates.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "q" not in qs:
        return None

    q_raw = qs["q"][0]
    q_text = unquote(q_raw.replace("+", " ")).strip()

    # Skip pure lat,lon
    if re.match(r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$", q_text):
        return None

    # Remove leading "m," garbage Google sometimes inserts
    if q_text.lower().startswith("m,"):
        q_text = q_text[2:].strip()

    return q_text if q_text else None


def extract_name_and_desc(feature: Dict[str, Any], idx: int) -> Tuple[str, str]:
    props = feature.get("properties") or {}
    loc = props.get("location") or {}

    # 1. Prefer location.name (exists for your recycling centre)
    if isinstance(loc, dict) and loc.get("name"):
        name_val = str(loc["name"])
    else:
        name_val = None

    # 2. Next: try q=<text> from URL
    if not name_val:
        url = props.get("google_maps_url") or props.get("Google Maps URL")
        if isinstance(url, str):
            name_from_url = derive_name_from_url(url)
            if name_from_url:
                name_val = name_from_url

    # 3. Next: try explicit name/title/label fields
    if not name_val:
        for key in ["name", "Name", "title", "Title", "label", "Label"]:
            if key in props and props[key]:
                name_val = str(props[key])
                break

    # 4. Final fallback
    if not name_val:
        name_val = f"Saved Place {idx}"

    # Build description
    parts: List[str] = []
    if props.get("date"):
        parts.append(f"Saved: {props['date']}")

    if isinstance(loc, dict) and loc.get("address"):
        parts.append(f"Address: {loc['address']}")

    url = props.get("google_maps_url") or props.get("Google Maps URL")
    if isinstance(url, str):
        parts.append(f"Google Maps: {url}")

    comment = props.get("Comment") or props.get("comment")
    if comment:
        parts.append(str(comment))

    desc_val = " | ".join(parts)

    return name_val, desc_val


def feature_to_wpt(feature: Dict[str, Any], idx: int) -> str:
    lat_lon = extract_lat_lon(feature)
    if lat_lon is None:
        return ""

    lat, lon = lat_lon
    name, desc = extract_name_and_desc(feature, idx)

    name_xml = html.escape(name, quote=True)
    desc_xml = html.escape(desc, quote=True)

    out = [
        f'  <wpt lat="{lat:.8f}" lon="{lon:.8f}">',
        f"    <name>{name_xml}</name>",
    ]
    if desc_xml:
        out.append(f"    <desc>{desc_xml}</desc>")
    out.append("  </wpt>")
    return "\n".join(out)


def json_to_gpx(data: Dict[str, Any]) -> str:
    features: List[Dict[str, Any]] = data.get("features") or []
    wpts = []

    for i, feat in enumerate(features, start=1):
        w = feature_to_wpt(feat, i)
        if w:
            wpts.append(w)

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="google-saved-to-gpx" '
        'xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
        'http://www.topografix.com/GPX/1/1/gpx.xsd">',
        *wpts,
        "</gpx>"
    ])


def main():
    parser = argparse.ArgumentParser(description="Convert Google Saved Places JSON to GPX.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = load_json(args.input)
    gpx = json_to_gpx(data)
    args.output.write_text(gpx, encoding="utf-8")
    print("GPX written:", args.output)


if __name__ == "__main__":
    main()
