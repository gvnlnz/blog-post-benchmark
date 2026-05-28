"""Deterministic, automatic metrics for a generated (Italian) blog post.

These are hardware-independent: they depend only on the produced text, so the
numbers transfer 1:1 to the production machine.
"""
import re

_word_re = re.compile(r"\w+", re.UNICODE)
_sentence_re = re.compile(r"[.!?]+")
_letter_re = re.compile(r"[A-Za-zÀ-ÿ]")


def strip_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # [label](url) -> label
    text = re.sub(r"[#*_`>]", "", text)                     # markdown symbols
    return text


def basic_counts(text: str):
    n_words = len(_word_re.findall(text)) or 1
    n_letters = len(_letter_re.findall(text)) or 1
    n_sentences = len([s for s in _sentence_re.split(text) if s.strip()]) or 1
    return n_words, n_letters, n_sentences


def gulpease(text: str) -> float:
    """Italian readability index (0-100, higher = easier to read)."""
    n_words, n_letters, n_sentences = basic_counts(text)
    return round(89 + (300 * n_sentences - 10 * n_letters) / n_words, 1)


def repetition_ratio(text: str, n: int = 3) -> float:
    """Share of repeated n-grams (0 = no repetition, higher = more repetitive)."""
    words = _word_re.findall(text.lower())
    grams = [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]
    if not grams:
        return 0.0
    return round(1 - len(set(grams)) / len(grams), 3)


class GrammarChecker:
    """Wraps LanguageTool for Italian. Lazy import; requires Java on the host."""

    def __init__(self, lang: str = "it"):
        import language_tool_python
        self.tool = language_tool_python.LanguageTool(lang)

    def errors_per_100w(self, text: str):
        n_words, _, _ = basic_counts(text)
        n_err = len(self.tool.check(text))
        return round(100 * n_err / n_words, 2), n_err


def text_metrics(body_it: str, grammar: "GrammarChecker | None") -> dict:
    plain = strip_markdown(body_it)
    n_words, _, _ = basic_counts(plain)
    out = {
        "words": n_words,
        "gulpease": gulpease(plain),
        "repetition_3gram": repetition_ratio(plain),
    }
    if grammar is not None:
        epw, n_err = grammar.errors_per_100w(plain)
        out["grammar_err_per_100w"] = epw
        out["grammar_err_count"] = n_err
    return out
