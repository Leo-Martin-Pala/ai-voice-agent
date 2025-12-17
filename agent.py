from dotenv import load_dotenv
import os
import requests
from typing import Annotated
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool
from livekit.plugins import (
    azure,
    noise_cancellation,
    google,
    cartesia,
    silero,
    openai,
)
from google.genai.types import Modality
from livekit.plugins.azure.tts import ProsodyConfig

load_dotenv()

# saab valida, kas tahta arve komakohtadega või mitte.
def format_float(value: float, use_decimals: bool = True) -> str:
    if use_decimals:
        return f"{value:.1f}".replace(".", ",")  # kasutab koma, mitte punkti
    return str(int(round(value)))


@function_tool()
async def get_weather(
    city: Annotated[str, "Täpne, käändeta, linna nimi, mille ilmaprognoosi soovitakse teada (nt Tartus -> Tartu, Tallinnas -> Tallinn)"]
) -> str:
    """Tagastab praegused ilmatingimused OpenWeather API-st."""
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Vabandust, API võti pole seadistatud. Palun seadistage OPENWEATHER_API_KEY keskkonnamuutuja."
    
    try:
        # Geokodeerimine täpse nime ja koordinaatide jaoks
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": city, "limit": 1, "appid": api_key}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data:
            return f"Linna '{city}' ei leitud. Palun kontrollige linna nime õigsust."
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        city_name = geo_data[0].get("name", city)
        country = geo_data[0].get("country", "")

        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "lang": "et",
            "appid": api_key,
        }
        response = requests.get(weather_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        weather_arr = data.get("weather", [])
        description = weather_arr[0].get("description", "") if weather_arr else ""

        temp = main.get("temp")
        feels_like = main.get("feels_like")
        humidity = main.get("humidity")
        pressure = main.get("pressure")
        wind_speed = wind.get("speed")

        if temp is None:
            return "Praegused ilma andmed puuduvad."

        temp_fmt = format_float(temp)
        feels_fmt = format_float(feels_like)
        wind_speed_fmt = format_float(wind_speed)

        weather_info = f"""
Praegused ilmatingimused {country} linnas {city_name} on järgmised:
Õhutemperatuur on {temp_fmt} kraadi (tundub nagu {feels_fmt} kraadi)
Tuule kiirus on {wind_speed_fmt} meetrit sekundis
Õhu niiskus on {humidity} protsenti
Õhurõhk on {pressure} hektopaskali
{description}
        """.strip()
        return weather_info

    except requests.exceptions.RequestException as e:
        return f"Viga ilmaandmete hankimisel: {str(e)}"
    except KeyError:
        return f"Linna '{city}' ei leitud. Palun kontrollige linna nime õigsust."
    except Exception as e:
        return f"Ootamatu viga: {str(e)}"


@function_tool()
async def get_weather_forecast(
    city: Annotated[str, "Täpne, käändeta, linna nimi, mille ilmaprognoosi soovitakse teada (nt Tartus -> Tartu, Tallinnas -> Tallinn)"],
    days: Annotated[int, "Päevade arv prognoosiks (1-5)"] = 5
) -> str:
    """Tagastab kuni 5-päevase prognoosi kasutades OpenWeather API v2.5 /forecast (3h sammuga) endpointi.
    Töötlemine:
    - Grupi 3h kirjete loend kuupäeva (kohalik aeg) järgi
    - Arvutab iga päeva min/maks temperatuuri, keskmise päeva temperatuuri, keskmise tunde temperatuuri (feels_like), keskmise tuule kiiruse, keskmise niiskuse, keskmise rõhu
    - Võtab kõige sagedasema ilma kirjelduse
    NB: Tasuta /forecast annab kuni ~5 päeva (40 * 3h kirjet)."""
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Vabandust, ilma API võti pole seadistatud. Palun seadistage OPENWEATHER_API_KEY keskkonnamuutuja."
    
    # Normaliseeri päevade arv 1..5
    if days < 1:
        days = 1
    if days > 5:
        days = 5
    
    try:
        # Geokodeerimine
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": city, "limit": 1, "appid": api_key}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data:
            return f"Linna '{city}' ei leitud. Kas saad palun uuesti linna nime öelda?"
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        city_name = geo_data[0].get("name", city)
        country = geo_data[0].get("country", "")

        # /data/2.5/forecast
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "lang": "et",
            "appid": api_key,
        }
        resp = requests.get(forecast_url, params=params, timeout=15)
        resp.raise_for_status()
        f_data = resp.json()

        entries = f_data.get("list", [])
        if not entries:
            return "Prognoosi andmed puuduvad."

        tz_offset = f_data.get("city", {}).get("timezone", 0)  # sekundites

        # Grupeeri kuupäeva järgi (kohalik aeg = UTC + offset)
        grouped = defaultdict(list)
        for item in entries:
            dt_utc = datetime.utcfromtimestamp(item.get("dt"))
            local_dt = dt_utc + timedelta(seconds=tz_offset)
            date_key = local_dt.date()
            grouped[date_key].append(item)
        
        # Sorteeritud kuupäevad
        dates_sorted = sorted(grouped.keys())
        # Piira soovitud päevade arvuga
        dates_selected = dates_sorted[:days]

        day_names_et = {
            "Monday": "Esmaspäeval",
            "Tuesday": "Teisipäeval", 
            "Wednesday": "Kolmapäeval",
            "Thursday": "Neljapäeval",
            "Friday": "Reedel",
            "Saturday": "Laupäeval",
            "Sunday": "Pühapäeval"
        }

        forecast_info = f"Ilmaprognoos järgnevaks {len(dates_selected)} päevaks {country} linnas {city_name}:\n\n"

        for date_key in dates_selected:
            items = grouped[date_key]
            temps = []
            temps_min = []
            temps_max = []
            feels = []
            winds = []
            hums = []
            presses = []
            desc_list = []
            for it in items:
                main = it.get("main", {})
                temps.append(main.get("temp"))
                temps_min.append(main.get("temp_min"))
                temps_max.append(main.get("temp_max"))
                feels.append(main.get("feels_like"))
                winds.append(it.get("wind", {}).get("speed"))
                hums.append(main.get("humidity"))
                presses.append(main.get("pressure"))
                w_arr = it.get("weather", [])
                if w_arr:
                    desc_list.append(w_arr[0].get("description", ""))
            # Filtreeri None väärtused
            def clean(vals):
                return [v for v in vals if v is not None]
            temps_c = clean(temps)
            temps_min_c = clean(temps_min)
            temps_max_c = clean(temps_max)
            feels_c = clean(feels)
            winds_c = clean(winds)
            hums_c = clean(hums)
            presses_c = clean(presses)
            
            if not temps_c:
                continue
            avg_temp = sum(temps_c)/len(temps_c)
            avg_feels = sum(feels_c)/len(feels_c) if feels_c else avg_temp
            min_temp = min(temps_min_c or temps_c)
            max_temp = max(temps_max_c or temps_c)
            avg_wind = sum(winds_c)/len(winds_c) if winds_c else 0.0
            avg_hum = int(round(sum(hums_c)/len(hums_c))) if hums_c else 0
            avg_press = int(round(sum(presses_c)/len(presses_c))) if presses_c else 0
            common_desc = ""
            if desc_list:
                common_desc = Counter(desc_list).most_common(1)[0][0]

            day_name = date_key.strftime("%A")
            day_name_et = day_names_et.get(day_name, day_name)

            avg_temp_fmt = format_float(avg_temp)
            min_temp_fmt = format_float(min_temp)
            max_temp_fmt = format_float(max_temp)
            wind_fmt = format_float(avg_wind)
            feels_fmt = format_float(avg_feels)

            forecast_info += f"{day_name_et} on ilm järgmine:\n"
            forecast_info += f"päeva keskmine temperatuur on {avg_temp_fmt} kraadi, mis tundub nagu {feels_fmt} kraadi. \n"
            forecast_info += f"Päeva miinimum temperatuur on {min_temp_fmt} kraadi ja maksimum temperatuur ulatub {max_temp_fmt} kraadini. \n"
            forecast_info += f"Tuule keskmine kiirus on {wind_fmt} meetrit sekundis, õhuniiskus on {avg_hum} protsenti ning õhurõhk on {avg_press} hektopaskalit. \n"
            if common_desc:
                forecast_info += f"Üldine ilma kirjeldus: {common_desc}.\n\n"
            else:
                forecast_info += "\n"

        return forecast_info.strip()
        
    except requests.exceptions.RequestException as e:
        return f"Viga ilmaandmete hankimisel: {str(e)}"
    except KeyError:
        return f"Linna '{city}' ei leitud. Kas saad palun uuesti linna nime öelda?"
    except Exception as e:
        return f"Ootamatu viga: {str(e)}"


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
                instructions="""Oled eesti keelt kõnelev häälassistent.

KINDEL REEGLIKOMPLEKT (JÄRGI TÄPSELT, ÄRA SELGITA KASUTAJALE):
1. Iga kasutaja sõnumi puhul kontrolli: kas ta küsib
    a) praegust ilma (ilm, temperatuur, tuul, niiskus, rõhk, pilvisus jmt) või
    b) prognoosi (sõnad: prognoos, homme, ülehomme, järgmised, mitu päeva, ennusta).
2. Kui (1a) ja linn on üheselt mõistetav -> KOHE kutsu get_weather.
3. Kui (1b) ja linn on üheselt mõistetav -> KOHE kutsu get_weather_forecast (days = kasutaja soov; kui puudub, kasuta 5).
4. Kui küsitakse maakonna või valla kohta -> vali suurim linn seal (nt Tartu, Pärnu, Narva, Põlva jne) ja kasuta seda.
5. Kui küsitakse riigi ilma -> kasuta pealinna (nt Eesti -> Tallinn, Läti -> Riia, Leedu -> Vilnius jne).
6. Kui linn pole selge või mitu linna mainitud -> küsi täpsustust (ära kasuta tööriista enne selgust).
7. ÄRA kunagi vasta ilmaandmetest enne kui vastav tööriist on käivitatud ja tulemus käes.
8. Pärast tööriista tulemuse saamist vasta KOHE lõppkasutajale ilma tööriista mainimata.
9. Kui sama linna "praegust ilma" küsitakse uuesti <5 min jooksul, võid vastata ilma uut kutset tegemata; prognoosi puhul tee alati uus kutse kui päeva arv erineb.
10. Kui sõnum ei puuduta ilma ega prognoosi -> vasta tavaliselt, ilma tööriistu kutsumata.
11. Kui kasutaja annab mitu linna ühes lauses ja ei täpsusta kumb huvitab -> küsi kumb linn.

STIIL:
- Ainult eesti keel.
- Ära kasuta markdown'i, koodi vormingut, emotikone ega emojisid.
- Ilma kirjelduses kirjuta KÕIK numbrid sõnadena (13,2 -> "kolmteist koma kaks").
- Ole detailne ja verbaalne: temperatuur, tuntav temperatuur, tuule kiirus, niiskus, rõhk, üldine kirjeldus. Selgita need täislausetena.
- Ära ütle kunagi, et kasutad või kasutasid funktsiooni.

OTSUSTUSPROTOKOLL (SISENEMÕTE, ÄRA VÄLJASTA): "Kas sõnum sisaldab ilma või prognoosi indikaatoreid? Kui jah -> vali õige tööriist või küsi linna. Kui ei -> tavaline vastus."

KEELATUD:
- "Ma kasutan get_weather..." või muu tööriista meta-jutt.
- Ilma numbrid toorandmetena ilma sõnadeks teisendamata.
- Ilmavastus ilma tööriista eelnevata (kui linn olemas).

NÄITED:
[KASUTAJA] Mis ilm täna Tartus on?
[SINA] (tee get_weather(city="Tartu") tööriista kutse; pärast tööriista tulemust) Tartus on praegu ... (numbrid sõnadena, detailne kirjeldus).

[KASUTAJA] Ennusta Tallinna ilma järgmised 3 päeva.
[SINA] (get_weather_forecast(city="Tallinn", days=3); siis kohe vastus) Tallinna järgmise kolme päeva prognoos on selline, esimesel päeval ...

[KASUTAJA] Kuidas sul läheb?
[SINA] (Tööriista EI kasuta) Mul läheb hästi, aitäh küsimast ...

[HALB] "Ma pean nüüd kasutama get_weather funktsiooni." (ÄRA NII TEE)

LÕPP: JÄRGI REEGLEID TÄPSELT.
""",
            tools=[get_weather, get_weather_forecast]
        )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=cartesia.STT(language="en"),
        llm=openai.LLM(model="gpt-5-nano"),
        tts=azure.TTS(
            voice="et-EE-AnuNeural",
            prosody=ProsodyConfig(rate=1.2)
        ),
    )
    
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(), 
        ),
    )

    await session.generate_reply(
        instructions="Ütle kasutajale, et oled tema ilma sünoptik. Palun küsi, millise linna ilma soovitakse teada. Maini, et suudad ennustata iga linna ilma kuni 5 päeva ette."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="my-telephony-agent"
    ))
