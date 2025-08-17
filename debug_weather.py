#!/usr/bin/env python3
"""debug_weather.py
Lihtne käsurea tööriist get_weather ja get_weather_forecast funktsioonide kiireks testimiseks.

Kasutusnäited:
  python debug_weather.py Tallinn
  python debug_weather.py Tallinn --forecast 5
  python debug_weather.py Tallinn Tartu Pärnu --forecast 2
  python debug_weather.py Tallinn --no-current --forecast 4
  python debug_weather.py --cities failiga_linnad.txt --forecast 3

Keskkond:
  Vajalik on .env või keskkonnamuutuja OPENWEATHER_API_KEY
"""

from __future__ import annotations
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv

MAX_FORECAST_DAYS = 5  # OpenWeather 2.5 /forecast annab kuni ~5 päeva

# Lae .env kui olemas
load_dotenv()

# Impordi funktsioonid
try:
    from agent import get_weather, get_weather_forecast  # type: ignore
except ImportError as e:
    print("[VIGA] Ei suutnud importida agent.py funktsioone:", e, file=sys.stderr)
    sys.exit(1)


def read_cities_file(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        print(f"[HOIATUS] Linnade faili ei leitud: {path}")
        return []
    cities: List[str] = []
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        cities.append(line)
    return cities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ilma funktsioonide testija")
    parser.add_argument('cities', nargs='*', help='Linna(d), mille ilma kontrollida')
    parser.add_argument('--cities-file', dest='cities_file', help='Fail, millest lugeda linnad (üks rida = üks linn)')
    parser.add_argument('--forecast', type=int, default=None, help=f'Kui määratud, toob ka prognoosi (1-{MAX_FORECAST_DAYS} päeva)')
    parser.add_argument('--no-current', action='store_true', help='Ära kuva praegust ilma, ainult prognoos')
    parser.add_argument('--only-current', action='store_true', help='Ainult praegune ilm, ignoreeri prognoosi')
    parser.add_argument('--raw', action='store_true', help='Ära lisa vormindavaid eraldajaid (sobib logimiseks)')
    return parser


async def process_city(city: str, show_current: bool, forecast_days: int | None, raw: bool):
    header = f"===== {city} =====" if not raw else ''
    if header:
        print(header)
    if show_current:
        current = await get_weather(city)
        print(current)
        if not raw:
            print()
    if forecast_days is not None and forecast_days > 0:
        forecast = await get_weather_forecast(city, days=forecast_days)
        print(forecast)
    if not raw:
        print()


async def main_async(args):
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        print('[VIGA] OPENWEATHER_API_KEY puudub. Lisa see .env faili või ekspordi keskkonda.')
        return 2

    cities: List[str] = []
    if args.cities_file:
        cities.extend(read_cities_file(args.cities_file))
    cities.extend(args.cities)
    # Eemalda duplikaadid, säilita järjekord
    seen = set()
    cities_unique = []
    for c in cities:
        if c not in seen:
            cities_unique.append(c)
            seen.add(c)

    if not cities_unique:
        print('[VIGA] Ühtegi linna ei antud. Lisa linn käsureal või kasuta --cities-file.')
        return 3

    forecast_days = None
    if args.only_current:
        forecast_days = None
    else:
        if args.forecast is not None:
            # normaliseeri vahemikku 1..MAX_FORECAST_DAYS
            if args.forecast < 1:
                forecast_days = 1
            elif args.forecast > MAX_FORECAST_DAYS:
                forecast_days = MAX_FORECAST_DAYS
            else:
                forecast_days = args.forecast
    show_current = not args.no_current
    if args.only_current:
        show_current = True

    for city in cities_unique:
        try:
            await process_city(city, show_current=show_current, forecast_days=forecast_days, raw=args.raw)
        except Exception as e:  # pragma: no cover
            print(f"[VIGA] Linnaga '{city}' tekkis ootamatu erind: {e}")

    return 0


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        exit_code = asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print('\n[INFO] Katkestatud kasutaja poolt.')
        exit_code = 130
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
