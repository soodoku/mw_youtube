"""Expand one city, publication year, and topic into exact API calls."""

import json
import re
from datetime import date, timedelta
from pathlib import Path
from string import Formatter

CONFIG = Path(__file__).with_name("config")
if not CONFIG.exists():
    CONFIG = Path(__file__).resolve().parents[2] / "config"


def validate_vocabulary(packet, city, topic, languages):
    if (
        packet["city"] != city
        or packet["topic"] != topic
        or not packet["description"].strip()
    ):
        raise ValueError(
            "Vocabulary targets a different city or topic, or lacks a definition"
        )
    ids = set()
    phrases = set()
    for entry in packet["keywords"]:
        identifier, lang, phrase = (
            entry["keyword_id"],
            entry["language"],
            entry["phrase"],
        )
        identity = (lang, " ".join(phrase.casefold().split()))
        if (
            not re.fullmatch("[a-z0-9_]+", identifier)
            or identifier in ids
            or identity in phrases
            or lang not in languages
            or not entry["concept"].strip()
        ):
            raise ValueError(
                "Duplicate or invalid keyword identifier, language, concept or phrase"
            )
        if [(f, s, c) for _, f, s, c in Formatter().parse(phrase) if f is not None] != [
            ("city", "", None)
        ]:
            raise ValueError("Each template requires exactly one literal {city} field")
        ids.add(identifier)
        phrases.add(identity)
    if {lang for lang, _ in phrases} != set(languages):
        raise ValueError("Missing language in vocabulary")


def searches(city, year, topic, config=CONFIG, vocabulary=None):
    cities = json.loads((config / "cities.json").read_text())
    topics = json.loads((config / "topics.json").read_text())
    if (
        city not in cities
        or (vocabulary is None and topic not in topics)
        or not 2005 <= year <= 9998
    ):
        raise ValueError(
            "Choose a configured city and topic and a valid YouTube publication year"
        )
    place = cities[city]
    if vocabulary is not None:
        validate_vocabulary(vocabulary, city, topic, place["names"])
        if not vocabulary.get("reviewer") or not vocabulary.get("reviewed_utc"):
            raise ValueError("Freeze the reviewed vocabulary before searching")
        keywords = vocabulary["keywords"]
    else:
        keywords = [
            dict(language=lang, keyword_id=concept, concept=concept, phrase=phrase)
            for lang in place["names"]
            for concept, phrase in topics[topic]["phrases"][lang].items()
        ]
    for quarter in range(1, 5):
        start = date(year, 3 * quarter - 2, 1)
        stop = date(year + (quarter == 4), (quarter * 3) % 12 + 1, 1) - timedelta(
            days=1
        )
        for keyword in keywords:
            lang, concept, phrase = (
                keyword[k] for k in ("language", "concept", "phrase")
            )
            local_city = place["names"][lang]
            keyword_id = keyword["keyword_id"]
            for duration in ("short", "medium", "long"):
                yield {
                    "search_id": f"{city}-{year}Q{quarter}-{topic}-{lang}-{keyword_id}-{duration}",
                    "city": city,
                    "year": year,
                    "quarter": quarter,
                    "topic": topic,
                    "query_language": lang,
                    "concept": concept,
                    "duration_band": duration,
                    "params": {
                        "part": "snippet",
                        "type": "video",
                        "order": "relevance",
                        "regionCode": place["region_code"],
                        "safeSearch": "moderate",
                        "maxResults": 25,
                        "q": phrase.format(city=local_city),
                        "relevanceLanguage": lang,
                        "videoDuration": duration,
                        "publishedAfter": f"{start}T00:00:00Z",
                        "publishedBefore": f"{stop}T23:59:59Z",
                    },
                }
