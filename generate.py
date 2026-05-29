"""Replicates Lingotto's write-digest -> fix -> translate pipeline for one model.

This standalone benchmark vendors the production Lingotto prompts in
lingotto_prompts.py so it can be published and run outside the main project.
Talks to an OpenAI-compatible endpoint (native Ollama on Metal by default).
"""
import json
import re
import time

from openai import OpenAI

import lingotto_prompts as P
from lingotto_helper import missing_fields, normalize_metals


def _loads_lenient(raw: str) -> dict:
    """Parse a JSON object that may be wrapped in markdown fences or preceded by
    prose (common with reasoning models, or when a provider strips the
    response_format hint). Mirrors the judge's tolerant extraction.

    Returns a dict, or raises json.JSONDecodeError if no object can be recovered.
    """
    s = raw.strip()
    if s.startswith("```"):                       # ```json ... ``` or ``` ... ```
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", s, re.DOTALL)         # first {...} block, greedy
    if m:
        return json.loads(m.group(0))              # raises if still malformed
    raise json.JSONDecodeError("no JSON object found", s, 0)


class DigestGenerator:
    def __init__(self, base_url: str, api_key: str = "ollama", temperature: float = 0.3):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.temperature = temperature

    def _chat(self, model: str, system: str, user_obj) -> str:
        kwargs = dict(
            model=model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)},
            ],
        )
        try:
            resp = self.client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs)
        except Exception:
            # some providers/models reject response_format; retry without it
            resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def warmup(self, model: str) -> None:
        """Load the model into memory so timed runs exclude cold-start."""
        try:
            self.client.chat.completions.create(
                model=model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ok"}],
            )
        except Exception:
            pass

    def generate(self, model: str, items: list[dict]) -> dict:
        """Run the full pipeline (write -> fix-if-needed -> translate).

        Returns the final Italian post, the English intermediate, and diagnostics
        (latency, whether the repair step fired, first-pass validity, errors).
        """
        t0 = time.perf_counter()
        diag = {"model": model, "repaired": False, "first_pass_valid": False, "error": None}

        # 1) write digest (English)
        raw = self._chat(model, P.BLOG_DIGEST_PROMPT, {"items": items})
        try:
            post = _loads_lenient(raw)
        except json.JSONDecodeError:
            diag.update(error="write step: invalid JSON", latency_s=time.perf_counter() - t0)
            return {"post": None, "post_en": None, "diag": diag}

        diag["first_pass_valid"] = not missing_fields(post)

        # 2) repair missing fields (mirrors service.write_digest)
        if missing_fields(post):
            diag["repaired"] = True
            articles = [it["article"] for it in items]
            fixed = self._chat(model, P.FIX_PROMPT, {
                "partial_post": post,
                "cluster": {"cluster_topic": "daily digest", "articles": articles},
            })
            try:
                post = _loads_lenient(fixed)
            except json.JSONDecodeError:
                diag.update(error="fix step: invalid JSON", latency_s=time.perf_counter() - t0)
                return {"post": None, "post_en": None, "diag": diag}
            if missing_fields(post):
                diag["error"] = "still missing fields after repair"

        post_en = dict(post)

        # 3) translate to Italian
        translated = self._chat(model, P.BLOG_TO_IT, post)
        try:
            post_it = _loads_lenient(translated)
        except json.JSONDecodeError:
            diag.update(error="translate step: invalid JSON", latency_s=time.perf_counter() - t0)
            return {"post": None, "post_en": post_en, "diag": diag}

        if missing_fields(post_it):
            diag["error"] = "translation step: missing required fields"

        # 4) proofread the Italian (fix grammar/calques only; never content).
        # On any failure, keep the translated post — it is already valid.
        diag["proofread"] = False
        if not missing_fields(post_it):
            proofed_raw = self._chat(model, P.PROOFREAD_IT, post_it)
            try:
                proofed = _loads_lenient(proofed_raw)
                if not missing_fields(proofed):
                    post_it = proofed
                    diag["proofread"] = True
            except json.JSONDecodeError:
                pass

        normalize_metals(post_it)

        diag["final_valid"] = not missing_fields(post_it)
        if missing_fields(post_it):
            diag["error"] = "missing required fields after proofread"

        diag["latency_s"] = time.perf_counter() - t0
        return {"post": post_it, "post_en": post_en, "diag": diag}
