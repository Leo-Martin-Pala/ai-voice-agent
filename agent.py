from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    # cartesia,
    # deepgram,
    azure,
    noise_cancellation,
    silero,
)

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="Sa oled kasulik AI kõne assistent nimega leo assistent. Palun tutvusta ennast, kui leo assistent, kui keegi sinuga räägib. räägitakse sinuga ainult telefonitsi, mis käib nii STT-LLM-TTS, niiet sa saad kuulda teisi.")


async def entrypoint(ctx: agents.JobContext):
    vad_model = silero.VAD.load()

    session = AgentSession(
        stt=azure.STT(
            language="et-EE"
        ),
        llm=openai.LLM(model="gpt-5-nano"),
        tts=azure.TTS(
            voice="et-EE-AnuNeural"
        ),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVCTelephony(), 
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,

        # agent_name is required for explicit dispatch
        agent_name="my-telephony-agent"
    ))
