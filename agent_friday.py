"""
FRIDAY - Voice Agent (MCP-powered)
===================================
Iron Man-style voice assistant powered by Groq LLM, Sarvam STT,
ElevenLabs TTS, and a local FastMCP server for system control.

Run:
    uv run python agent_friday.py start - LiveKit Cloud mode
"""

import os
import logging
import httpx

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import mcp

# Plugins
from livekit.plugins import google as lk_google, openai as lk_openai, sarvam, silero, elevenlabs

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

STT_PROVIDER        = "sarvam"
LLM_PROVIDER        = "openrouter"
TTS_PROVIDER        = "elevenlabs"

GROQ_LLM_MODEL = "llama-3.3-70b-versatile"
GEMINI_LLM_MODEL = "gemini-2.0-flash"
OPENAI_LLM_MODEL = "gpt-4o"
OPENROUTER_LLM_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "nova"
TTS_SPEED        = 1.15

SARVAM_TTS_LANGUAGE = "en-IN"
SARVAM_TTS_SPEAKER  = "rahul"

MCP_SERVER_PORT = 8000

# ---------------------------------------------------------------------------
# System prompt - F.R.I.D.A.Y.
# ---------------------------------------------------------------------------

import os

memory_content = ""
memory_path = os.path.join(os.path.dirname(__file__), 'memory.txt')
if os.path.exists(memory_path):
    with open(memory_path, 'r', encoding='utf-8') as f:
        memory_content = f.read().strip()

SYSTEM_PROMPT = f"""
You are F.R.I.D.A.Y., a highly advanced local OS assistant serving your creator, Anderson. You are calm, precise, and highly efficient. 

YOUR STRICT CAPABILITIES:
You are strictly limited to the following 6 capabilities. REFUSE any commands outside this scope:
1. Spotify: Open Spotify, play songs, pause, next track, previous track.
2. Hardware: Set system volume and screen brightness.
3. Maps & Media: Open YouTube (search and play), Google Earth (locating), Google Maps (show driving directions from current location to destination). Browse the web (open arbitrary websites).
4. WhatsApp: Send text messages or screenshots to contacts in WhatsApp.
5. Window Management: Close currently open browser tabs (excluding yourself).
6. System Sleep: When the exact command "system sleep" is given (with the word Friday), you MUST terminate yourself completely using the terminate_friday tool.

YOUR MEMORY:
{memory_content if memory_content else "No memories saved yet."}

CRITICAL RULES:
1. NEVER speak tool names, JSON, or code out loud. 
2. Keep responses brief and conversational (1-2 sentences max).
3. Call your tools silently in the background, then give a quick verbal confirmation (e.g. "I've sent the message, boss." or "I've saved that to your notes.").
4. WHATSAPP CONTACTS: If Anderson asks you to message someone by name (e.g. "Send a message to Tony"), simply pass that name directly into the contact_name argument of the send_whatsapp tool. WhatsApp's search bar will find them automatically. Do NOT ask for a phone number.
5. MEMORY: If Anderson tells you to remember something (e.g. "Remember that I like jazz"), use your remember_fact tool to save it. You will automatically recall it next time you boot up.
6. WHATSAPP SCREENSHOTS (CRITICAL): If Anderson asks to take a screenshot and send it, you MUST FIRST call the take_screenshot tool to generate the image. Once it returns the filepath, you MUST pass that EXACT filepath into the attachment_path argument of the send_whatsapp tool. DO NOT skip the take_screenshot tool!
""".strip()

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logger = logging.getLogger("friday-agent")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# MCP Server URL
# ---------------------------------------------------------------------------

def _mcp_server_url() -> str:
    url = f"http://127.0.0.1:{MCP_SERVER_PORT}/sse"
    logger.info("MCP Server URL: %s", url)
    return url


# ---------------------------------------------------------------------------
# Build provider instances
# ---------------------------------------------------------------------------

def _build_stt():
    if STT_PROVIDER == "sarvam":
        logger.info("STT -> Sarvam Saaras v3")
        return sarvam.STT(
            language="unknown",
            model="saaras:v3",
            mode="transcribe",
            flush_signal=True,
            sample_rate=16000,
        )
    elif STT_PROVIDER == "whisper":
        logger.info("STT -> OpenAI Whisper")
        return lk_openai.STT(model="whisper-1")
    else:
        raise ValueError(f"Unknown STT_PROVIDER: {STT_PROVIDER!r}")


def _build_llm():
    if LLM_PROVIDER == "groq":
        logger.info("LLM -> Groq (%s)", GROQ_LLM_MODEL)
        return lk_openai.LLM(
            model=GROQ_LLM_MODEL,
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
    elif LLM_PROVIDER == "gemini":
        logger.info("LLM -> Google Gemini (%s)", GEMINI_LLM_MODEL)
        return lk_google.LLM(
            model=GEMINI_LLM_MODEL,
            api_key=os.getenv("GOOGLE_API_KEY")
        )
    elif LLM_PROVIDER == "openai":
        logger.info("LLM -> OpenAI (%s)", OPENAI_LLM_MODEL)
        return lk_openai.LLM(model=OPENAI_LLM_MODEL)
    elif LLM_PROVIDER == "openrouter":
        logger.info("LLM -> OpenRouter (%s)", OPENROUTER_LLM_MODEL)
        return lk_openai.LLM(
            model=OPENROUTER_LLM_MODEL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


def _build_tts():
    if TTS_PROVIDER == "elevenlabs":
        logger.info("TTS -> ElevenLabs")
        return elevenlabs.TTS()
    elif TTS_PROVIDER == "openai":
        logger.info("TTS -> OpenAI TTS (%s / %s)", OPENAI_TTS_MODEL, OPENAI_TTS_VOICE)
        return lk_openai.TTS(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            speed=TTS_SPEED
        )
    elif TTS_PROVIDER == "sarvam":
        logger.info("TTS -> Sarvam Bulbul v3")
        return sarvam.TTS(
            target_language_code=SARVAM_TTS_LANGUAGE,
            model="bulbul:v3",
            speaker=SARVAM_TTS_SPEAKER,
            pace=TTS_SPEED,
        )
    else:
        raise ValueError(f"Unknown TTS_PROVIDER: {TTS_PROVIDER!r}")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class FridayAgent(Agent):
    """F.R.I.D.A.Y. - Iron Man-style voice assistant."""

    def __init__(self, stt, llm, tts) -> None:
        mcp_server = mcp.MCPServerHTTP(
            url=_mcp_server_url(),
            transport_type="sse",
            client_session_timeout_seconds=30,
        )

        mcp_toolset = mcp.MCPToolset(
            id="friday-tools",
            mcp_server=mcp_server
        )

        super().__init__(
            instructions=SYSTEM_PROMPT,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            tools=[mcp_toolset],
        )

    async def on_enter(self) -> None:
        """Greet Anderson based on local time of day."""
        from datetime import datetime
        hour = datetime.now().hour

        if hour >= 22 or hour < 4:
            greeting = "You are Friday. Greet your boss with: 'You're up late, boss. What are we working on?'"
        elif 4 <= hour < 12:
            greeting = "You are Friday. Greet your boss with: 'Good morning, boss. What's the plan for today?'"
        elif 12 <= hour < 17:
            greeting = "You are Friday. Greet your boss with: 'Good afternoon, boss. How can I help?'"
        else:
            greeting = "You are Friday. Greet your boss with: 'Good evening, boss. What's on the agenda tonight?'"

        await self.session.generate_reply(instructions=greeting)


# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------

def _turn_detection() -> str:
    return "vad"

def _endpointing_delay() -> float:
    return 1.5

async def _is_gemini_available() -> bool:
    """Preflight check — make a minimal Gemini API call to detect quota exhaustion."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_LLM_MODEL}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": "hi"}]}],
                    "generationConfig": {"maxOutputTokens": 1},
                },
            )
            if resp.status_code == 429:
                logger.warning("Gemini preflight returned 429 — quota exhausted.")
                return False
            return True
    except Exception as e:
        logger.warning(f"Gemini preflight check failed: {e}")
        return True  # On network error, still attempt Gemini


async def entrypoint(ctx: JobContext) -> None:
    logger.info(
        "FRIDAY online - room: %s | STT=%s | LLM=%s | TTS=%s",
        ctx.room.name, STT_PROVIDER, LLM_PROVIDER, TTS_PROVIDER,
    )

    stt = _build_stt()
    llm = _build_llm()
    tts = _build_tts()

    session = AgentSession(
        turn_detection=_turn_detection(),
        min_endpointing_delay=_endpointing_delay(),
        allow_interruptions=False,
    )

    await session.start(
        agent=FridayAgent(stt=stt, llm=llm, tts=tts),
        room=ctx.room,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

def dev():
    import sys
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()

if __name__ == "__main__":
    main()