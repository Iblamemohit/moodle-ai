import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
WIKI_REST_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
HEADERS = {
    "User-Agent": "MoodleStudyAgent/1.0 (academic-ai-tutor@iitd.ac.in)"
}

def search_wikipedia(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """
    Searches Wikipedia for fallback context when course materials lack general concepts.
    Returns a list of dicts: [{'title': str, 'summary': str, 'url': str, 'source': str}]
    """
    results = []
    try:
        # 1. Search for matching titles
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": max_results
        }
        resp = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return []

        search_hits = resp.json().get("query", {}).get("search", [])
        for hit in search_hits:
            title = hit.get("title", "")
            if not title:
                continue

            # 2. Get clean page summary from REST API
            summary_resp = requests.get(f"{WIKI_REST_URL}{title.replace(' ', '_')}", headers=HEADERS, timeout=8)
            if summary_resp.status_code == 200:
                data = summary_resp.json()
                extract = data.get("extract", "")
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
                if extract:
                    results.append({
                        "title": title,
                        "summary": extract,
                        "url": page_url,
                        "source": f"Wikipedia: {title}"
                    })
            else:
                # Fallback to snippet from search hit
                snippet_html = hit.get("snippet", "")
                clean_snippet = BeautifulSoup(snippet_html, "html.parser").get_text()
                if clean_snippet:
                    results.append({
                        "title": title,
                        "summary": clean_snippet,
                        "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        "source": f"Wikipedia: {title}"
                    })

    except Exception as e:
        print(f"[Wikipedia Search Error]: {e}")

    return results
