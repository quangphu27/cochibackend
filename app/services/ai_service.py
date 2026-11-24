"""AI service — Google Gemini only (default models: 2.5 Flash / flash-latest)."""
from flask import current_app

AI_TOOLS = {
    "lesson_generator": "Generate an English lesson for {grade} on {topic}. Include objectives, activities, and assessment.",
    "quiz_generator": "Create a {difficulty} English quiz on {topic} for {grade} with {count} questions.",
    "worksheet_generator": "Create an English worksheet on {topic} for {grade} students.",
    "speaking_evaluation": "Evaluate this English speaking transcript for pronunciation, fluency, and vocabulary: {content}",
    "writing_evaluation": "Evaluate this English writing for grammar, vocabulary, coherence, and task achievement: {content}",
    "content_creator": "Create educational English content about {topic} for {grade} students.",
    "game_generator": "Create a fun English learning game about {topic} for {grade} students.",
    "vocabulary_builder": "Create a vocabulary list with definitions and example sentences for {topic} at {level} level.",
    "grammar_checker": "Check and correct grammar in this text, explain errors: {content}",
    "reading_questions": "Generate reading comprehension questions for this passage: {content}",
}

# gemini-1.5-flash đã bị gỡ khỏi API → dùng 2.5 / alias latest
DEFAULT_GEMINI_MODELS = (
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
)


class DefaultDict(dict):
    def __missing__(self, key):
        return f"[{key}]"


class AIService:
    def __init__(self):
        self.openai_key = None
        self.gemini_key = None

    def _get_keys(self):
        self.openai_key = current_app.config.get("OPENAI_API_KEY", "")
        self.gemini_key = (current_app.config.get("GEMINI_API_KEY") or "").strip()

    def _model_candidates(self):
        preferred = (current_app.config.get("GEMINI_MODEL") or "").strip()
        models = []
        if preferred:
            models.append(preferred)
        for m in DEFAULT_GEMINI_MODELS:
            if m not in models:
                models.append(m)
        return models

    def generate(self, tool_type, params, provider="gemini"):
        self._get_keys()
        params = params or {}
        if params.get("prompt"):
            prompt = params["prompt"]
        else:
            prompt_template = AI_TOOLS.get(tool_type, "")
            try:
                prompt = prompt_template.format_map(DefaultDict(params)) if "{" in prompt_template else prompt_template
            except (KeyError, ValueError):
                prompt = f"{prompt_template}\n\nParams: {params}"

        json_mode = bool(params.get("json_mode"))
        if not self.gemini_key:
            return {
                "error": "Chưa cấu hình GEMINI_API_KEY trên server",
                "response": None,
                "provider": "gemini",
            }
        return self._call_gemini(prompt, json_mode=json_mode)

    def _call_gemini(self, prompt, json_mode=False):
        try:
            import google.generativeai as genai
        except ImportError:
            return {
                "provider": "gemini",
                "error": "Thiếu thư viện google-generativeai",
                "response": None,
            }

        genai.configure(api_key=self.gemini_key)
        system = (
            "You are an expert English teacher assistant for Vietnamese high school students. "
            "Follow the user instructions carefully."
        )
        if json_mode:
            system += " Reply with valid JSON only — no markdown fences."

        generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.35,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        last_error = None
        for model_name in self._model_candidates():
            try:
                model = genai.GenerativeModel(
                    model_name,
                    generation_config=generation_config,
                )
                response = model.generate_content(f"{system}\n\n{prompt}")
                text = self._response_text(response)
                if not text:
                    last_error = f"Model {model_name} trả về rỗng (có thể bị chặn an toàn)"
                    continue
                return {
                    "provider": "gemini",
                    "model": model_name,
                    "response": text,
                    "tokens_used": 0,
                }
            except Exception as e:
                msg = str(e)
                last_error = f"{model_name}: {msg}"
                # thử model kế nếu 404 / not found
                if "404" in msg or "not found" in msg.lower():
                    continue
                # lỗi auth / quota — không cần thử model khác
                if any(x in msg.lower() for x in ("api key", "permission", "403", "401", "quota", "resource_exhausted")):
                    break

        return {
            "provider": "gemini",
            "error": last_error or "Gemini không phản hồi",
            "response": None,
        }

    @staticmethod
    def _response_text(response) -> str:
        try:
            text = getattr(response, "text", None) or ""
            if text:
                return text.strip()
        except Exception:
            pass
        try:
            candidates = getattr(response, "candidates", None) or []
            if not candidates:
                return ""
            parts = candidates[0].content.parts
            return "".join(getattr(p, "text", "") or "" for p in parts).strip()
        except Exception:
            return ""
