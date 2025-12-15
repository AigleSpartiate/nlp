import json
import re
from typing import List

from models.lyric_analysis import (
    LyricAnalysis, LineAnalysis, SyllableInfo, EmotionalTone
)
from utils.text_utils import TextUtils
from .base_agent import BaseAgent


class LyricAnalysisAgent(BaseAgent):
    """Agent for analyzing lyrics"""

    @property
    def name(self) -> str:
        return "LyricAnalysisAgent"

    @property
    def description(self) -> str:
        return "Analyzes lyrics to extract rhythm, mood, structure, and musical suggestions."

    def _get_analysis_prompt(self, lyrics: str, language: str) -> str:
        """Generate prompt for lyric analysis"""
        return f"""Analyze the following song lyrics and provide a detailed musical analysis.

Lyrics:
{lyrics}

Language: {language}

Please analyze and respond in the following JSON format:
{{
    "emotional_tone": "one of: joyful, melancholic, energetic, peaceful, romantic, angry, nostalgic, hopeful",
    "mood_description": "brief description of the overall mood",
    "suggested_tempo": <integer between 60-180>,
    "suggested_key": "musical key like C, G, Am, etc.",
    "suggested_style": "one of: pop, ballad, rock, folk, classical",
    "structure_notes": "observations about the lyric structure"
}}

Respond ONLY with the JSON object, no additional text."""

    def _parse_llm_response(self, response: str) -> dict:
        """Parse LLM response to extract JSON"""
        try:
            # find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    def _analyze_structure(
            self,
            lyrics: str,
            language: str
    ) -> tuple[List[LineAnalysis], List[str]]:
        """Analyze lyric structure and tokenize"""
        lines_text = TextUtils.split_into_lines(lyrics)
        lines = []
        all_words = []
        word_index = 0

        for line_idx, line_text in enumerate(lines_text):
            words = TextUtils.tokenize_lyrics(line_text, language)
            syllables = []

            for i, word in enumerate(words):
                syllable_info = SyllableInfo(
                    text=word,
                    index=word_index,
                    syllable_count=TextUtils.get_syllable_count(word, language),
                    stress_level=self._estimate_stress(i, len(words)),
                    duration_weight=1.0,
                    is_word_end=(i == len(words) - 1),
                    is_line_end=(i == len(words) - 1)
                )
                syllables.append(syllable_info)
                all_words.append(word)
                word_index += 1

            line_analysis = LineAnalysis(
                text=line_text,
                line_index=line_idx,
                syllables=syllables,
                syllable_count=sum(s.syllable_count for s in syllables),
                suggested_measures=max(1, len(syllables) // 4)
            )
            lines.append(line_analysis)

        return lines, all_words

    def _estimate_stress(self, position: int, total: int) -> int:
        """Estimate stress level based on position"""
        if position == 0:
            return 3  # first word usually stressed
        elif position == total - 1:
            return 2  # last word somewhat stressed
        elif position % 2 == 0:
            return 2  # even positions get some stress
        else:
            return 1  # odd positions less stressed

    def process(self, lyrics: str) -> LyricAnalysis:
        """Analyze lyrics and return structured analysis"""
        self.log("Starting lyric analysis")

        # clean + detect language
        lyrics = TextUtils.clean_lyrics(lyrics)
        language = TextUtils.detect_language(lyrics)
        self.log(f"Detected language: {language}")

        # LLM analysis
        prompt = self._get_analysis_prompt(lyrics, language)
        try:
            llm_response = self.llm_client.complete(
                prompt,
                system_prompt="You are a music composition expert. Analyze lyrics and provide musical suggestions in JSON format.",
                temperature=0.5
            )
            llm_analysis = self._parse_llm_response(llm_response)
        except Exception as e:
            self.log(f"LLM analysis failed: {e}, using defaults", "warning")
            llm_analysis = self._parse_llm_response("")

        lines, word_list = self._analyze_structure(lyrics, language)

        try:
            emotional_tone = EmotionalTone(llm_analysis.get("emotional_tone", "peaceful"))
        except ValueError:
            emotional_tone = EmotionalTone.PEACEFUL

        # build analysis result
        analysis = LyricAnalysis(
            original_text=lyrics,
            language=language,
            lines=lines,
            total_syllables=sum(line.syllable_count for line in lines),
            total_words=len(word_list),
            suggested_tempo=llm_analysis.get("suggested_tempo", 100),
            suggested_key=llm_analysis.get("suggested_key", "C"),
            suggested_time_signature="4/4",
            suggested_style=llm_analysis.get("suggested_style", "pop"),
            emotional_tone=emotional_tone,
            mood_description=llm_analysis.get("mood_description", ""),
            word_list=word_list
        )

        self.log(f"Analysis complete: {len(word_list)} words, tempo={analysis.suggested_tempo}")
        return analysis
