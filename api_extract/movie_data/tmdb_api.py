import os
import json
import requests
import time
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_tmdb_genre_mappings():
    url = 'https://api.themoviedb.org/3/genre/movie/list'
    headers = {
        'accept': 'application/json',
        'Authorization': f"Bearer {os.getenv('TMDB_API_KEY')}"
    }
    
    res_ko = requests.get(url, headers=headers, params={'language': 'ko-KR'})
    genres_ko = res_ko.json().get('genres', []) if res_ko.status_code == 200 else []
    
    res_en = requests.get(url, headers=headers, params={'language': 'en-US'})
    genres_en = res_en.json().get('genres', []) if res_en.status_code == 200 else []
    
    ko_mapping = {g['id']: g['name'] for g in genres_ko}
    en_mapping = {g['id']: g['name'] for g in genres_en}
    
    ko_to_en_mapping = {}
    for g_id, ko_name in ko_mapping.items():
        ko_to_en_mapping[ko_name] = en_mapping.get(g_id, "uncategorized")
        
    return ko_mapping, ko_to_en_mapping

def save_genre_data_safely(movies_by_genre, folder_name, ko_to_en_mapping):
    for genre_name, movies in movies_by_genre.items():
        en_genre_name = ko_to_en_mapping.get(genre_name, "uncategorized")
        
        safe_genre_name = en_genre_name.replace("/", "_").replace(" ", "_").lower()
        file_path = os.path.join(folder_name, f"tmdb_{safe_genre_name}.json")
        
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
                    
        existing_data.extend(movies)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)

def get_all_movies_by_genre(start_year=2000, end_year=2026):
    genre_mapping_ko, ko_to_en_mapping = get_tmdb_genre_mappings()
    
    url = 'https://api.themoviedb.org/3/discover/movie'
    headers = {
        'accept': 'application/json',
        'Authorization': f"Bearer {os.getenv('TMDB_API_KEY')}"
    }
    
    folder_name = Path(__file__).resolve().parent / "raw"
    os.makedirs(folder_name, exist_ok=True)
    
    print(f"{start_year}년부터 {end_year}년까지의 모든 영화를 장르별로 수집합니다...")
    
    for year in range(start_year, end_year + 1):
        current_page = 1
        movies_by_genre = defaultdict(list)
        year_movie_count = 0
        
        while True:
            params = {
                'include_adult': False,
                'include_video': False,
                'language': 'ko-KR',
                'primary_release_year': year,
                'sort_by': 'popularity.desc',
                'page': current_page
            }
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
            except requests.exceptions.RequestException:
                time.sleep(5)
                continue
            
            if response.status_code == 200:
                data = response.json()
                raw_data = data.get('results', [])
                
                if not raw_data:
                    break
                    
                for movie in raw_data:
                    genre_ids = movie.get('genre_ids', [])
                    genre_names = [genre_mapping_ko.get(g_id, "미분류") for g_id in genre_ids]
                    movie['genre_names'] = genre_names
                    
                    if not genre_names:
                        movies_by_genre["미분류"].append(movie)
                    else:
                        for genre_name in genre_names:
                            movies_by_genre[genre_name].append(movie)
                            
                year_movie_count += len(raw_data)
                total_pages = data.get('total_pages', 1)
                
                if current_page >= total_pages or current_page >= 500:
                    break
                    
                current_page += 1
                time.sleep(0.1)
            else:
                break
        
        if movies_by_genre:
            save_genre_data_safely(movies_by_genre, folder_name, ko_to_en_mapping)
            print(f"{year}년도 영화 {year_movie_count}개 수집 및 기존 파일에 추가 완료")

    print("\n모든 2000년대 영화의 장르별 데이터 추가가 완료되었습니다.")

if __name__ == "__main__":
    get_all_movies_by_genre(start_year=2000, end_year=2026)
