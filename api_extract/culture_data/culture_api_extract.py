import os
import json
from pathlib import Path
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv


# ======================================================
# 1. .env 파일 불러오기
# ======================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SERVICE_KEY = os.getenv("CULTURE_API_KEY")

if not SERVICE_KEY:
    raise ValueError(f".env 파일에서 CULTURE_API_KEY 값을 찾을 수 없습니다. 확인 경로: {ENV_PATH}")


# ======================================================
# 2. 기본 URL
# 실제 테스트에서 200이 나온 URL 기준
# ======================================================

BASE_URL = "http://apis.data.go.kr/B553457/cultureinfo"


# ======================================================
# 3. 공통 설정
# ======================================================

START_DATE = "20260101"
END_DATE = "20261231"
PAGE_NO = "1"
NUM_OF_ROWS = "20"


# ======================================================
# 4. 최종 JSON 컬럼
# ======================================================

FINAL_FIELDS = [
    "seq",
    "serviceName",
    "title",
    "startDate",
    "endDate",
    "place",
    "realmName",
    "area",
    "sigungu",
    "price",
    "contents1",
    "url",
    "phone",
    "thumbnail",
    "imgUrl",
    "gpsX",
    "gpsY",
    "placeUrl",
    "placeAddr",
    "placeSeq",
    "detailStatus",
]


# ======================================================
# 5. XML 파싱 보조 함수
# ======================================================

def parse_xml_items(xml_text):
    """
    XML 응답에서 item 목록을 찾아서
    [{필드명: 값}, ...] 형태로 변환하는 함수
    """
    root = ET.fromstring(xml_text)

    items = []

    for item in root.iter("item"):
        data = {}

        for child in item:
            data[child.tag] = child.text.strip() if child.text else ""

        items.append(data)

    return items


def print_items(title, items, limit=20):
    """
    API 결과를 보기 좋게 출력하는 함수
    """
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if not items:
        print("조회된 데이터가 없습니다.")
        return

    for idx, item in enumerate(items[:limit], start=1):
        print(f"\n[{idx}]")

        for key, value in item.items():
            print(f"{key}: {value}")


def remove_empty_params(params):
    """
    값이 빈 문자열인 파라미터는 요청에서 제외
    """
    return {
        key: value
        for key, value in params.items()
        if value is not None and value != ""
    }


def mask_service_key(url):
    """
    터미널 출력 시 서비스키 노출 방지
    """
    return url.replace(SERVICE_KEY, "********")


def request_api(endpoint, params):
    """
    API 요청 공통 함수
    """
    url = f"{BASE_URL}/{endpoint}"
    clean_params = remove_empty_params(params)

    try:
        response = requests.get(url, params=clean_params, timeout=15)
    except requests.exceptions.RequestException as error:
        print("요청 중 오류 발생:", error)
        return []

    print("\n요청 URL:")
    print(mask_service_key(response.url))

    print("상태 코드:", response.status_code)

    if response.status_code != 200:
        print("요청 실패")
        print(response.text)
        return []

    if "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in response.text:
        print("서비스키가 등록되지 않았거나, 해당 API 활용 신청이 안 된 상태입니다.")
        print(response.text)
        return []

    if "NO_OPENAPI_SERVICE_ERROR" in response.text:
        print("요청 URL이 잘못되었거나 존재하지 않는 API입니다.")
        print(response.text)
        return []

    if "SERVICE ERROR" in response.text:
        print("API 서비스 오류가 발생했습니다.")
        print(response.text)
        return []

    if "Unexpected errors" in response.text:
        print("API 서버에서 Unexpected errors를 반환했습니다.")
        print(response.text)
        return []

    try:
        return parse_xml_items(response.text)
    except ET.ParseError:
        print("XML 파싱 실패")
        print(response.text)
        return []


# ======================================================
# 6. 문화캘린더정보 목록조회 API
# /cultureinfo/livelihood2
# ======================================================

def get_livelihood_list():
    params = {
        "serviceKey": SERVICE_KEY,
        "PageNo": PAGE_NO,
        "numOfrows": NUM_OF_ROWS,
        "keyword": ""
    }

    return request_api("livelihood2", params)


# ======================================================
# 7. 기간별 문화정보목록조회 API
# /cultureinfo/period2
# ======================================================

def get_period_list():
    params = {
        "serviceKey": SERVICE_KEY,
        "from": START_DATE,
        "to": END_DATE,
        "PageNo": PAGE_NO,
        "numOfrows": NUM_OF_ROWS,
        "place": "",
        "gpsxfrom": "",
        "gpsyfrom": "",
        "gpsxto": "",
        "gpsyto": "",
        "keyword": "",
        "sortStdr": "1",
        "serviceTp": "A"
    }

    return request_api("period2", params)


# ======================================================
# 8. 지역별 문화정보목록조회 API
# /cultureinfo/area2
# ======================================================

def get_area_list():
    params = {
        "serviceKey": SERVICE_KEY,
        "sido": "서울",
        "sigungu": "",
        "from": START_DATE,
        "to": END_DATE,
        "place": "",
        "gpsxfrom": "",
        "gpsyfrom": "",
        "gpsxto": "",
        "gpsyto": "",
        "PageNo": PAGE_NO,
        "numOfrows": NUM_OF_ROWS,
        "keyword": "",
        "sortStdr": "1",
        "serviceTp": "A"
    }

    return request_api("area2", params)


# ======================================================
# 9. 분야별 문화정보목록조회 API
# /cultureinfo/realm2
#
# realmCode 분류코드
# A000: 연극
# B000: 음악/콘서트
# B002: 국악
# C000: 무용/발레
# D000: 전시
# B003: 뮤지컬/오페라
# E000: 아동/가족
# F000: 행사/축제
# G000: 교육/체험
# H000: 도서
# I000: 체육
# L000: 기타
# ======================================================

def get_realm_list():
    params = {
        "serviceKey": SERVICE_KEY,
        "realmCode": "D000",
        "PageNo": PAGE_NO,
        "numOfrows": NUM_OF_ROWS,
        "from": START_DATE,
        "to": END_DATE,
        "sido": "",
        "place": "",
        "gpsxfrom": "",
        "gpsyfrom": "",
        "gpsxto": "",
        "gpsyto": "",
        "keyword": "",
        "sortStdr": "1",
        "serviceTp": "A"
    }

    return request_api("realm2", params)


# ======================================================
# 10. 문화정보 상세정보조회 API
# /cultureinfo/detail2?seq=...
# ======================================================

def get_detail(seq):
    params = {
        "serviceKey": SERVICE_KEY,
        "seq": seq
    }

    detail_items = request_api("detail2", params)

    # 상세조회 성공 여부 표시
    if detail_items:
        for item in detail_items:
            item["detailStatus"] = "success"

    return detail_items


def get_detail_list(seq_list):
    """
    중복 제거된 전체 seq에 대해 상세정보 조회
    """
    detail_results = []

    for seq in seq_list:
        print(f"\n상세정보 조회 중 seq = {seq}")

        detail_items = get_detail(seq)

        if detail_items:
            detail_results.extend(detail_items)
        else:
            detail_results.append({
                "seq": seq,
                "detailStatus": "failed"
            })

    return detail_results


# ======================================================
# 11. 중복 제거 및 병합 함수
# ======================================================

def merge_items_by_seq(*item_lists):
    """
    여러 API 결과를 seq 기준으로 하나로 합치는 함수

    - 같은 seq는 같은 문화정보로 판단
    - detail_items에 있는 가격, 전화번호, 주소 등 상세정보를 기존 목록 정보에 병합
    - 값이 비어있지 않은 경우만 덮어쓰기
    """
    merged = {}

    for items in item_lists:
        for item in items:
            seq = item.get("seq")

            if not seq:
                continue

            if seq not in merged:
                merged[seq] = item.copy()
            else:
                for key, value in item.items():
                    if value:
                        merged[seq][key] = value

    return list(merged.values())


def get_unique_seq_list(*item_lists):
    """
    여러 목록에서 seq만 모아서 중복 제거하는 함수
    """
    seq_set = set()

    for items in item_lists:
        for item in items:
            seq = item.get("seq")

            if seq:
                seq_set.add(seq)

    return sorted(seq_set)


# ======================================================
# 12. 컬럼 통일 및 빈 값 처리 함수
# ======================================================

def normalize_item(item):
    """
    최종 JSON의 컬럼 구조를 통일하는 함수

    - 모든 데이터가 FINAL_FIELDS에 정의된 컬럼을 갖도록 함
    - 값이 없으면 '정보 없음'으로 채움
    - thumbnail과 imgUrl은 서로 보완
    """
    item = item.copy()

    # 이미지 필드 보완
    if not item.get("imgUrl") and item.get("thumbnail"):
        item["imgUrl"] = item.get("thumbnail")

    if not item.get("thumbnail") and item.get("imgUrl"):
        item["thumbnail"] = item.get("imgUrl")

    # 상세조회 상태 기본값
    if not item.get("detailStatus"):
        item["detailStatus"] = "not_requested"

    normalized = {}

    for field in FINAL_FIELDS:
        value = item.get(field)

        if value is None or value == "":
            normalized[field] = "정보 없음"
        else:
            normalized[field] = value

    return normalized


def normalize_items(items):
    """
    여러 데이터를 한 번에 컬럼 통일하는 함수
    """
    return [normalize_item(item) for item in items]


# ======================================================
# 13. JSON 저장 함수
# ======================================================

def save_items_to_json(items, file_name):
    """
    최종 병합 결과를 JSON 파일로 저장하는 함수
    """
    save_dir = BASE_DIR / "data"
    save_dir.mkdir(exist_ok=True)

    save_path = save_dir / file_name

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"JSON 저장 완료: {save_path}")


# ======================================================
# 14. 전체 API 실행
# ======================================================

if __name__ == "__main__":
    # 1. 문화캘린더정보 목록조회
    # 현재 최종 병합에는 사용하지 않지만, API 동작 확인용으로 호출
    livelihood_items = get_livelihood_list()
    print_items("1. 문화캘린더정보 목록조회 결과 20개", livelihood_items)

    # 2. 기간별 문화정보목록조회
    period_items = get_period_list()
    print_items("2. 기간별 문화정보목록조회 결과 20개", period_items)

    # 3. 지역별 문화정보목록조회
    area_items = get_area_list()
    print_items("3. 지역별 문화정보목록조회 결과 20개", area_items)

    # 4. 분야별 문화정보목록조회
    realm_items = get_realm_list()
    print_items("4. 분야별 문화정보목록조회 결과 20개", realm_items)

    # 5. period, area, realm에서 seq를 모두 모은 뒤 중복 제거
    seq_list = get_unique_seq_list(
        period_items,
        area_items,
        realm_items
    )

    print("\n" + "=" * 80)
    print("상세조회 대상 seq 개수")
    print("=" * 80)
    print(f"중복 제거된 seq 개수: {len(seq_list)}")

    # 6. 모든 seq에 대해 상세정보 조회
    detail_items = get_detail_list(seq_list)
    print_items("5. 문화정보 상세정보조회 결과", detail_items)

    # 7. seq 기준 중복 제거 및 병합
    # livelihood_items는 구조가 달라서 우선 제외
    merged_items = merge_items_by_seq(
        period_items,
        area_items,
        realm_items,
        detail_items
    )

    # 8. 모든 컬럼 통일 + 빈 값은 '정보 없음'으로 처리
    merged_items = normalize_items(merged_items)

    print_items("6. 중복 제거 후 통합 문화정보 결과", merged_items)

    print("\n" + "=" * 80)
    print("중복 제거 결과 요약")
    print("=" * 80)
    print(f"period_items 개수: {len(period_items)}")
    print(f"area_items 개수: {len(area_items)}")
    print(f"realm_items 개수: {len(realm_items)}")
    print(f"detail_items 개수: {len(detail_items)}")
    print(f"중복 제거 후 merged_items 개수: {len(merged_items)}")

    # 9. 최종 병합 JSON 하나만 저장
    save_items_to_json(merged_items, "culture_items_merged.json")