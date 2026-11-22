import pytest
from services.intent_classifier import (
    INTENT_NORMAL_CHAT,
    INTENT_CREATE_PRESENTATION,
    INTENT_EDIT_PRESENTATION,
    INTENT_AMBIGUOUS,
    classify_chat_intent,
)


def test_normal_chat_intents():
    normal_prompts = [
        "Hi",
        "Hello",
        "How are you?",
        "What can you do?",
        "Explain artificial intelligence.",
        "Tell me about Python.",
        "Thank you.",
        "who are you",
        "good morning",
        "thanks so much!",
    ]
    for prompt in normal_prompts:
        # Test with and without active presentation
        res_no_pres = classify_chat_intent(prompt, has_active_presentation=False)
        assert res_no_pres.intent == INTENT_NORMAL_CHAT, f"Expected normal_chat for '{prompt}', got {res_no_pres.intent}"

        res_with_pres = classify_chat_intent(prompt, has_active_presentation=True, active_title="AI Deck")
        assert res_with_pres.intent == INTENT_NORMAL_CHAT, f"Expected normal_chat for '{prompt}' with active presentation, got {res_with_pres.intent}"


def test_presentation_explanation_is_normal_chat():
    explanation_prompts = [
        "Explain my presentation",
        "Explain this presentation",
        "Summarize my presentation",
        "Summarize this deck",
        "What is this presentation about?",
        "What is on slide 2?",
        "Tell me about slide 3",
        "Can you describe the slides?",
    ]
    for prompt in explanation_prompts:
        res = classify_chat_intent(prompt, has_active_presentation=True, active_title="My Sales Pitch")
        assert res.intent == INTENT_NORMAL_CHAT, f"Expected normal_chat for '{prompt}', got {res.intent}"


def test_create_presentation_intents():
    creation_prompts = [
        ("Create a 10-slide presentation about artificial intelligence.", "artificial intelligence", 10),
        ("Make a PowerPoint about climate change.", "climate change", 6),
        ("Generate a presentation on cybersecurity.", "cybersecurity", 6),
        ("Build a pitch deck for a startup", "pitch deck for a startup", 6),
    ]
    for prompt, expected_topic_substr, expected_slides in creation_prompts:
        res = classify_chat_intent(prompt, has_active_presentation=False)
        assert res.intent == INTENT_CREATE_PRESENTATION, f"Expected create_presentation for '{prompt}', got {res.intent}"
        assert res.slide_count == expected_slides
        assert expected_topic_substr.lower() in res.topic.lower()


def test_edit_presentation_intents():
    edit_prompts = [
        "Change slide 3's title.",
        "Add a conclusion slide.",
        "Make the presentation more professional.",
        "Replace the image on slide 2.",
        "Change the theme of this presentation.",
        "Delete slide 4",
        "Shorten the bullet points on slide 1",
    ]
    for prompt in edit_prompts:
        # When active presentation exists:
        res = classify_chat_intent(prompt, has_active_presentation=True, active_title="Existing Deck")
        assert res.intent == INTENT_EDIT_PRESENTATION, f"Expected edit_presentation for '{prompt}', got {res.intent}"

        # When NO active presentation exists:
        res_no_pres = classify_chat_intent(prompt, has_active_presentation=False)
        assert res_no_pres.intent != INTENT_EDIT_PRESENTATION, f"Should not trigger edit when no presentation is active: '{prompt}'"


def test_ambiguous_intents():
    ambiguous_prompts = [
        "Slide 3 is too crowded and wordy.",
        "The presentation is too technical.",
    ]
    for prompt in ambiguous_prompts:
        res = classify_chat_intent(prompt, has_active_presentation=True, active_title="Tech Deck")
        assert res.intent in (INTENT_AMBIGUOUS, INTENT_NORMAL_CHAT)
        if res.intent == INTENT_AMBIGUOUS:
            assert res.clarification
