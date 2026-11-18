"""AI service integrations - OpenAI and Gemini."""
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


class DefaultDict(dict):
    def __missing__(self, key):
        return f"[{key}]"


class AIService:
    def __init__(self):
        self.openai_key = None
        self.gemini_key = None

    def _get_keys(self):
        self.openai_key = current_app.config.get("OPENAI_API_KEY", "")
        self.gemini_key = current_app.config.get("GEMINI_API_KEY", "")

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

        # Nền tảng dùng Google Gemini làm mô hình AI mặc định duy nhất.
        if self.gemini_key:
            return self._call_gemini(prompt)
        return {"error": "Chưa cấu hình GEMINI_API_KEY", "response": None, "provider": "gemini"}

    def _call_openai(self, prompt):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert English teacher assistant for Vietnamese high school students."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
            )
            content = response.choices[0].message.content
            return {"provider": "openai", "response": content, "tokens_used": response.usage.total_tokens}
        except Exception as e:
            return {"provider": "openai", "error": str(e), "response": None}

    def _call_gemini(self, prompt):
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={"max_output_tokens": 8192, "temperature": 0.4},
            )
            response = model.generate_content(
                f"You are an expert English teacher assistant for Vietnamese high school students.\n\n{prompt}"
            )
            text = getattr(response, "text", None) or ""
            if not text and response.candidates:
                parts = response.candidates[0].content.parts
                text = "".join(getattr(p, "text", "") or "" for p in parts)
            return {"provider": "gemini", "response": text, "tokens_used": 0}
        except Exception as e:
            return {"provider": "gemini", "error": str(e), "response": None}
