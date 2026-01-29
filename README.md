# Google Saved Places → Apple Maps Converter

This project converts **Google Maps “Saved Places” (Google Takeout JSON)** into formats that can be opened easily on macOS/iOS and saved permanently in **Apple Maps** (Favorites or Guides).

Since Apple Maps does **not** support direct import of GPX/KML/JSON/CSV, this tool generates an **HTML launcher page** containing one-click Apple Maps links for each location. This allows fast, semi-bulk saving of places directly into Apple Maps.

This project converts **Google Maps “Saved Places” (Google Takeout JSON)** into a format that can be opened easily on macOS/iOS and saved permanently inside **Apple Maps** (Favorites or Guides).

Apple Maps does **not** support direct import of GPX, KML, JSON, or CSV files.
This tool generates an **HTML launcher page** that opens each location directly in Apple Maps, allowing fast semi-bulk saving.

## Features

- Extracts coordinates from Google Takeout:
  - `geometry.coordinates`
  - Coordinates embedded in `google_maps_url` (`?q=lat,lon`)
- Extracts names from:
  - `location.name`
  - `q=Place+Name` in Google Maps URLs
  - Fallback labels when missing
- Generates:
  - **HTML Launcher Page** with place names, Apple Maps links, Google Maps links, and metadata.
  - fallback coordinates embedded in `google_maps_url` (`?q=lat,lon`)
- Extracts names from:
  - `location.name`
  - text inside Google Maps URL (`?q=Place+Name`)
  - other fallback labels
- Generates:
  - **HTML Launcher Page** containing:
    - Place names
    - One-click **Open in Apple Maps** links
    - Google Maps links
    - Coordinates, dates, notes, addresses

Works on all devices, and relies on Apple Maps’ native “Add to Favorites / Add to Guide” buttons for permanent saving.

## Input Format (Google Takeout)

Export from:

    Google Takeout → Maps → Saved Places → Labeled places.json

Example:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "geometry": { "coordinates": [0, 0], "type": "Point" },
      "properties": {
        "date": "2025-01-01T12:00:00Z",
        "google_maps_url": "http://maps.google.com/?q=50.82253,-0.13150",
        "Comment": "..."
      }
    }
  ]
}
```

## Output Format (HTML Launcher)

Running the script produces:

    saved_places.html

This HTML file contains:
- A table of all places
- **Open in Apple Maps** links
- Google Maps URLs
- Coordinates + metadata

Open it → click a link → Apple Maps opens →
Click **Add to Favorites** or **Add to Guide** → saved permanently.

## Installation

Ensure Python 3 is installed:

```bash
python3 --version
```

## Usage

Clone your repository:

```bash
git clone https://gitlab.com/your-username/saved-places-applemaps.git
cd saved-places-applemaps
```

## Usage

Place your Google Takeout file in the project directory, then run:

```bash
python3 saved_places_to_html.py "Labeled places.json" saved_places.html
```

Open `saved_places.html` and click each **Open in Apple Maps** link, then save the location in Apple Maps.

Then:

1. Open `saved_places.html`
2. Click **Open in Apple Maps** for each location
3. In Apple Maps, click **Add to Favorites** or **Add to Guide**

Apple Maps syncs saved places through iCloud across Mac, iPhone, iPad.

## How It Works

Google Takeout often includes:
- Real coordinates
- Or fake `[0,0]` placeholders + real coordinates hidden in URL query strings

This tool:

1. Reads coordinates from `geometry.coordinates`
2. If `[0,0]`, extracts `lat,lon` from:

       google_maps_url → ?q=lat,lon

3. Extracts a readable name from:
   - `location.name`
   - `?q=Name+Text`
   - fallback fields
4. Generates an Apple Maps deep link:

       https://maps.apple.com/?ll=LAT,LON&q=NAME

Opening this link loads the location instantly inside Apple Maps.

## Apple Maps Limitations

- No Apple Maps API for importing locations
- No GPX/KML/JSON import
- No file format for Guide creation
- No programmatic Favorites import
- No AppleScript support

This tool provides the closest possible workflow using official, supported behaviour.

## Roadmap

- Grouping places by region/date
- Apple Shortcuts automation template
- macOS GUI wrapper app

## License

MIT License — see `LICENSE`.

Free for distribution, create with help of GPT
Reza Mirfayzi

