import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def get_aladin_novels(query="사랑", target_count=20):
    url = 'http://www.aladin.co.kr/ttb/api/ItemSearch.aspx'
    
    # 1. 넉넉하게 데이터를 가져오기 위해 MaxResults를 100으로 설정합니다.
    params = {
        'ttbkey': os.getenv('ALADIN_TTB_KEY'),
        'Query': query,
        'MaxResults': 100, 
        'SearchTarget': 'Book',
        'output': 'js',
        'Version': '20131101'
    }
    
    response = requests.get(url, params=params)
    novel_list = []
    
    if response.status_code == 200:
        books = response.json().get('item', [])
        
        for book in books:
            category = book.get('categoryName', '')
            
            # 2. 카테고리 이름에 '소설'이라는 글자가 포함되어 있는지 검사합니다.
            if '소설' in category:
                novel_list.append(book)
                
            # 3. 우리가 원하는 개수(20개)가 다 채워지면 반복문을 즉시 종료합니다.
            if len(novel_list) == target_count:
                break
                
    return novel_list

def save_to_json_file(data, folder_name="output", file_name="aladin_novel_data.json"):
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"작업 완료: 총 {len(data)}개의 소설 데이터가 '{file_path}' 파일에 저장되었습니다.")

if __name__ == "__main__":
    # 소설이 많이 나올 법한 검색어를 넣으면 20개를 더 빨리 채울 수 있습니다.
    search_keyword = "사랑" 
    results = get_aladin_novels(search_keyword, target_count=20)
    save_to_json_file(results)