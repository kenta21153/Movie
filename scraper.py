import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

FILMARKS_USER = "rossken"
DATA_FILE = "movies.json"
TOTAL_PAGES = 26
TMDB_KEY = os.environ.get("TMDB_KEY", "72a10af0cd80c5de6028e8401d682cc6")

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"movies": [], "last_updated": None, "total": 0}

def save(data):
    data["last_updated"] = datetime.utcnow().isoformat()
    data["total"] = len(data["movies"])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# TMDBでタイトル検索してtmdb_id・英語タイトルを返す
def search_tmdb(title):
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_KEY, "query": title, "language": "ja-JP"}
        res = requests.get(url, params=params, timeout=10)
        results = res.json().get("results", [])
        if results:
            top = results[0]
            return {
                "tmdb_id": top["id"],
                "title_en": top.get("original_title", ""),
            }
    except Exception as e:
        print(f"  TMDB検索失敗 ({title}): {e}")
    return {"tmdb_id": None, "title_en": ""}

# Filmarksの1ページをスクレイプ
def scrape_page(page):
    url = f"https://filmarks.com/users/{FILMARKS_USER}/marks?view=poster&page={page}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; personal-movie-tracker/1.0)"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"  ページ{page} 取得失敗: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    movies = []
    for item in soup.select("h3 a"):
        href = item.get("href", "")
        title = item.get_text(strip=True)
        if not title or "/movies/" not in href:
            continue
        # スコア取得
        score = None
        parent = item.find_parent()
        for _ in range(6):
            if parent is None:
                break
            for el in parent.find_all(True):
                text = el.get_text(strip=True)
                try:
                    val = float(text)
                    if 1.0 <= val <= 5.0:
                        score = val
                        break
                except:
                    pass
            if score:
                break
            parent = parent.find_parent()

        filmarks_id = href.split("/movies/")[1].split("#")[0].split("?")[0]
        movies.append({
            "filmarks_id": filmarks_id,
            "title": title,
            "score": score,
        })
    return movies

def main():
    print("=== Filmarks スクレイパー開始 ===")
    data = load_existing()
    existing_ids = {m.get("filmarks_id") for m in data["movies"]}
    new_count = 0

    # 全ページをスクレイプして新規追加
    for page in range(1, TOTAL_PAGES + 1):
        print(f"ページ {page}/{TOTAL_PAGES} 取得中...")
        movies = scrape_page(page)
        for movie in movies:
            if movie["filmarks_id"] not in existing_ids:
                # 新規映画はTMDBも検索
                print(f"  新規: {movie['title']} → TMDB検索中...")
                tmdb_info = search_tmdb(movie["title"])
                movie.update(tmdb_info)
                data["movies"].insert(0, movie)
                existing_ids.add(movie["filmarks_id"])
                new_count += 1
                print(f"  追加完了: {movie['title']} (tmdb_id={movie['tmdb_id']}) ★{movie['score']}")
                time.sleep(0.3)  # TMDB API制限対策
        time.sleep(2)  # Filmarks負荷軽減

    # tmdb_idが未取得の既存映画を最大50件ずつ補完
    no_tmdb = [m for m in data["movies"] if not m.get("tmdb_id")]
    print(f"\ntmdb_id未取得: {len(no_tmdb)}本 → 最大50件補完します")
    for i, movie in enumerate(no_tmdb[:50]):
        print(f"  補完 ({i+1}/50): {movie['title']}")
        tmdb_info = search_tmdb(movie["title"])
        movie.update(tmdb_info)
        time.sleep(0.3)

    save(data)
    print(f"\n完了: 新規{new_count}本追加 / 合計{data['total']}本")

if __name__ == "__main__":
    main()
