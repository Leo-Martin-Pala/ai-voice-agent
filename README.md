# AI Voice Agent with Weather Integration

An Estonian-speaking voice AI agent built with LiveKit Agents framework, enhanced with weather data capabilities through OpenWeatherMap API.

## Features

- 🎤 **Voice Interaction**: Real-time voice conversations in Estonian
- 🇬🇧 **English Support**: Optional English-speaking weather agent available
- 🌡️ **Weather Information**: Current weather conditions and forecasts
- 📅 **Weather Forecasts**: Up to 5-day weather predictions
- 🇪🇪 **Estonian Language**: Full Estonian language support for weather data

## Weather Capabilities

The agent can provide:
- Weather descriptions in Estonian
- Current weather conditions for any city
- Weather forecasts up to 5 days
- Temperature, humidity, wind speed, and pressure information

### Example Weather Queries

Users can ask questions like:
- "Milline on ilm Tallinnas?" (What's the weather in Tallinn?)
- "Mis ilm on homme Tartus?" (What's the weather tomorrow in Tartu?)
- "Anna mulle 5-päevane ilmaprognoos Paide jaoks" (Give me a 5-day forecast for Paide)

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file and configure the following API keys:

```env
# LiveKit Configuration
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Google Gemini API (for LLM)
GOOGLE_API_KEY=your_google_api_key

# Azure Speech Services (for TTS)
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=your_azure_region

# OpenWeatherMap API (for weather data)
OPENWEATHER_API_KEY=your_openweather_api_key
```

### 4. Get API Keys

- **OpenWeatherMap**: Free API key from [openweathermap.org](https://openweathermap.org/api)
- **Google Gemini**: API key from [Google AI Studio](https://aistudio.google.com/)
- **Azure Speech**: Speech Services key from [Azure Portal](https://portal.azure.com/)
- **LiveKit**: Account and keys from [LiveKit Cloud](https://cloud.livekit.io/)

### 5. Configure Telephony

Follow LiveKit's guide to configure your telephony/SIP provider:
- Docs: https://docs.livekit.io/sip/
- Set up your SIP trunk with your provider and connect it in LiveKit
- Create an inbound rule to route calls to your agent

## Running the Agent

### Install required model files
```bash
pip agent.py download-files
```

### Console Mode
```bash
python agent.py console
```

### Development Mode
```bash
python agent.py dev
```

### Production Mode
```bash
python agent.py start
```

### Running English Agent
To run the English version of the agent:
```bash
python agent-english.py dev
```

### Test Weather Functions
```bash
python debug_weather.py --help
```

## Architecture

The agent is built using:
- **LiveKit Agents**: Framework for real-time voice AI
- **Google Gemini 2.5 Flash**: Advanced language model with real-time capabilities
- **Azure TTS**: Estonian text-to-speech synthesis
- **OpenWeatherMap API**: Weather data provider
- **Function Tools**: Weather integration through LiveKit's tool system