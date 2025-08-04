"""
Enhanced Text-to-Speech engines with modern AI voices
Supports multiple TTS engines: gTTS, pyttsx3, and Edge-TTS
"""

import os
import asyncio
from pathlib import Path
from gtts import gTTS
import pyttsx3
import edge_tts
from typing import Optional, Dict, List

from ..utils.logging_config import get_logger, log_error_with_context


class TTSEngine:
    """Base class for TTS engines"""
    
    def __init__(self):
        self.supported_languages = {}
        self.logger = get_logger('tts')
    
    def generate_audio(self, text: str, language: str, output_path: str) -> bool:
        """Generate audio file from text"""
        raise NotImplementedError


class GTTSEngine(TTSEngine):
    """Google Text-to-Speech (online)"""
    
    def __init__(self):
        super().__init__()
        from gtts import lang
        self.supported_languages = lang.tts_langs()
    
    def generate_audio(self, text: str, language: str, output_path: str) -> bool:
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(output_path)
            
            self.logger.info(f"Generated audio with gTTS: {output_path}")
            return True
            
        except Exception as e:
            log_error_with_context(e, {
                'engine': 'gtts',
                'language': language,
                'output_path': output_path,
                'text_length': len(text)
            })
            return False


class Pyttsx3Engine(TTSEngine):
    """Local TTS engine (offline)"""
    
    def __init__(self):
        super().__init__()
        try:
            self.engine = pyttsx3.init()
            # Common language mappings
            self.supported_languages = {
                'en': 'English',
                'es': 'Spanish', 
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese'
            }
        except Exception as e:
            self.logger.error(f"Failed to initialize pyttsx3: {e}")
            self.engine = None
    
    def generate_audio(self, text: str, language: str, output_path: str) -> bool:
        if not self.engine:
            return False
            
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Configure voice properties
            voices = self.engine.getProperty('voices')
            
            # Try to find a voice for the language
            for voice in voices:
                if language.lower() in voice.name.lower() or 'en' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            # Set speech rate and volume
            self.engine.setProperty('rate', 180)  # Speed
            self.engine.setProperty('volume', 0.9)  # Volume
            
            # Generate audio
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            
            self.logger.info(f"Generated audio with pyttsx3: {output_path}")
            return True
            
        except Exception as e:
            log_error_with_context(e, {
                'engine': 'pyttsx3',
                'language': language,
                'output_path': output_path,
                'text_length': len(text)
            })
            return False


class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTS (online, high quality)"""
    
    def __init__(self):
        super().__init__()
        self.voices = {
            'en': 'en-US-AriaNeural',
            'es': 'es-ES-ElviraNeural', 
            'fr': 'fr-FR-DeniseNeural',
            'de': 'de-DE-KatjaNeural',
            'it': 'it-IT-ElsaNeural',
            'pt': 'pt-BR-FranciscaNeural',
            'ja': 'ja-JP-NanamiNeural',
            'ko': 'ko-KR-SunHiNeural',
            'zh': 'zh-CN-XiaoxiaoNeural',
            'ar': 'ar-SA-ZariyahNeural',
            'hi': 'hi-IN-SwaraNeural',
            'ru': 'ru-RU-SvetlanaNeural'
        }
        self.supported_languages = self.voices
    
    async def generate_audio_async(self, text: str, language: str, output_path: str) -> bool:
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            voice = self.voices.get(language, 'en-US-AriaNeural')
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
            self.logger.info(f"Generated audio with Edge-TTS: {output_path}")
            return True
            
        except Exception as e:
            log_error_with_context(e, {
                'engine': 'edge-tts',
                'language': language,
                'output_path': output_path,
                'text_length': len(text)
            })
            return False
    
    def generate_audio(self, text: str, language: str, output_path: str) -> bool:
        """Sync wrapper for async method"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.generate_audio_async(text, language, output_path)
            )
            loop.close()
            return result
        except Exception as e:
            log_error_with_context(e, {
                'engine': 'edge-tts-sync',
                'language': language,
                'output_path': output_path
            })
            return False


class TTSManager:
    """Manages multiple TTS engines with fallback support"""
    
    def __init__(self):
        self.logger = get_logger('tts')
        self.engines = {}
        
        # Initialize engines with error handling
        try:
            self.engines['edge'] = EdgeTTSEngine()
        except Exception as e:
            self.logger.warning(f"Edge-TTS not available: {e}")
        
        try:
            self.engines['gtts'] = GTTSEngine()
        except Exception as e:
            self.logger.warning(f"gTTS not available: {e}")
        
        try:
            self.engines['pyttsx3'] = Pyttsx3Engine()
        except Exception as e:
            self.logger.warning(f"pyttsx3 not available: {e}")
        
        self.preferred_order = ['edge', 'gtts', 'pyttsx3']
        
        available_engines = list(self.engines.keys())
        self.logger.info(f"Available TTS engines: {available_engines}")
    
    def generate_audio(self, text: str, language: str, output_path: str, 
                      engine_preference: Optional[str] = None) -> bool:
        """
        Generate audio with fallback support
        
        Args:
            text: Text to convert to speech
            language: Language code (e.g., 'en', 'es')
            output_path: Path to save audio file
            engine_preference: Preferred engine ('edge', 'gtts', 'pyttsx3')
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        if not self.engines:
            self.logger.error("No TTS engines available")
            return False
        
        # Determine engine order
        if engine_preference and engine_preference in self.engines:
            engines_to_try = [engine_preference] + [e for e in self.preferred_order if e != engine_preference]
        else:
            engines_to_try = self.preferred_order
        
        # Filter to only available engines
        engines_to_try = [e for e in engines_to_try if e in self.engines]
        
        # Try engines in order
        for engine_name in engines_to_try:
            engine = self.engines[engine_name]
            
            # Check if engine supports the language
            if language not in engine.supported_languages:
                self.logger.debug(f"{engine_name} doesn't support language '{language}', trying next...")
                continue
            
            self.logger.info(f"Trying {engine_name} TTS engine...")
            
            if engine.generate_audio(text, language, output_path):
                self.logger.info(f"✅ Audio generated successfully with {engine_name}")
                return True
            else:
                self.logger.warning(f"❌ {engine_name} failed, trying next engine...")
        
        self.logger.error("❌ All TTS engines failed")
        return False
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines"""
        return list(self.engines.keys())
    
    def get_supported_languages(self, engine_name: str) -> Dict:
        """Get supported languages for an engine"""
        if engine_name in self.engines:
            return self.engines[engine_name].supported_languages
        return {}
    
    def is_language_supported(self, language: str) -> bool:
        """Check if any engine supports the language"""
        for engine in self.engines.values():
            if language in engine.supported_languages:
                return True
        return False
