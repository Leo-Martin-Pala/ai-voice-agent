# AI Voice Agent with Weather Integration

An Estonian-speaking voice AI agent built with LiveKit Agents framework, enhanced with weather data capabilities through OpenWeatherMap API.

## Features

- 🎤 **Voice Interaction**: Real-time voice conversations in Estonian
- 🌡️ **Weather Information**: Current weather conditions and forecasts
- 📅 **Weather Forecasts**: Up to 5-day weather predictions
- 🇪🇪 **Estonian Language**: Full Estonian language support for weather data
- 🔊 **Text-to-Speech**: Azure TTS with Estonian voice (et-EE-AnuNeural)
- 🎯 **Noise Cancellation**: Enhanced BVC telephony noise cancellation

## Weather Capabilities

The agent can provide:
- Current weather conditions for any city
- Weather forecasts up to 5 days
- Temperature, humidity, wind speed, and pressure information
- Weather descriptions in Estonian
- Localized day names and formatting

### Example Weather Queries

Users can ask questions like:
- "Milline on ilm Tallinnas?" (What's the weather in Tallinn?)
- "Mis ilm on homme Tartus?" (What's the weather tomorrow in Tartu?)
- "Anna mulle 5-päevane ilmaprognoos Paide jaoks" (Give me a 5-day forecast for Paide)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

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

### 3. Get API Keys

- **OpenWeatherMap**: Free API key from [openweathermap.org](https://openweathermap.org/api)
- **Google Gemini**: API key from [Google AI Studio](https://aistudio.google.com/)
- **Azure Speech**: Speech Services key from [Azure Portal](https://portal.azure.com/)
- **LiveKit**: Account and keys from [LiveKit Cloud](https://cloud.livekit.io/)

## Running the Agent

### Development Mode
```bash
python agent.py dev
```

### Production Mode
```bash
python agent.py start
```

### Test Weather Functions
```bash
python test_weather.py
```

## Architecture

The agent is built using:
- **LiveKit Agents**: Framework for real-time voice AI
- **Google Gemini 2.0 Flash**: Advanced language model with real-time capabilities
- **Azure TTS**: Estonian text-to-speech synthesis
- **OpenWeatherMap API**: Weather data provider
- **Function Tools**: Weather integration through LiveKit's tool system

## Project Structure

```
├── agent.py                 # Main agent implementation
├── requirements.txt         # Python dependencies
├── test_weather.py         # Weather function testing
├── WEATHER_README.md       # Detailed weather setup guide
├── dispatch-rule.json     # LiveKit dispatch configuration
└── .env                   # Environment variables (create this)
```

## Deployment

The agent supports deployment to:
- LiveKit Cloud Agents (managed service)
- Kubernetes clusters
- Docker containers
- Various cloud platforms

For production deployment, see the [LiveKit Agents deployment guide](https://docs.livekit.io/agents/deployment/).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.