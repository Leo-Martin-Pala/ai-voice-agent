from dotenv import load_dotenv
import os
import requests
import json
from typing import Annotated
from datetime import datetime

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool
from livekit.plugins import (
    azure,
    noise_cancellation,
    google,
)
from google.genai import types
from google.genai.types import Modality
from livekit.plugins.azure.tts import ProsodyConfig

load_dotenv()

# saab kasutada use_decimals=True ning kasutame koma, mitte punkti ("18,2"), mis aitab vältida kuupäeva lugemist.
def format_float(value: float, use_decimals: bool = True) -> str:
    if use_decimals:
        return f"{value:.1f}".replace(".", ",")  # kasutab koma, mitte punkti
    return str(int(round(value)))


@function_tool()
async def get_weather(
    city: Annotated[str, "Linna nimi, mille ilma soovitakse teada"]
) -> str:
    """Tagastab praegused ilmatingimused määratud linna jaoks OpenWeatherMap-st."""
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Vabandust, API võti pole seadistatud. Palun seadistage OPENWEATHER_API_KEY keskkonnamuutuja."
    
    try:
        # Get current weather
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "et"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        city_name = data["name"]
        country = data["sys"]["country"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        description = data["weather"][0]["description"]
        wind_speed = data["wind"]["speed"]
        
        # Ümardatud väärtused TTS jaoks
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
    except KeyError as e:
        return f"Linna '{city}' ei leitud. Palun kontrollige linna nime õigsust."
    except Exception as e:
        return f"Ootamatu viga: {str(e)}"


@function_tool()
async def get_weather_forecast(
    city: Annotated[str, "Linna nimi, mille ilmaprognoosi soovitakse teada"],
    days: Annotated[int, "Päevade arv prognoosiks (1-5)"] = 3
) -> str:
    """Tagastab ilmaprognoosi määratud linna jaoks kuni 5 päeva ette OpenWeatherMap API-st."""
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Vabandust, ilma API võti pole seadistatud. Palun seadistage OPENWEATHER_API_KEY keskkonnamuutuja."
    
    if days < 1 or days > 5:
        days = 3
    
    try:
        # Get weather forecast
        url = f"http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "et"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        city_name = data["city"]["name"]
        country = data["city"]["country"]

        forecast_info = f"Ilmaprognoos järgmiseks {days} päevaks {country} linnas {city_name},:\n\n"

        # Group forecasts by day
        current_day = None
        day_count = 0
        
        for item in data["list"]:
            if day_count >= days:
                break
                
            date = item["dt_txt"].split(" ")[0]
            time = item["dt_txt"].split(" ")[1]
            
            # Only show midday forecasts (12:00) for each day
            if time == "12:00:00":
                if current_day != date:
                    current_day = date
                    day_count += 1
                    
                    if day_count > days:
                        break
                
                temp = item["main"]["temp"]
                description = item["weather"][0]["description"]
                wind_speed = item["wind"]["speed"]
                humidity = item["main"]["humidity"]
                
                temp_fmt = format_float(temp)
                wind_speed_fmt = format_float(wind_speed)

                # Translate day names to Estonian
                day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
                day_names_et = {
                    "Monday": "Esmaspäeval",
                    "Tuesday": "Teisipäeval", 
                    "Wednesday": "Kolmapäeval",
                    "Thursday": "Neljapäeval",
                    "Friday": "Reedel",
                    "Saturday": "Laupäeval",
                    "Sunday": "Pühapäeval"
                }
                
                day_name_et = day_names_et.get(day_name, day_name)
                
                forecast_info += f"{day_name_et} on\n"
                forecast_info += f"õhutemperatuur {temp_fmt} kraadi\n"
                forecast_info += f"Tuulekiirus on {wind_speed_fmt} meetrit sekundis ja õhuniiskus on {humidity} protsenti\n"
                forecast_info += f"{description}\n\n"
        
        return forecast_info.strip()
        
    except requests.exceptions.RequestException as e:
        return f"Viga ilmaandmete hankimisel: {str(e)}"
    except KeyError as e:
        return f"Linna '{city}' ei leitud. Kas saad palun uuesti linna nime öelda?"
    except Exception as e:
        return f"Ootamatu viga: {str(e)}"


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""Oled kasulik eesti keelt kõnelev häälassistent. 
OLULINE:
- Räägi ALATI eesti keeles
- Vasta kõikidele küsimustele, mida küsitakse
- Ole sõbralik ja abivalmis
- Kui ei mõista küsimust, küsi täpsustust
- Ära kasuta markdown teksti ega koodi vormingut

ILMAANDMED:
- Kui kasutaja küsib ilma kohta, kasuta get_weather funktsiooni praeguste tingimuste jaoks
- Kui küsitakse ilmaprognoosi, kasuta get_weather_forecast funktsiooni
- Kirjuta kõik sümbolid sõnadega välja, näiteks "13,2 kraadi" asemel "kolmteist koma kaks kraadi"
- Ole väga verboosne ilmaandmete kirjeldamisel. Kirjuta kõik pikalt välja. näiteks (temp 13.2°C, tuul 3.5 m/s kirjelda niimodi -> temperatuur on kolmteist koma kaks kraadi ning tuule kiirus on kolm koma viis meetrit sekundis)

VASTAMISE STIIL:
- Ole loomlik ja vestluslik
- Anna täpseid vastuseid
- Ole alati positiivne ja abivalmis
- ära kasuta emotikone ja emojisid
""",
            tools=[get_weather, get_weather_forecast]
        )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        llm=google.beta.realtime.RealtimeModel(
            # model="gemini-2.5-flash-live-preview",
            model="gemini-2.0-flash-live-001",
            modalities=[Modality.TEXT],
        ),
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
        instructions="Ütle kasutajale, et oled tema ilma sünoptik. Palun küsi, millise linna ilma soovitakse teada."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,

        # agent_name is required for explicit dispatch
        agent_name="my-telephony-agent"
    ))
