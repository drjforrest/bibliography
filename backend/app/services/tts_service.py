"""
TTS (Text-to-Speech) Service for HERO Evidence Library v2.0

Supports three TTS providers:
1. Kokoro (free, local, default)
2. OpenAI TTS (pay-per-use, $15/1M chars)
3. ElevenLabs (subscription, $5-99/month)

Smart routing based on user preferences and cost optimization.
"""

import os
import asyncio
from typing import Optional, Literal
from pathlib import Path
import httpx
from datetime import datetime

# TTS Provider types
TTSProvider = Literal["kokoro", "openai", "elevenlabs"]
TTSOptimizationMode = Literal["auto", "prefer_openai", "prefer_elevenlabs", "kokoro_only"]


class TTSService:
    """
    Unified TTS service supporting multiple providers.
    
    Usage:
        tts = TTSService(user_id=123, openai_key="sk-...", elevenlabs_key="...")
        audio_path = await tts.generate_speech("Hello world", provider="auto")
    """
    
    def __init__(
        self,
        user_id: int,
        openai_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        optimization_mode: TTSOptimizationMode = "auto",
        output_dir: Optional[Path] = None
    ):
        self.user_id = user_id
        self.openai_api_key = openai_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        self.optimization_mode = optimization_mode
        self.output_dir = output_dir or Path("/tmp/hero_tts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_speech(
        self,
        text: str,
        provider: TTSProvider | Literal["auto"] = "auto",
        voice: Optional[str] = None,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generate speech audio from text using specified or auto-selected provider.
        
        Args:
            text: Text to convert to speech
            provider: TTS provider to use ("auto", "kokoro", "openai", "elevenlabs")
            voice: Voice ID/name (provider-specific)
            output_filename: Optional custom filename
            
        Returns:
            Path to generated audio file
        """
        # Auto-select provider based on optimization mode
        if provider == "auto":
            provider = self._select_provider()
            
        # Generate filename
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"tts_{self.user_id}_{timestamp}.mp3"
            
        output_path = self.output_dir / output_filename
        
        # Route to appropriate provider
        if provider == "kokoro":
            await self._generate_kokoro(text, output_path, voice)
        elif provider == "openai":
            await self._generate_openai(text, output_path, voice)
        elif provider == "elevenlabs":
            await self._generate_elevenlabs(text, output_path, voice)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")
            
        return output_path
    
    def _select_provider(self) -> TTSProvider:
        """
        Auto-select TTS provider based on user's optimization mode and available keys.
        """
        if self.optimization_mode == "kokoro_only":
            return "kokoro"
            
        if self.optimization_mode == "prefer_openai" and self.openai_api_key:
            return "openai"
            
        if self.optimization_mode == "prefer_elevenlabs" and self.elevenlabs_api_key:
            return "elevenlabs"
            
        # Auto mode: use cheapest available option
        # For now, default to Kokoro (free)
        # TODO: Implement cost-based routing using PodcastUsageStats
        return "kokoro"
    
    async def _generate_kokoro(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None
    ) -> None:
        """
        Generate speech using Kokoro TTS (local, free).
        
        Kokoro is a local TTS model that runs on the HERO server.
        No API keys required, completely free.
        """
        # TODO: Implement Kokoro TTS
        # This will use a local Kokoro model instance
        # For now, create a placeholder
        raise NotImplementedError(
            "Kokoro TTS not yet implemented. "
            "Will use local model at HERO server."
        )
    
    async def _generate_openai(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None
    ) -> None:
        """
        Generate speech using OpenAI TTS API.
        
        Cost: $15 per 1M characters (~$0.015 per 1k chars)
        Voices: alloy, echo, fable, onyx, nova, shimmer
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")
            
        voice = voice or "alloy"  # Default voice
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",  # or "tts-1-hd" for higher quality
                    "input": text,
                    "voice": voice
                },
                timeout=60.0
            )
            response.raise_for_status()
            
            # Save audio file
            output_path.write_bytes(response.content)
    
    async def _generate_elevenlabs(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None
    ) -> None:
        """
        Generate speech using ElevenLabs API.
        
        Cost: Subscription-based ($5-99/month)
        Offers highest quality voices and customization.
        """
        if not self.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not configured")
            
        voice = voice or "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={
                    "xi-api-key": self.elevenlabs_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=60.0
            )
            response.raise_for_status()
            
            # Save audio file
            output_path.write_bytes(response.content)
    
    @staticmethod
    def estimate_cost(
        text: str,
        provider: TTSProvider,
        monthly_character_count: int = 0
    ) -> float:
        """
        Estimate cost for generating TTS for given text.
        
        Args:
            text: Text to convert
            provider: TTS provider
            monthly_character_count: User's monthly character usage (for ElevenLabs tier calculation)
            
        Returns:
            Estimated cost in USD
        """
        char_count = len(text)
        
        if provider == "kokoro":
            return 0.0  # Free
            
        elif provider == "openai":
            # $15 per 1M characters
            return (char_count / 1_000_000) * 15.0
            
        elif provider == "elevenlabs":
            # Subscription-based, estimate marginal cost per character
            # This is complex as it depends on the tier, but we can estimate
            # the effective cost per character based on subscription price
            
            # Starter tier: $5/month for 30k chars = $0.000167/char
            # Creator tier: $22/month for 100k chars = $0.00022/char
            # Pro tier: $99/month for 500k chars = $0.000198/char
            
            # Use average effective rate
            return char_count * 0.0002
        
        return 0.0


# Example usage
async def main():
    """Example usage of TTSService"""
    tts = TTSService(
        user_id=1,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        optimization_mode="auto"
    )
    
    test_text = "Hello, this is a test of the HERO Evidence Library podcast generation system."
    
    # Generate with auto provider selection
    audio_path = await tts.generate_speech(test_text, provider="auto")
    print(f"Generated audio: {audio_path}")
    
    # Estimate costs
    print(f"Kokoro cost: ${tts.estimate_cost(test_text, 'kokoro')}")
    print(f"OpenAI cost: ${tts.estimate_cost(test_text, 'openai'):.4f}")
    print(f"ElevenLabs cost: ${tts.estimate_cost(test_text, 'elevenlabs'):.4f}")


if __name__ == "__main__":
    asyncio.run(main())
