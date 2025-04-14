
import requests
from bs4 import BeautifulSoup
import json

def parse_site(source, keyword):
    url = source["url"]
    article_selector = source["article_selector"]
    link_tag = source.get("link_tag", "a")

    try:
        response = requests.get(url, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")
        articles = soup.select(article_selector)

        results = []
        for article in articles:
            link_elem = article.find(link_tag) if link_tag else article
            if not link_elem or not link_elem.get("href"):
                continue
            link = link_elem.get("href")
            title = link_elem.get_text(strip=True)

            if keyword.lower() in title.lower():
                if link.startswith("/"):
                    domain = '/'.join(url.split("/")[:3])
                    link = domain + link
                results.append({
                    "title": title,
                    "summary": "",  # Можно расширить позже
                    "url": link,
                    "date": ""
                })
        return results
    except Exception as e:
        return [{"title": f"Ошибка: {e}", "url": url, "summary": "", "date": ""}]

def parse_all(keyword):
    with open("sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)

    all_results = []
    for source in sources:
        results = parse_site(source, keyword)
        all_results.extend(results)
    return all_results
