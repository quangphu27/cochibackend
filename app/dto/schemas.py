"""Request validation schemas."""
from marshmallow import Schema, fields, validate, ValidationError
from functools import wraps
from flask import request, jsonify


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6))
    full_name = fields.Str(required=True)
    role = fields.Str(load_default="student", validate=validate.OneOf(["student"]))
    phone = fields.Str()


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class ClassCreateSchema(Schema):
    name = fields.Str(required=True)
    description = fields.Str()
    grade = fields.Str()
    subject = fields.Str()
    schedule = fields.List(fields.Dict())


class QuestionCreateSchema(Schema):
    type = fields.Str(required=True)
    content = fields.Str(required=True)
    options = fields.List(fields.Raw())
    correct_answer = fields.Raw()
    alternative_answers = fields.List(fields.Str())
    pairs = fields.List(fields.Dict())
    words = fields.List(fields.Str())
    sentences = fields.List(fields.Str())
    blanks = fields.List(fields.Dict())
    passage = fields.Str()
    explanation = fields.Str()
    category = fields.Str()
    skill = fields.Str()
    grade = fields.Str()
    topic = fields.Str()
    difficulty = fields.Str(validate=validate.OneOf(
        ["easy", "medium", "hard", "application", "high_application"]
    ))
    tags = fields.List(fields.Str())
    points = fields.Float()
    image_url = fields.Str()
    audio_url = fields.Str()
    video_url = fields.Str()
    time_limit = fields.Int()
    word_limit = fields.Int()


class QuestionSetCreateSchema(Schema):
    title = fields.Str(required=True)
    passage = fields.Str()
    instructions = fields.Str()
    skill = fields.Str()
    grade = fields.Str()
    topic = fields.Str()
    difficulty = fields.Str(validate=validate.OneOf(
        ["easy", "medium", "hard", "application", "high_application"]
    ))
    tags = fields.List(fields.Str())
    image_url = fields.Str()
    audio_url = fields.Str()
    video_url = fields.Str()
    time_limit = fields.Int()
    subtitles = fields.List(fields.Dict())
    content_type = fields.Str()
    questions = fields.List(fields.Dict(), required=True)


class ExamCreateSchema(Schema):
    title = fields.Str(required=True)
    class_id = fields.Str(required=True)
    description = fields.Str()
    type = fields.Str()
    skills = fields.List(fields.Str())
    question_ids = fields.List(fields.Raw())
    question_set_ids = fields.List(fields.Str())
    duration_minutes = fields.Int()


class AIGenerateSchema(Schema):
    tool_type = fields.Str(required=True)
    params = fields.Dict()
    provider = fields.Str(validate=validate.OneOf(["openai", "gemini"]))


def validate_request(schema_class):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            schema = schema_class()
            try:
                data = schema.load(request.get_json() or {})
            except ValidationError as err:
                return jsonify({"error": "Validation failed", "details": err.messages}), 400
            return fn(*args, **kwargs, validated_data=data)
        return wrapper
    return decorator
