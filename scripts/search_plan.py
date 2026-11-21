"""Expand one city, publication year, and topic into exact API calls."""

import json
from datetime import date, timedelta
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "config"


def searches(city, year, topic, config=CONFIG):
    cities = json.loads((config / "cities.json").read_text())
    topics = json.loads((config / "topics.json").read_text())
    if city not in cities or topic not in topics or not 2005 <= year <= 9998:
        raise ValueError(
            "Choose a configured city and topic and a valid YouTube publication year"
        )
    place, subject = cities[city], topics[topic]
    for quarter in range(1, 5):
        start = date(year, 3 * quarter - 2, 1)
        stop = date(year + (quarter == 4), (quarter * 3) % 12 + 1, 1) - timedelta(
            days=1
        )
        for lang, local_city in place["names"].items():
            for concept, phrase in subject["phrases"][lang].items():
                for duration in ("short", "medium", "long"):
                    yield {
                        "search_id": f"{city}-{year}Q{quarter}-{topic}-{lang}-{concept}-{duration}",
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
