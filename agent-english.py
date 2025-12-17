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
from livekit.plugins.azure.tts import ProsodyConfig

load_dotenv()

# Allows choosing whether to have numbers with decimals or not.
def format_float(value: float, use_decimals: bool = True) -> str:
    if use_decimals:
        return f"{value:.1f}"
    return str(int(round(value)))


@function_tool()
async def get_weather(
    city: Annotated[str, "Exact city name for which the weather forecast is desired (e.g. London, New York)"]
) -> str:
    """Returns current weather conditions from OpenWeather API."""
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Sorry, API key is not configured. Please configure OPENWEATHER_API_KEY environment variable."
    
    try:
        # Geocoding for exact name and coordinates
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": city, "limit": 1, "appid": api_key}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data:
            return f"City '{city}' not found. Please check the city name."
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        city_name = geo_data[0].get("name", city)
        country = geo_data[0].get("country", "")

        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "lang": "en",
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
            return "Current weather data is missing."

        temp_fmt = format_float(temp)
        feels_fmt = format_float(feels_like)
        wind_speed_fmt = format_float(wind_speed)

        weather_info = f"""
Current weather conditions in {city_name}, {country} are as follows:
Air temperature is {temp_fmt} degrees (feels like {feels_fmt} degrees)
Wind speed is {wind_speed_fmt} meters per second
Humidity is {humidity} percent
Pressure is {pressure} hectopascals
{description}
        """.strip()
        return weather_info

    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {str(e)}"
    except KeyError:
        return f"City '{city}' not found. Please check the city name."
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@function_tool()
async def get_weather_forecast(
    city: Annotated[str, "Exact city name for which the weather forecast is desired (e.g. London, New York)"],
    days: Annotated[int, "Number of days for forecast (1-5)"] = 5
) -> str:
    """Returns up to 5-day forecast using OpenWeather API v2.5 /forecast (3h steps)."""
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Sorry, weather API key is not configured. Please configure OPENWEATHER_API_KEY environment variable."
    
    # Normalize days 1..5
    if days < 1:
        days = 1
    if days > 5:
        days = 5
    
    try:
        # Geocoding
        geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": city, "limit": 1, "appid": api_key}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data:
            return f"City '{city}' not found. Can you please say the city name again?"
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
            "lang": "en",
            "appid": api_key,
        }
        resp = requests.get(forecast_url, params=params, timeout=15)
        resp.raise_for_status()
        f_data = resp.json()

        entries = f_data.get("list", [])
        if not entries:
            return "Forecast data missing."

        tz_offset = f_data.get("city", {}).get("timezone", 0)  # in seconds

        # Group by date (local time = UTC + offset)
        grouped = defaultdict(list)
        for item in entries:
            dt_utc = datetime.utcfromtimestamp(item.get("dt"))
            local_dt = dt_utc + timedelta(seconds=tz_offset)
            date_key = local_dt.date()
            grouped[date_key].append(item)
        
        # Sorted dates
        dates_sorted = sorted(grouped.keys())
        # Limit to requested days
        dates_selected = dates_sorted[:days]

        forecast_info = f"Weather forecast for the next {len(dates_selected)} days in {city_name}, {country}:\n\n"

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
                hums.append(main.get("humidity") )
                presses.append(main.get("pressure") )
                w_arr = it.get("weather", [])
                if w_arr:
                    desc_list.append(w_arr[0].get("description", ""))
            # Filter None values
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
            
            avg_temp_fmt = format_float(avg_temp)
            min_temp_fmt = format_float(min_temp)
            max_temp_fmt = format_float(max_temp)
            wind_fmt = format_float(avg_wind)
            feels_fmt = format_float(avg_feels)

            forecast_info += f"On {day_name}, the weather is as follows:\n"
            forecast_info += f"Day's average temperature is {avg_temp_fmt} degrees, feels like {feels_fmt} degrees. \n"
            forecast_info += f"Day's minimum temperature is {min_temp_fmt} degrees and maximum temperature reaches {max_temp_fmt} degrees. \n"
            forecast_info += f"Average wind speed is {wind_fmt} meters per second, humidity is {avg_hum} percent and pressure is {avg_press} hectopascals. \n"
            if common_desc:
                forecast_info += f"General weather description: {common_desc}.\n\n"
            else:
                forecast_info += "\n"

        return forecast_info.strip()
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {str(e)}"
    except KeyError:
        return f"City '{city}' not found. Can you please say the city name again?"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
                instructions="""You are an English-speaking voice assistant.

STRICT RULE SET (FOLLOW EXACTLY, DO NOT EXPLAIN TO USER):
1. For every user message check: are they asking for
    a) current weather (weather, temperature, wind, humidity, pressure, clouds etc.) or
    b) forecast (words: forecast, tomorrow, day after tomorrow, next days, predict).
2. If (1a) and city is unambiguous -> IMMEDIATELY call get_weather.
3. If (1b) and city is unambiguous -> IMMEDIATELY call get_weather_forecast (days = user desire; if missing, use 5).
4. If asked about a county or region -> choose the largest city there (e.g. New York State -> New York City, California -> Los Angeles, etc.) and use that.
5. If asked about a country's weather -> use the capital (e.g. USA -> Washington D.C., UK -> London, etc.).
6. If city is unclear or multiple cities mentioned -> ask for clarification (do NOT use tool before clarity).
7. NEVER answer with weather data before the corresponding tool has been executed and result received.
8. After receiving tool result, answer the end user IMMEDIATELY without mentioning the tool.
9. If "current weather" for the same city is asked again within <5 min, you may answer without new call; for forecast always make a new call if days differ.
10. If message is not about weather or forecast -> answer normally, without calling tools.
11. If user gives multiple cities in one sentence and doesn't specify which one interests them -> ask which city.

STYLE:
- Only English language.
- Do not use markdown, code formatting, emoticons or emojis.
- In weather description, write ALL numbers as words (13.2 -> "thirteen point two").
- Be detailed and verbal: temperature, feels like temperature, wind speed, humidity, pressure, general description. Explain these in full sentences.
- Never say you use or used a function.

DECISION PROTOCOL (INTERNAL THOUGHT, DO NOT OUTPUT): "Does message contain weather or forecast indicators? If yes -> choose right tool or ask city. If no -> normal answer."

FORBIDDEN:
- "I am using get_weather..." or other tool meta-talk.
- Weather numbers as raw data without converting to words.
- Weather answer without preceding tool call (if city exists).

EXAMPLES:
[USER] What is the weather like in London today?
[YOU] (call get_weather(city="London"); after tool result) In London, it is currently ... (numbers as words, detailed description).

[USER] Forecast for Paris for the next 3 days.
[YOU] (get_weather_forecast(city="Paris", days=3); then immediate answer) The forecast for Paris for the next three days is as follows, on the first day ...

[USER] How are you?
[YOU] (Do NOT use tool) I am doing well, thank you for asking ...

[BAD] "I need to use get_weather function now." (DO NOT DO THIS)

END: FOLLOW RULES EXACTLY.
""",
            tools=[get_weather, get_weather_forecast]
        )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=cartesia.STT(language="en"),
        llm=openai.LLM(model="gpt-5-chat-latest"),
        tts=azure.TTS(
            voice="en-US-JennyNeural",
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
        instructions="Tell the user that you are their weather forecaster. Please ask which city's weather they would like to know. Mention that you can forecast any city's weather up to 5 days ahead."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="my-telephony-agent"
    ))