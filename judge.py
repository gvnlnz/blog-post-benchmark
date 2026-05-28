"""LLM-as-judge: scores faithfulness, quality and coherence (1-5).

Use a judge that is INDEPENDENT and stronger than the models under test
(e.g. a frontier API model, or at least a larger different local model).
Never let a model judge its own output (self-preference bias).
"""
import json
import re
import time

from openai import OpenAI

RUBRIC = """You are an expert editorial evaluator for an Italian financial blog about precious metals.
You receive the SOURCE material (cluster topics + source articles, in English) and a BLOG POST generated from it (in Italian).
Score the post on three axes as integers from 1 to 5 (5 = best):
- faithfulness: every claim is supported by the sources; no invented facts, numbers, dates or entities. 5 = fully grounded, 1 = clear hallucinations.
- quality: overall editorial quality for a retail investor (clarity, informativeness, structure, professional tone).
- coherence: logical flow and cohesion across paragraphs.
Return ONLY raw JSON, no fences: {"faithfulness":int,"quality":int,"coherence":int,"reason":"<=2 sentences"}"""


def _extract_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {}


class Judge:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def _call(self, user_payload: dict) -> str:
        kwargs = dict(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": RUBRIC},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
        try:
            resp = self.client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs)
        except Exception:
            # some providers reject response_format; retry without it
            resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or "{}"

    def score(self, items: list[dict], post_it: dict) -> dict:
        payload = {
            "sources": [{"cluster_topic": it["cluster_topic"], "article": it["article"]} for it in items],
            "blog_post": {"title": post_it.get("title"), "body": post_it.get("body")},
        }
        last_err = None
        for attempt in range(3):                 # tolerate transient rate-limit / network errors
            try:
                data = _extract_json(self._call(payload))
                return {
                    "faithfulness": data.get("faithfulness"),
                    "quality": data.get("quality"),
                    "coherence": data.get("coherence"),
                    "reason": data.get("reason"),
                }
            except Exception as e:
                last_err = e
                time.sleep(5 * (attempt + 1))
        return {"faithfulness": None, "quality": None, "coherence": None,
                "reason": f"judge error: {str(last_err)[:120]}"}
