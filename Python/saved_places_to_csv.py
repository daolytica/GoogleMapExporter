#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_latlon_from_url(url: str) -> Optional[Tuple[float, float]]:
    """
    Try to extract latitude, longitude from google_maps_url.

    Works for URLs like:
      http://maps.google.com/?q=50.82253,-0.13150
    """
    if not url:
        return None

    # Direct ?q=lat,lon
    m = re.search(r"[?&]q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", url)
    if m:
        try:
            lat, lon = float(m.group(1)), float(m.group(2))
            return lat, lon
        except ValueError:
            pass

    # Fallback: parse query & inspect q
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    q_vals = qs.get("q")
    if not q_vals:
        return None

    q_raw = q_vals[0]
    q_text = unquote(q_raw.replace("+", " ")).strip()

    # If q is "lat,lon"
    m2 = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", q_text)
    if m2:
        try:
            lat, lon = float(m2.group(1)), float(m2.group(2))
            return lat, lon
        except ValueError:
            return None

    return None


def extract_lat_lon(feature: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    Extract latitude/longitude from:
      1) geometry.coordinates if non-zero
      2) google_maps_url (?q=lat,lon)
    """
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
            # Treat exact (0,0) as placeholder
            if not (abs(lat) < 1e-12 and abs(lon) < 1e-12):
                return lat, lon

    # 2. URL
    url = props.get("google_maps_url") or props.get("Google Maps URL")
    if isinstance(url, str):
        parsed = parse_latlon_from_url(url)
        if parsed:
            return parsed

    return None


def derive_name_from_url(url: str) -> Optional[str]:
    """
    Try to extract a human-readable name from ?q=... in the URL,
    but only if it isn't pure coordinates.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    q_vals = qs.get("q")
    if not q_vals:
        return None

    q_raw = q_vals[0]
    q_text = unquote(q_raw.replace("+", " ")).strip()

    # Skip if it's just lat,lon
    if re.match(r"^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$", q_text):
        return None

    # Google sometimes prefixes "m,"
    if q_text.lower().startswith("m,"):
        q_text = q_text[2:].strip()

    return q_text or None


def extract_name_and_notes(feature: Dict[str, Any], idx: int) -> Tuple[str, str]:
    props = feature.get("properties") or {}
    loc = props.get("location") or {}

    # 1. Prefer location.name
    name_val: Optional[str] = None
    if isinstance(loc, dict) and loc.get("name"):
        name_val = str(loc["name"])

    # 2. Derive from URL ?q=... text
    if not name_val:
        url = props.get("google_maps_url") or props.get("Google Maps URL")
        if isinstance(url, str):
            n = derive_name_from_url(url)
            if n:
                name_val = n

    # 3. Fallback to other label-ish fields
    if not name_val:
        for key in ("name", "Name", "title", "Title", "label", "Label"):
            if key in props and props[key]:
                name_val = str(props[key])
                break

    # 4. Last resort
    if not name_val:
        name_val = f"Saved Place {idx}"

    # Notes: date / address / comment
    notes_parts: List[str] = []
    if props.get("date"):
        notes_parts.append(f"Saved: {props['date']}")

    if isinstance(loc, dict) and loc.get("address"):
        notes_parts.append(f"Address: {loc['address']}")

    comment = props.get("Comment") or props.get("comment")
    if comment:
        notes_parts.append(str(comment))

    notes = " | ".join(notes_parts)
    return name_val, notes


def json_to_rows(data: Dict[str, Any]) -> List[Dict[str, str]]:
    features = data.get("features") or []
    rows: List[Dict[str, str]] = []

    for i, feat in enumerate(features, start=1):
        latlon = extract_lat_lon(feat)
        if latlon is None:
            # Skip entries we can't locate
            continue

        lat, lon = latlon
        props = feat.get("properties") or {}
        url = props.get("google_maps_url") or props.get("Google Maps URL") or ""
        name, notes = extract_name_and_notes(feat, i)

        rows.append(
            {
                "name": name,
                "latitude": f"{lat:.8f}",
                "longitude": f"{lon:.8f}",
                "url": url,
                "notes": notes,
            }
        )

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Convert Google Saved Places JSON to CSV for Apple Maps Guide tools."
    )
    parser.add_argument("input", type=Path, help="Input JSON (e.g. 'Labeled places.json').")
    parser.add_argument("output", type=Path, help="Output CSV (e.g. 'saved_places.csv').")
    args = parser.parse_args()

    data = load_json(args.input)
    rows = json_to_rows(data)

    fieldnames = ["name", "latitude", "longitude", "url", "notes"]
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
