# Written by Claude.ai to my specs
# Computes YTD cycling mileage from RideWithGPS and renders it as a
# small, size-conscious PNG for use as a BikeForums signature image.

import os
import asyncio
from datetime import datetime

import aiohttp
from aioridewithgps import RideWithGPSClient
from PIL import Image, ImageDraw, ImageFont

RWGPS_API_KEY = os.environ["RWGPS_API_KEY"]
RWGPS_AUTH_TOKEN = os.environ["RWGPS_AUTH_TOKEN"]
OUTPUT_PATH = "cycling_stats_sig.png"

# Flat, two-color palette keeps the PNG small.
BG_COLOR = (0xCA, 0x48, 0x6E)   # #CA486E
TEXT_COLOR = (255, 255, 255)    # white
WIDTH, HEIGHT = 400, 92

# Arial works locally on Windows; Liberation Sans is the fallback available
# on GitHub Actions' Ubuntu runners, so the same script renders correctly
# on both machines.
FONT_BOLD_CANDIDATES = ["arialbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
FONT_REGULAR_CANDIDATES = ["arial.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]

def load_font(candidates, size):
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


async def fetch_ytd_stats():
    current_year = datetime.now().year

    async with aiohttp.ClientSession() as session:
        client = RideWithGPSClient(session, api_key=RWGPS_API_KEY, auth_token=RWGPS_AUTH_TOKEN)
        trips = await client.get_all_trips()

    total_meters = 0.0
    total_elev_m = 0.0
    ride_count = 0
    longest_m = 0.0

    for trip in trips:
        if not trip.departed_at:
            continue
        trip_dt = datetime.fromisoformat(trip.departed_at)
        if trip_dt.year != current_year:
            continue
        dist = trip.distance or 0
        total_meters += dist
        total_elev_m += trip.elevation_gain or 0
        ride_count += 1
        longest_m = max(longest_m, dist)

    miles = total_meters / 1609.34
    feet = total_elev_m * 3.28084
    longest_mi = longest_m / 1609.34
    return current_year, miles, feet, ride_count, longest_mi


def render_png(year, miles, feet, ride_count, longest_mi, path):
    img = Image.new("P", (WIDTH, HEIGHT), color=0)
    img.putpalette(list(BG_COLOR) + list(TEXT_COLOR) + [0] * (256 * 3 - 6))
    draw = ImageDraw.Draw(img)

    font_header = load_font(FONT_BOLD_CANDIDATES, 18)
    font_body = load_font(FONT_REGULAR_CANDIDATES, 15)

    header = f"YTD {year}"
    line2 = f"{miles:,.0f} mi., {ride_count} rides, {feet:,.0f} ft ascent"
    line3 = f"Longest ride: {longest_mi:,.1f} mi."

    draw.text((10, 6), header, fill=1, font=font_header)
    draw.line((10, 30, WIDTH - 10, 30), fill=1, width=1)  # divider under header
    draw.text((10, 40), line2, fill=1, font=font_body)
    draw.text((10, 64), line3, fill=1, font=font_body)

    img.save(path, optimize=True)


async def main():
    year, miles, feet, ride_count, longest_mi = await fetch_ytd_stats()
    print(f"{year} YTD: {miles:.1f} mi, {feet:.0f} ft climbed, "
          f"{ride_count} rides, longest {longest_mi:.1f} mi")
    render_png(year, miles, feet, ride_count, longest_mi, OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)} bytes)")


asyncio.run(main())
