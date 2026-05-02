import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

FILMARKS_USER = "rossken"
DATA_FILE = "movies.json"
TOTAL_PAGES = 26

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"movies": [], "last_updated": None}

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

        # スコアを取得（h3の親要素から探す）
        parent = item.find_parent()
        score = None
        for _ in range(5):
            if parent is None:
                break
            score_el = parent.find(class_=lambda c: c and "score" in c.lower())
            if score_el:
                try:
                    score = float(score_el.get_text(strip=True))
                except:
                    pass
                break
            parent = parent.find_parent()

        # 映画IDを抽出
        movie_id = href.split("/movies/")[1].split("#")[0].split("?")[0]

        movies.append({
            "id": movie_id,
            "title": title,
            "score": score,
            "filmarks_url": f"https://filmarks.com/movies/{movie_id}"
        })

    return movies

def main():
    print("=== Filmarks スクレイパー開始 ===")
    data = load_existing()
    existing_ids = {m["id"] for m in data["movies"]}
    new_count = 0

    # 最初のページだけ確認して新着があるかチェック
    for page in range(1, TOTAL_PAGES + 1):
        print(f"ページ {page}/{TOTAL_PAGES} 取得中...")
        movies = scrape_page(page)

        for movie in movies:
            if movie["id"] not in existing_ids:
                data["movies"].insert(0, movie)
                existing_ids.add(movie["id"])
                new_count += 1
                print(f"  新規追加: {movie['title']} ★{movie['score']}")

        time.sleep(2)  # サーバー負荷軽減

    data["last_updated"] = datetime.utcnow().isoformat()
    data["total"] = len(data["movies"])

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n完了: {new_count}本追加 / 合計{data['total']}本")

if __name__ == "__main__":
    main()
