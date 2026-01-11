"""
Text-to-Speech Service with multi-provider support.

Supports:
- OpenAI TTS (pay-per-use, $15/1M chars)
- ElevenLabs (subscription, $5-99/month)
- Kokoro (free, local - planned, currently NotImplemented)
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import aiohttp

logger = logging.getLogger(__name__)

# Audio storage directory
TTS_STORAGE_DIR = Path(tempfile.gettempdir()) / "hero_tts"
TTS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class TTSService:
    """Text-to-Speech service with multi-provider support."""

    def __init__(
        self,
        provider: str = "openai",
        openai_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
    ):
        """
        Initialize TTS Service.

        Args:
            provider: TTS provider ("openai", "elevenlabs", "kokoro")
            openai_api_key: OpenAI API key (for OpenAI TTS)
            elevenlabs_api_key: ElevenLabs API key (for ElevenLabs TTS)
        """
        self.provider = provider.lower()
        self.openai_api_key = openai_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 min timeout

    def _get_headers(self, provider: str) -> dict:
        """Get HTTP headers with API key for the specified provider."""
        headers = {"Content-Type": "application/json"}
        if provider == "openai" and self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"
        elif provider == "elevenlabs" and self.elevenlabs_api_key:
            headers["xi-api-key"] = self.elevenlabs_api_key
        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(timeout=self.timeout)
        return self.http_session

    async def close(self):
        """Close HTTP session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    def estimate_cost(self, text: str, provider: Optional[str] = None) -> float:
        """
        Estimate cost for TTS generation.

        Args:
            text: Text to convert
            provider: Provider to estimate for (uses self.provider if not specified)

        Returns:
            Estimated cost in USD
        """
        provider = (provider or self.provider).lower()
        char_count = len(text)

        if provider == "openai":
            # OpenAI TTS: $15 per 1M characters
            return (char_count / 1_000_000) * 15.0
        elif provider == "elevenlabs":
            # ElevenLabs: Subscription-based, but ~$0.18 per 1000 characters for pay-per-use
            # For subscription plans, this is included, but we estimate pay-per-use
            return (char_count / 1000) * 0.18
        elif provider == "kokoro":
            # Free (local)
            return 0.0
        else:
            return 0.0

    async def generate(
        self, text: str, output_filename: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Generate audio from text using the configured provider.

        Args:
            text: Text to convert to speech
            output_filename: Optional filename (without extension). If not provided, generates a unique name.

        Returns:
            Tuple of (file_path, duration_seconds)
        """
        provider = self.provider.lower()

        if provider == "openai":
            return await self._generate_openai(text, output_filename)
        elif provider == "elevenlabs":
            return await self._generate_elevenlabs(text, output_filename)
        elif provider == "kokoro":
            return await self._generate_kokoro(text, output_filename)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider}")

    async def _generate_openai(
        self, text: str, output_filename: Optional[str] = None
    ) -> Tuple[str, float]:
        """Generate audio using OpenAI TTS API."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI TTS")

        try:
            session = await self._get_session()
            headers = self._get_headers("openai")

            # Generate output filename if not provided
            if not output_filename:
                import uuid

                output_filename = f"tts_{uuid.uuid4().hex[:8]}"

            output_path = TTS_STORAGE_DIR / f"{output_filename}.mp3"

            # Call OpenAI TTS API
            async with session.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"OpenAI TTS API error ({response.status}): {error_text}"
                    )
                    raise ValueError(f"OpenAI TTS API error: {error_text}")

                # Save audio file
                audio_data = await response.read()
                async with aiofiles.open(output_path, "wb") as f:
                    await f.write(audio_data)

                # Estimate duration (rough estimate: ~150 words per minute, average 5 chars per word)
                # OpenAI TTS typically generates ~150-160 words per minute
                word_count = len(text.split())
                estimated_duration = (word_count / 150) * 60  # seconds

                logger.info(
                    f"Generated OpenAI TTS audio: {output_path} (~{estimated_duration:.1f}s)"
                )
                return str(output_path), estimated_duration

        except Exception as e:
            logger.error(f"Failed to generate OpenAI TTS audio: {str(e)}")
            raise

    async def _generate_elevenlabs(
        self, text: str, output_filename: Optional[str] = None
    ) -> Tuple[str, float]:
        """Generate audio using ElevenLabs API."""
        if not self.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key is required for ElevenLabs TTS")

        try:
            session = await self._get_session()
            headers = self._get_headers("elevenlabs")

            # Generate output filename if not provided
            if not output_filename:
                import uuid

                output_filename = f"tts_{uuid.uuid4().hex[:8]}"

            output_path = TTS_STORAGE_DIR / f"{output_filename}.mp3"

            # Use a default voice ID (can be made configurable)
            # Default: "21m00Tcm4TlvDq8ikWAM" (Rachel - professional female voice)
            voice_id = "21m00Tcm4TlvDq8ikWAM"

            # Call ElevenLabs API
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5,
                    },
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"ElevenLabs TTS API error ({response.status}): {error_text}"
                    )
                    raise ValueError(f"ElevenLabs TTS API error: {error_text}")

                # Save audio file
                audio_data = await response.read()
                async with aiofiles.open(output_path, "wb") as f:
                    await f.write(audio_data)

                # Estimate duration (ElevenLabs is typically faster, ~160-170 words per minute)
                word_count = len(text.split())
                estimated_duration = (word_count / 165) * 60  # seconds

                logger.info(
                    f"Generated ElevenLabs TTS audio: {output_path} (~{estimated_duration:.1f}s)"
                )
                return str(output_path), estimated_duration

        except Exception as e:
            logger.error(f"Failed to generate ElevenLabs TTS audio: {str(e)}")
            raise

    async def _generate_kokoro(
        self, text: str, output_filename: Optional[str] = None
    ) -> Tuple[str, float]:
        """Generate audio using Kokoro TTS (local model - planned)."""
        raise NotImplementedError(
            "Kokoro TTS is not yet implemented. Requires local model deployment."
        )
