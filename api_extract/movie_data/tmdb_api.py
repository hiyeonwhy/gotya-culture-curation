import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_tmdb_genre_mapping():
    url = 'https://api.themoviedb.org/3/genre/movie/list'
    headers = {
        'accept': 'application/json',
        'Authorization': f"Bearer {os.getenv('TMDB_API_KEY')}"
    }
    params = {
        'language': 'ko-KR'
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        genres = response.json().get('genres', [])
        return {genre['id']: genre['name'] for genre in genres}
    return {}

def get_and_save_tmdb_data(query="어벤져스"):
    genre_mapping = get_tmdb_genre_mapping()
    
    url = 'https://api.themoviedb.org/3/search/movie'
    headers = {
        'accept': 'application/json',
        'Authorization': f"Bearer {os.getenv('TMDB_API_KEY')}"
    }
    params = {
        'query': query,
        'include_adult': False,
        'language': 'ko-KR',
        'page': 1
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        raw_data = response.json().get('results', [])
        
        for movie in raw_data:
            genre_ids = movie.get('genre_ids', [])
            movie['genre_names'] = [genre_mapping.get(g_id, "알 수 없음") for g_id in genre_ids]
        
        folder_name = "output"
        file_name = "tmdb_raw_data.json"
        os.makedirs(folder_name, exist_ok=True)
        file_path = os.path.join(folder_name, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=4)
            
        print(f"작업 완료: '{file_path}' 파일이 생성되었습니다.")
    else:
        print(f"API 요청 실패: 상태 코드 {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    search_keyword = "어벤져스"
    get_and_save_tmdb_data(search_keyword)