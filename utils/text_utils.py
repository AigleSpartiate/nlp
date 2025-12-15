import re
import unicodedata
from typing import List, Tuple


class TextUtils:
    """Utilities for text and lyrics processing"""

    # chinese character range
    CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect if text is primarily Chinese or English"""
        chinese_chars = len(TextUtils.CHINESE_PATTERN.findall(text))
        total_chars = len(re.sub(r'\s+', '', text))

        if total_chars == 0:
            return "unknown"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "chinese"
        return "english"

    @staticmethod
    def tokenize_chinese(text: str) -> List[str]:
        """Tokenize Chinese text into individual characters"""
        # remove whitespace and punctuation for singing
        text = re.sub(r'[，。！？、；：""''（）\s]', '', text)
        return list(text)

    @staticmethod
    def tokenize_english(text: str) -> List[str]:
        """Tokenize English text into syllables"""
        # TODO: this is catastrophically bad, use real phonemizer...
        words = text.lower().split()
        syllables = []

        for word in words:
            word = re.sub(r'[^\w]', '', word)
            if word:
                # syllable estimation
                word_syllables = TextUtils._estimate_syllables(word)
                syllables.extend(word_syllables)

        return syllables

    @staticmethod
    def _estimate_syllables(word: str) -> List[str]:
        """Estimate syllables in an English word"""
        vowels = "aeiouy"
        word = word.lower()

        if len(word) <= 3:
            return [word]

        syllables = []
        current = ""
        prev_vowel = False

        for i, char in enumerate(word):
            current += char
            is_vowel = char in vowels

            # syllable break after vowel followed by consonant
            if prev_vowel and not is_vowel and i < len(word) - 1:
                if len(current) > 1:
                    syllables.append(current[:-1])
                    current = char

            prev_vowel = is_vowel

        if current:
            if syllables:
                syllables[-1] += current
            else:
                syllables.append(current)

        return syllables if syllables else [word]

    @staticmethod
    def tokenize_lyrics(text: str, language: str = "auto") -> List[str]:
        """Tokenize lyrics based on language"""
        if language == "auto":
            language = TextUtils.detect_language(text)

        if language == "chinese":
            return TextUtils.tokenize_chinese(text)
        else:
            return TextUtils.tokenize_english(text)

    @staticmethod
    def get_syllable_count(word: str, language: str = "auto") -> int:
        """Get syllable count for a word"""
        if language == "auto":
            language = TextUtils.detect_language(word)

        if language == "chinese":
            return 1  # one Chinese character = one syllable
        else:
            return len(TextUtils._estimate_syllables(word))

    @staticmethod
    def split_into_lines(text: str) -> List[str]:
        """Split lyrics into lines"""
        lines = text.strip().split('\n')
        return [line.strip() for line in lines if line.strip()]

    @staticmethod
    def clean_lyrics(text: str) -> str:
        """Clean lyrics text for processing"""
        # normalize unicode
        text = unicodedata.normalize('NFKC', text)

        # remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    @staticmethod
    def get_pinyin(text: str) -> List[Tuple[str, str]]:
        """Get pinyin for Chinese characters"""
        try:
            from pypinyin import pinyin, Style
            result = pinyin(text, style=Style.NORMAL)
            chars = list(text)
            return [(char, py[0]) for char, py in zip(chars, result)]
        except ImportError:
            # fallback without pypinyin
            return [(char, char) for char in text]
