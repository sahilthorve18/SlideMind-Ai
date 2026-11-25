"""Unit tests for the modern deck image search service."""
from unittest.mock import patch, MagicMock
from services.deck.image_search import (
    CandidateImage,
    VisualBrief,
    search_wikipedia_images,
    search_wikimedia_commons,
    search_unsplash,
    search_pexels,
    retrieve_image_candidates,
)


def test_visual_brief_defaults():
    brief = VisualBrief(slide_title="Quantum Computing", main_message="Qubits scale exponentially", key_concepts=["quantum", "qubit"])
    assert brief.slide_title == "Quantum Computing"
    assert brief.search_keywords == ["Quantum Computing"]
    assert brief.preferred_composition == "split_right"


def test_candidate_image_to_dict():
    img = CandidateImage(
        id="test_1",
        title="Sample",
        image_url="https://example.com/photo.jpg",
        thumb_url="https://example.com/thumb.jpg",
        source="Wikimedia Commons",
        source_page="https://commons.wikimedia.org",
        artist="Photographer",
        artist_url=None,
        license="CC BY-SA 4.0",
        license_url=None,
        width=1280,
        height=720,
        aspect_ratio=1.78,
        description="A nice photo",
    )
    d = img.to_dict()
    assert d["id"] == "test_1"
    assert d["width"] == 1280
    assert d["source"] == "Wikimedia Commons"


@patch("requests.get")
def test_search_wikipedia_images(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "pages": [
            {
                "id": 12345,
                "title": "Quantum processor",
                "description": "Superconducting qubit chip",
                "thumbnail": {"url": "//upload.wikimedia.org/wikipedia/commons/thumb/1/1a/chip.jpg/300px-chip.jpg"},
            }
        ]
    }
    mock_get.return_value = mock_resp

    results = search_wikipedia_images("quantum chip")
    assert len(results) == 1
    assert results[0].title == "Quantum processor"
    assert "1280px-chip.jpg" in results[0].image_url
    assert results[0].source == "Wikimedia Commons"


@patch("requests.get")
def test_search_wikimedia_commons(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "query": {
            "pages": {
                "999": {
                    "title": "File:Solar_panels_array.jpg",
                    "imageinfo": [
                        {
                            "thumburl": "https://upload.wikimedia.org/solar_1280.jpg",
                            "url": "https://upload.wikimedia.org/solar.jpg",
                            "thumbwidth": 1280,
                            "thumbheight": 720,
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "Artist": {"value": "Jane Doe"},
                                "ImageDescription": {"value": "Solar panel farm"},
                            },
                        }
                    ],
                }
            }
        }
    }
    mock_get.return_value = mock_resp

    results = search_wikimedia_commons("solar energy")
    assert len(results) == 1
    assert results[0].title == "Solar_panels_array.jpg"
    assert results[0].artist == "Jane Doe"
    assert results[0].source == "Wikimedia Commons"


@patch("services.deck.image_search.search_wikipedia_images")
@patch("services.deck.image_search.search_wikimedia_commons")
def test_retrieve_image_candidates(mock_wiki, mock_wiki_page):
    c1 = CandidateImage("1", "T1", "https://img1.jpg", "https://t1.jpg", "Wikimedia Commons", "p", "a", None, "CC", None, 1280, 720, 1.78, "d")
    mock_wiki.return_value = [c1]
    mock_wiki_page.return_value = []

    brief = VisualBrief(slide_title="Solar Energy", main_message="Clean Power", key_concepts=["solar"])
    candidates = retrieve_image_candidates(brief, already_used_urls=set())
    assert len(candidates) >= 1
    assert candidates[0].image_url == "https://img1.jpg"
