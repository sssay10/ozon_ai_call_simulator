import asyncio
import logging
import os

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.agents.stt import StreamAdapter
from livekit.plugins import openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from dialogue_logging import (
    DialogueLogger,
    make_conversation_item_callback,
    trigger_judge_session,
)
from session_settings import build_system_prompt, parse_session_metadata
from stt_tone import ToneSTT
from tts_silero import SileroTTS


logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(instructions=instructions)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm


def _extract_owner_user_id_from_room(ctx: JobContext) -> str:
    remote_participants = getattr(ctx.room, "remote_participants", None)
    if isinstance(remote_participants, dict):
        for participant in remote_participants.values():
            identity = str(getattr(participant, "identity", "") or "")
            if identity.startswith("app_user_"):
                return identity.removeprefix("app_user_")
    return ""


@server.rtc_session()
async def my_agent(ctx: JobContext):
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Session settings from UI (agent dispatch metadata)
    meta = parse_session_metadata(ctx.job.metadata or "")
    if not isinstance(meta.get("prompt_blocks"), dict):
        raise ValueError("prompt_blocks are required in session metadata")
    scenario_label = meta.get("training_scenario_name") or meta.get("training_scenario_id") or None
    instructions = build_system_prompt(
        prompt_blocks=meta["prompt_blocks"],
        scenario_label=scenario_label if isinstance(scenario_label, str) and scenario_label.strip() else None,
    )
    log_product = meta.get("product") or meta.get("training_scenario_name") or ""
    logger.info(
        "session settings: scenario_id=%s scenario_name=%s product=%s",
        meta.get("training_scenario_id", ""),
        meta.get("training_scenario_name", ""),
        log_product,
    )
    logger.info("system prompt length=%s chars (log level DEBUG for full text)", len(instructions))
    logger.debug("full system prompt:\n%s", instructions)

    # STT: T-one via STT service (set STT_SERVICE_URL in .env.local, e.g. http://localhost:8001)
    tone_stt = ToneSTT(base_url=os.environ["STT_SERVICE_URL"])
    stt = StreamAdapter(stt=tone_stt, vad=ctx.proc.userdata["vad"])

    # LLM: choose between local Ollama and OpenRouter (default)
    llm_provider = os.environ.get("LLM_PROVIDER", "openrouter").lower()
    if llm_provider == "ollama":
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.1")
        ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        logger.info("LLM provider=ollama model=%s base_url=%s", ollama_model, ollama_base)
        llm = openai.LLM.with_ollama(
            model=ollama_model,
            base_url=ollama_base,
        )
    else:
        openrouter_model = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
        logger.info(
            "LLM provider=openrouter model=%s temperature=0.3",
            openrouter_model,
        )
        llm = openai.LLM.with_openrouter(
            model=openrouter_model,
            temperature=0.3,
        )

    # TTS: Silero v5 Russian via TTS service (set TTS_SERVICE_URL in .env.local, e.g. http://localhost:8002)
    tts = SileroTTS(base_url=os.environ["TTS_SERVICE_URL"])

    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(instructions=instructions),
        room=ctx.room,
    )

    # Join the room and connect to the user
    await ctx.connect()

    owner_user_id = meta["owner_user_id"] or _extract_owner_user_id_from_room(ctx)

    # Optional: dialogue logging to Postgres (DATABASE_URL)
    dialogue_logger = None
    db_session_id = None
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        dialogue_logger = DialogueLogger(database_url)
        db_product = log_product or "training"
        db_session_id = await dialogue_logger.create_session(
            room_name=ctx.room.name,
            job_id=getattr(ctx.job, "id", None) or "",
            product=db_product,
            owner_user_id=owner_user_id,
            training_scenario_id=meta.get("training_scenario_id", ""),
        )
        if db_session_id:
            loop = asyncio.get_running_loop()
            session.on(
                "conversation_item_added",
                make_conversation_item_callback(dialogue_logger, db_session_id, loop),
            )

            async def _finalize_session(_reason: str) -> None:
                await asyncio.sleep(0.5)
                await dialogue_logger.end_session(db_session_id)
                judge_service_url = os.environ.get("JUDGE_SERVICE_URL")
                if judge_service_url:
                    await trigger_judge_session(
                        judge_service_url=judge_service_url,
                        session_id=db_session_id,
                        room_name=ctx.room.name,
                        product=db_product,
                    )
                await dialogue_logger.close()

            ctx.add_shutdown_callback(_finalize_session)
        else:
            ctx.add_shutdown_callback(dialogue_logger.close)



if __name__ == "__main__":
    cli.run_app(server)
