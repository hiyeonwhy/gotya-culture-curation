import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ======================================================
# 1. 기본 설정
# ======================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

SERVICE_KEY = os.getenv("CULTURE_API_KEY")

if not SERVICE_KEY:
    raise ValueError(
        f".env 파일에서 CULTURE_API_KEY 값을 찾을 수 없습니다. 확인 경로: {ENV_PATH}"
    )

BASE_URL = os.getenv(
    "CULTURE_API_BASE_URL",
    "http://apis.data.go.kr/B553457/cultureinfo",
)

START_DATE = "20260101"
END_DATE = "20261231"

# 종료일자가 이미 지난 데이터를 최대한 조회 단계에서 줄이기 위한 시작일
# START_DATE와 오늘 날짜 중 더 늦은 날짜를 사용합니다.
TODAY_TEXT = date.today().strftime("%Y%m%d")
QUERY_START_DATE = max(START_DATE, TODAY_TEXT)

SORT_STDR = "1"

FETCH_DETAILS = True

# livelihood는 기간 필터가 약해서 기본 제외합니다.
# 필요하면 True로 바꾸세요.
USE_LIVELIHOOD = False

# 도서는 알라딘 API를 따로 쓸 예정이면 False 추천
INCLUDE_H000_BOOK_CULTURE = False

AREA_FALLBACK_BY_SIDO = True

REQUEST_DELAY = 0.2
MAX_RETRIES = 3

COUNT_CHECK_ROWS = 3
FALLBACK_PAGE_SIZE = 100

ROWS_PARAM_NAME = "numOfrows"

# 외부 API 원본 저장 폴더
OUTPUT_DIR = BASE_DIR / "raw"

# 기존 output 안의 예전 결과 파일 정리 여부
CLEAN_PREVIOUS_OUTPUT = True


# ======================================================
# 2. endpoint 자동 설정
# ======================================================

def get_endpoint_map() -> Dict[str, str]:
    """
    BASE_URL 형태에 따라 endpoint 이름을 자동 설정합니다.

    기존 주소:
    http://apis.data.go.kr/B553457/cultureinfo
    -> livelihood2, period2, area2, realm2, detail2

    nopenapi 주소:
    .../publicperformancedisplays
    -> livelihood, period, area, realm, detail
    """
    lower_base_url = BASE_URL.lower()

    if "publicperformancedisplays" in lower_base_url:
        return {
            "livelihood": "livelihood",
            "period": "period",
            "area": "area",
            "realm": "realm",
            "detail": "detail",
        }

    return {
        "livelihood": "livelihood2",
        "period": "period2",
        "area": "area2",
        "realm": "realm2",
        "detail": "detail2",
    }


ENDPOINTS = get_endpoint_map()


# ======================================================
# 3. 문화 API 분류 기준
# ======================================================

SERVICE_TYPE_MAP = {
    "A": "공연/전시",
    "B": "행사/축제",
    "C": "교육/체험",
    "N": "기타/분류없음",
}

SERVICE_TP_CODES = ["A", "B", "C"]

CULTURE_CATEGORY_MAP = {
    "A000": {
        "realm_name": "연극",
        "main_category": "공연",
        "sub_category": "연극",
        "service_type_code": "A",
    },
    "B000": {
        "realm_name": "음악/콘서트",
        "main_category": "공연",
        "sub_category": "음악/콘서트",
        "service_type_code": "A",
    },
    "B002": {
        "realm_name": "국악",
        "main_category": "공연",
        "sub_category": "국악",
        "service_type_code": "A",
    },
    "C000": {
        "realm_name": "무용/발레",
        "main_category": "공연",
        "sub_category": "무용/발레",
        "service_type_code": "A",
    },
    "B003": {
        "realm_name": "뮤지컬/오페라",
        "main_category": "공연",
        "sub_category": "뮤지컬/오페라",
        "service_type_code": "A",
    },
    "D000": {
        "realm_name": "전시",
        "main_category": "전시",
        "sub_category": "전시",
        "service_type_code": "A",
    },
    "E000": {
        "realm_name": "아동/가족",
        "main_category": "가족·아동",
        "sub_category": "아동/가족",
        "service_type_code": "A",
    },
    "F000": {
        "realm_name": "행사/축제",
        "main_category": "축제·행사",
        "sub_category": "행사/축제",
        "service_type_code": "B",
    },
    "G000": {
        "realm_name": "교육/체험",
        "main_category": "교육·체험",
        "sub_category": "교육/체험",
        "service_type_code": "C",
    },
    "H000": {
        "realm_name": "도서",
        "main_category": "도서문화",
        "sub_category": "도서",
        "service_type_code": "N",
    },
    "I000": {
        "realm_name": "체육",
        "main_category": "스포츠·기타",
        "sub_category": "체육",
        "service_type_code": "N",
    },
    "L000": {
        "realm_name": "기타",
        "main_category": "스포츠·기타",
        "sub_category": "기타",
        "service_type_code": "N",
    },
}

CULTURE_CATEGORY_FILENAME_MAP = {
    "가족·아동": "family_children",
    "공연": "performances",
    "교육·체험": "education_experience",
    "스포츠·기타": "sports_other",
    "전시": "exhibitions",
    "축제·행사": "festivals_events",
}

CATEGORY_TAG_MAP = {
    "공연": ["공연", "실내", "감상"],
    "전시": ["전시", "미술관", "실내", "감상"],
    "축제·행사": ["축제", "행사", "야외", "체험"],
    "교육·체험": ["교육", "체험", "참여형"],
    "가족·아동": ["가족", "아동", "함께보기"],
    "스포츠·기타": ["체육", "활동", "기타"],
    "도서문화": ["도서", "독서", "문화행사"],
    "분류없음": ["문화"],
}

SIDO_LIST = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]

# 대분류별 JSON 파일에 저장할 최종 컬럼
# title은 저장하지 않고 name으로 저장합니다.
CATEGORY_OUTPUT_FIELDS = [
    "seq",
    "name",
    "cultureMainCategory",
    "cultureSubCategory",
    "realmCode",
    "realmName",
    "startDate",
    "endDate",
    "place",
    "area",
    "sigungu",
    "address",
    "longitude",
    "latitude",
    "gpsX",
    "gpsY",
    "thumbnail",
    "url",
    "phone",
    "price",
]

REMOVE_SINGLE_SOURCE_FIELDS = {
    "sourceOperation",
    "sourceServiceTp",
    "sourceRealmCode",
    "sourceSido",
}


# ======================================================
# 4. 공통 유틸 함수
# ======================================================

def remove_empty_params(params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if value is not None and value != ""
    }


def mask_service_key(url: str) -> str:
    if not SERVICE_KEY:
        return url

    return url.replace(SERVICE_KEY, "********")


def sanitize_xml_text(xml_text: str) -> str:
    """
    XML 파싱을 방해하는 잘못된 문자 보정

    - URL 안의 & 문자를 &amp;로 보정
    - XML에서 허용되지 않는 제어 문자 제거
    """
    xml_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", xml_text)

    xml_text = re.sub(
        r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)",
        "&amp;",
        xml_text,
    )

    return xml_text


def get_text(root: ET.Element, tag_name: str) -> Optional[str]:
    node = root.find(f".//{tag_name}")

    if node is None or node.text is None:
        return None

    return node.text.strip()


def parse_xml_response(xml_text: str) -> Tuple[List[Dict[str, str]], Optional[int]]:
    root = ET.fromstring(xml_text)

    total_count_text = get_text(root, "totalCount")
    total_count = None

    if total_count_text and total_count_text.isdigit():
        total_count = int(total_count_text)

    items = []

    for item in root.iter("item"):
        data = {}

        for child in item:
            data[child.tag] = child.text.strip() if child.text else ""

        items.append(data)

    return items, total_count


def request_api(
    endpoint: str,
    params: Dict[str, Any],
    print_url: bool = False,
) -> Tuple[List[Dict[str, str]], Optional[int]]:
    url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    clean_params = remove_empty_params(params)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=clean_params, timeout=30)
        except requests.exceptions.RequestException as error:
            print(f"요청 오류 발생: {error} / 재시도 {attempt}/{MAX_RETRIES}")
            time.sleep(REQUEST_DELAY * attempt)
            continue

        if print_url:
            print("요청 URL:", mask_service_key(response.url))

        if response.status_code != 200:
            print(f"HTTP 오류: {response.status_code} / 재시도 {attempt}/{MAX_RETRIES}")
            print(response.text[:500])
            time.sleep(REQUEST_DELAY * attempt)
            continue

        error_keywords = [
            "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
            "NO_OPENAPI_SERVICE_ERROR",
            "SERVICE ERROR",
            "Unexpected errors",
            "INVALID_REQUEST_PARAMETER_ERROR",
        ]

        if any(keyword in response.text for keyword in error_keywords):
            print("API 오류 응답:")
            print(response.text[:1000])
            return [], None

        try:
            return parse_xml_response(response.text)
        except ET.ParseError:
            print("XML 파싱 실패 - XML 보정 후 재시도합니다.")

            cleaned_xml = sanitize_xml_text(response.text)

            try:
                return parse_xml_response(cleaned_xml)
            except ET.ParseError:
                print("XML 보정 후에도 파싱 실패")
                print(response.text[:1000])
                return [], None

    return [], None


def parse_date_yyyymmdd(value: Any) -> Optional[date]:
    if value is None:
        return None

    value = str(value).strip()

    if not value or value == "정보 없음":
        return None

    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def is_date_ongoing(
    start_date: Any,
    end_date: Any,
    reference_date: Optional[date] = None,
) -> bool:
    if reference_date is None:
        reference_date = date.today()

    start = parse_date_yyyymmdd(start_date)
    end = parse_date_yyyymmdd(end_date)

    if start is None or end is None:
        return False

    return start <= reference_date <= end


def is_expired(
    end_date: Any,
    reference_date: Optional[date] = None,
) -> bool:
    """
    종료일자가 기준일보다 이전이면 True
    """
    if reference_date is None:
        reference_date = date.today()

    end = parse_date_yyyymmdd(end_date)

    if end is None:
        return False

    return end < reference_date


def filter_not_expired_items(
    items: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """
    종료일자가 이미 지난 데이터 제외
    """
    filtered_items = []
    expired_count = 0

    for item in items:
        if is_expired(item.get("endDate")):
            expired_count += 1
            continue

        filtered_items.append(item)

    return filtered_items, expired_count


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    value = str(value).strip()

    if not value or value == "정보 없음":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def has_valid_coordinates(item: Dict[str, Any]) -> bool:
    longitude = to_float(item.get("gpsX"))
    latitude = to_float(item.get("gpsY"))

    if longitude is None or latitude is None:
        return False

    return -180 <= longitude <= 180 and -90 <= latitude <= 90


def find_realm_code_from_realm_name(realm_name: str) -> Optional[str]:
    if not realm_name:
        return None

    for code, info in CULTURE_CATEGORY_MAP.items():
        if info["realm_name"] == realm_name:
            return code

    return None


def find_service_type_code_from_service_name(service_name: str) -> str:
    if not service_name:
        return "N"

    if "공연" in service_name or "전시" in service_name:
        return "A"

    if "행사" in service_name or "축제" in service_name:
        return "B"

    if "교육" in service_name or "체험" in service_name:
        return "C"

    return "N"


def unique_list(values: List[Any]) -> List[Any]:
    result = []
    seen = set()

    for value in values:
        if value is None or value == "":
            continue

        key = json.dumps(value, ensure_ascii=False, sort_keys=True)

        if key not in seen:
            seen.add(key)
            result.append(value)

    return result


# ======================================================
# 5. totalCount 기반 전체 조회 함수
# ======================================================

def get_total_count(
    endpoint: str,
    base_params: Dict[str, Any],
    label: str,
) -> int:
    params = base_params.copy()
    params["PageNo"] = 1
    params[ROWS_PARAM_NAME] = COUNT_CHECK_ROWS

    items, total_count = request_api(endpoint, params)

    if total_count is None:
        total_count = len(items)

    print(f"[{label}] totalCount 확인: {total_count}")

    return total_count


def fetch_all_items_by_total_count_once(
    endpoint: str,
    base_params: Dict[str, Any],
    label: str,
) -> List[Dict[str, str]]:
    total_count = get_total_count(endpoint, base_params, label)

    if total_count == 0:
        print(f"[{label}] 조회된 데이터 없음")
        return []

    params = base_params.copy()
    params["PageNo"] = 1
    params[ROWS_PARAM_NAME] = max(total_count, COUNT_CHECK_ROWS)

    print(f"[{label}] 한 페이지 전체 요청 시도: {ROWS_PARAM_NAME}={params[ROWS_PARAM_NAME]}")

    items, checked_total_count = request_api(endpoint, params)

    if checked_total_count is not None:
        total_count = checked_total_count

    print(f"[{label}] 한 페이지 요청 결과: {len(items)} / {total_count}")

    if len(items) >= total_count:
        return items

    print(f"[{label}] 한 페이지 전체 조회가 부족합니다. {FALLBACK_PAGE_SIZE}개 단위로 보완 조회합니다.")

    return fetch_all_items_by_page_fallback(endpoint, base_params, label, total_count)


def fetch_all_items_by_page_fallback(
    endpoint: str,
    base_params: Dict[str, Any],
    label: str,
    total_count: int,
) -> List[Dict[str, str]]:
    all_items = []
    total_pages = math.ceil(total_count / FALLBACK_PAGE_SIZE)

    for page_no in range(1, total_pages + 1):
        params = base_params.copy()
        params["PageNo"] = page_no
        params[ROWS_PARAM_NAME] = FALLBACK_PAGE_SIZE

        items, _ = request_api(endpoint, params)

        print(f"[{label}] 보완 조회 page={page_no}/{total_pages}, items={len(items)}")

        if not items:
            break

        all_items.extend(items)
        time.sleep(REQUEST_DELAY)

    return all_items


# ======================================================
# 6. 각 오퍼레이션 수집 함수
# ======================================================

def annotate_items(
    items: List[Dict[str, str]],
    operation: str,
    service_tp: Optional[str] = None,
    realm_code: Optional[str] = None,
    sido: Optional[str] = None,
) -> List[Dict[str, str]]:
    for item in items:
        item["sourceOperation"] = operation

        if service_tp:
            item["sourceServiceTp"] = service_tp

        if realm_code:
            item["sourceRealmCode"] = realm_code
            item["realmCode"] = realm_code

            realm_info = CULTURE_CATEGORY_MAP.get(realm_code)

            if realm_info and not item.get("realmName"):
                item["realmName"] = realm_info["realm_name"]

        if sido:
            item["sourceSido"] = sido

    return items


def collect_livelihood_items() -> List[Dict[str, str]]:
    print("\n" + "=" * 80)
    print("문화캘린더정보 목록조회 시작")
    print("=" * 80)

    params = {
        "serviceKey": SERVICE_KEY,
        "keyword": "",
    }

    items = fetch_all_items_by_total_count_once(
        ENDPOINTS["livelihood"],
        params,
        "livelihood",
    )

    return annotate_items(items, operation="livelihood")


def collect_period_items() -> List[Dict[str, str]]:
    print("\n" + "=" * 80)
    print("기간별 문화정보목록조회 시작")
    print("=" * 80)

    results = []

    for service_tp in SERVICE_TP_CODES:
        params = {
            "serviceKey": SERVICE_KEY,
            "from": QUERY_START_DATE,
            "to": END_DATE,
            "place": "",
            "gpsxfrom": "",
            "gpsyfrom": "",
            "gpsxto": "",
            "gpsyto": "",
            "keyword": "",
            "sortStdr": SORT_STDR,
            "serviceTp": service_tp,
        }

        label = f"period serviceTp={service_tp}"
        items = fetch_all_items_by_total_count_once(ENDPOINTS["period"], params, label)
        results.extend(annotate_items(items, operation="period", service_tp=service_tp))

    return results


def collect_area_items() -> List[Dict[str, str]]:
    print("\n" + "=" * 80)
    print("지역별 문화정보목록조회 시작")
    print("=" * 80)

    results = []

    for service_tp in SERVICE_TP_CODES:
        params = {
            "serviceKey": SERVICE_KEY,
            "sido": "",
            "sigungu": "",
            "from": QUERY_START_DATE,
            "to": END_DATE,
            "place": "",
            "gpsxfrom": "",
            "gpsyfrom": "",
            "gpsxto": "",
            "gpsyto": "",
            "keyword": "",
            "sortStdr": SORT_STDR,
            "serviceTp": service_tp,
        }

        label = f"area 전체 serviceTp={service_tp}"
        items = fetch_all_items_by_total_count_once(ENDPOINTS["area"], params, label)
        results.extend(annotate_items(items, operation="area", service_tp=service_tp))

    if results or not AREA_FALLBACK_BY_SIDO:
        return results

    print("sido 없이 지역별 전체 조회 결과가 없어 시도별 조회로 전환합니다.")

    for sido in SIDO_LIST:
        for service_tp in SERVICE_TP_CODES:
            params = {
                "serviceKey": SERVICE_KEY,
                "sido": sido,
                "sigungu": "",
                "from": QUERY_START_DATE,
                "to": END_DATE,
                "place": "",
                "gpsxfrom": "",
                "gpsyfrom": "",
                "gpsxto": "",
                "gpsyto": "",
                "keyword": "",
                "sortStdr": SORT_STDR,
                "serviceTp": service_tp,
            }

            label = f"area {sido} serviceTp={service_tp}"
            items = fetch_all_items_by_total_count_once(ENDPOINTS["area"], params, label)

            results.extend(
                annotate_items(
                    items,
                    operation="area",
                    service_tp=service_tp,
                    sido=sido,
                )
            )

    return results


def get_target_realm_codes() -> List[str]:
    realm_codes = list(CULTURE_CATEGORY_MAP.keys())

    if not INCLUDE_H000_BOOK_CULTURE:
        realm_codes = [code for code in realm_codes if code != "H000"]

    return realm_codes


def collect_realm_items() -> List[Dict[str, str]]:
    print("\n" + "=" * 80)
    print("분야별 문화정보목록조회 시작")
    print("=" * 80)

    results = []

    for realm_code in get_target_realm_codes():
        realm_info = CULTURE_CATEGORY_MAP[realm_code]
        service_type_code = realm_info["service_type_code"]

        params = {
            "serviceKey": SERVICE_KEY,
            "realmCode": realm_code,
            "from": QUERY_START_DATE,
            "to": END_DATE,
            "sido": "",
            "place": "",
            "gpsxfrom": "",
            "gpsyfrom": "",
            "gpsxto": "",
            "gpsyto": "",
            "keyword": "",
            "sortStdr": SORT_STDR,
            "serviceTp": service_type_code if service_type_code in SERVICE_TP_CODES else "",
        }

        label = f"realm {realm_code} {realm_info['realm_name']}"
        items = fetch_all_items_by_total_count_once(ENDPOINTS["realm"], params, label)

        results.extend(
            annotate_items(
                items,
                operation="realm",
                service_tp=params.get("serviceTp") or None,
                realm_code=realm_code,
            )
        )

    return results


def collect_detail_items(seq_list: List[str]) -> List[Dict[str, str]]:
    print("\n" + "=" * 80)
    print("문화정보 상세정보조회 시작")
    print("=" * 80)

    detail_results = []
    total = len(seq_list)

    for index, seq in enumerate(seq_list, start=1):
        print(f"상세정보 조회 중: {index}/{total} seq={seq}")

        params = {
            "serviceKey": SERVICE_KEY,
            "seq": seq,
        }

        items, _ = request_api(ENDPOINTS["detail"], params)

        if items:
            annotated = annotate_items(items, operation="detail")

            for item in annotated:
                item["detailStatus"] = "success"

            detail_results.extend(annotated)
        else:
            detail_results.append(
                {
                    "seq": seq,
                    "sourceOperation": "detail",
                    "detailStatus": "failed",
                }
            )

        time.sleep(REQUEST_DELAY)

    return detail_results


# ======================================================
# 7. 중복 제거 및 병합
# ======================================================

def get_unique_seq_list(*item_lists: List[Dict[str, str]]) -> List[str]:
    seq_set = set()

    for items in item_lists:
        for item in items:
            seq = item.get("seq")

            if seq:
                seq_set.add(seq)

    return sorted(seq_set)


def merge_metadata_list(existing: List[Any], new_value: Any) -> List[Any]:
    result = list(existing)

    if new_value:
        if isinstance(new_value, list):
            result.extend(new_value)
        else:
            result.append(new_value)

    return unique_list(result)


def merge_items_by_seq(*item_lists: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}

    for items in item_lists:
        for item in items:
            seq = item.get("seq")

            if not seq:
                continue

            source_operation = item.get("sourceOperation")
            source_service_tp = item.get("sourceServiceTp")
            source_realm_code = item.get("sourceRealmCode") or item.get("realmCode")
            source_sido = item.get("sourceSido")

            if seq not in merged:
                merged[seq] = item.copy()
                merged[seq]["sourceOperations"] = []
                merged[seq]["sourceServiceTps"] = []
                merged[seq]["sourceRealmCodes"] = []
                merged[seq]["sourceSidos"] = []

            target = merged[seq]

            target["sourceOperations"] = merge_metadata_list(
                target.get("sourceOperations", []),
                source_operation,
            )

            target["sourceServiceTps"] = merge_metadata_list(
                target.get("sourceServiceTps", []),
                source_service_tp,
            )

            target["sourceRealmCodes"] = merge_metadata_list(
                target.get("sourceRealmCodes", []),
                source_realm_code,
            )

            target["sourceSidos"] = merge_metadata_list(
                target.get("sourceSidos", []),
                source_sido,
            )

            is_detail = source_operation == "detail"

            for key, value in item.items():
                if value is None or value == "":
                    continue

                if key in REMOVE_SINGLE_SOURCE_FIELDS:
                    continue

                if not target.get(key):
                    target[key] = value
                    continue

                if is_detail:
                    target[key] = value

    return list(merged.values())


# ======================================================
# 8. 분류 및 저장용 데이터 정리
# ======================================================

def infer_realm_code(item: Dict[str, Any]) -> Optional[str]:
    if item.get("realmCode"):
        return str(item["realmCode"])

    source_realm_codes = item.get("sourceRealmCodes")

    if isinstance(source_realm_codes, list) and source_realm_codes:
        return str(source_realm_codes[0])

    realm_name = str(item.get("realmName", "")).strip()

    return find_realm_code_from_realm_name(realm_name)


def infer_service_type_code(item: Dict[str, Any], realm_code: Optional[str]) -> str:
    if realm_code and realm_code in CULTURE_CATEGORY_MAP:
        service_type_code = CULTURE_CATEGORY_MAP[realm_code]["service_type_code"]

        if service_type_code:
            return service_type_code

    source_service_tps = item.get("sourceServiceTps")

    if isinstance(source_service_tps, list) and source_service_tps:
        return str(source_service_tps[0])

    service_name = str(item.get("serviceName", "")).strip()

    return find_service_type_code_from_service_name(service_name)


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    item = item.copy()

    for field in REMOVE_SINGLE_SOURCE_FIELDS:
        item.pop(field, None)

    realm_code = infer_realm_code(item)

    realm_info = CULTURE_CATEGORY_MAP.get(
        realm_code,
        {
            "realm_name": item.get("realmName", "분류없음"),
            "main_category": "분류없음",
            "sub_category": item.get("realmName", "분류없음"),
            "service_type_code": "N",
        },
    )

    service_type_code = infer_service_type_code(item, realm_code)
    service_type_name = SERVICE_TYPE_MAP.get(service_type_code, "기타/분류없음")

    main_category = realm_info["main_category"]
    sub_category = realm_info["sub_category"]

    recommendation_tags = CATEGORY_TAG_MAP.get(main_category, ["문화"]) + [sub_category]

    if not item.get("imgUrl") and item.get("thumbnail"):
        item["imgUrl"] = item.get("thumbnail")

    if not item.get("thumbnail") and item.get("imgUrl"):
        item["thumbnail"] = item.get("imgUrl")

    longitude = to_float(item.get("gpsX"))
    latitude = to_float(item.get("gpsY"))

    is_ongoing = is_date_ongoing(item.get("startDate"), item.get("endDate"))

    is_festival = (
        realm_code == "F000"
        or main_category == "축제·행사"
        or item.get("realmName") == "행사/축제"
        or item.get("serviceName") == "행사/축제"
    )

    is_map_target = is_ongoing and is_festival and has_valid_coordinates(item)

    item["contentType"] = "CULTURE"
    item["serviceTypeCode"] = service_type_code
    item["serviceTypeName"] = service_type_name
    item["serviceName"] = item.get("serviceName") or service_type_name
    item["realmCode"] = realm_code or "정보 없음"
    item["realmName"] = item.get("realmName") or realm_info["realm_name"]
    item["cultureMainCategory"] = main_category
    item["cultureSubCategory"] = sub_category
    item["recommendationTags"] = sorted(set(recommendation_tags))
    item["detailStatus"] = item.get("detailStatus") or "not_requested"
    item["isOngoing"] = is_ongoing
    item["isFestival"] = is_festival
    item["isMapTarget"] = is_map_target
    item["longitude"] = longitude if longitude is not None else "정보 없음"
    item["latitude"] = latitude if latitude is not None else "정보 없음"
    item["address"] = item.get("placeAddr") or "정보 없음"

    return item


def normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_item(item) for item in items]


def make_category_item(item: Dict[str, Any]) -> Dict[str, Any]:
    result = {}

    for field in CATEGORY_OUTPUT_FIELDS:
        if field == "name":
            value = item.get("title")
        else:
            value = item.get(field)

        if value is None or value == "":
            result[field] = "정보 없음"
        else:
            result[field] = value

    return result


def group_items_by_main_category_for_save(
    items: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for item in items:
        category = str(item.get("cultureMainCategory", "분류없음"))
        save_item = make_category_item(item)
        grouped.setdefault(category, []).append(save_item)

    return grouped


# ======================================================
# 9. summary 생성
# ======================================================

def make_summary(
    items: List[Dict[str, Any]],
    raw_counts: Dict[str, int],
    expired_excluded_count: int,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "period": {
            "startDate": START_DATE,
            "queryStartDate": QUERY_START_DATE,
            "endDate": END_DATE,
        },
        "referenceDate": date.today().strftime("%Y%m%d"),
        "baseUrl": BASE_URL,
        "endpoints": ENDPOINTS,
        "rawCounts": raw_counts,
        "mergedTotalCountAfterFilter": len(items),
        "expiredExcludedCount": expired_excluded_count,
        "mapFestivalCount": 0,
        "savedColumns": CATEGORY_OUTPUT_FIELDS,
        "countByMainCategory": {},
        "countBySubCategory": {},
        "countByRealmCode": {},
        "countBySourceOperation": {},
    }

    for item in items:
        main_category = str(item.get("cultureMainCategory", "정보 없음"))
        sub_category = str(item.get("cultureSubCategory", "정보 없음"))
        realm_code = str(item.get("realmCode", "정보 없음"))

        summary["countByMainCategory"][main_category] = (
            summary["countByMainCategory"].get(main_category, 0) + 1
        )

        summary["countBySubCategory"][sub_category] = (
            summary["countBySubCategory"].get(sub_category, 0) + 1
        )

        summary["countByRealmCode"][realm_code] = (
            summary["countByRealmCode"].get(realm_code, 0) + 1
        )

        if item.get("isMapTarget"):
            summary["mapFestivalCount"] += 1

        source_operations = item.get("sourceOperations", [])

        if isinstance(source_operations, list):
            for operation in source_operations:
                summary["countBySourceOperation"][operation] = (
                    summary["countBySourceOperation"].get(operation, 0) + 1
                )

    return summary


# ======================================================
# 10. JSON 저장 함수
# ======================================================

def save_json(data: Any, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"JSON 저장 완료: {file_path}")


def clean_previous_output() -> None:
    """
    예전 실행 결과 중 현재 구조에서 쓰지 않는 파일을 정리합니다.
    data 폴더는 직접 삭제하지 않습니다.
    """
    if not CLEAN_PREVIOUS_OUTPUT:
        return

    old_files = [
        OUTPUT_DIR / "culture_all_operations_merged.json",
        OUTPUT_DIR / "culture_all_operations_grouped.json",
        OUTPUT_DIR / "culture_ongoing_festivals_for_map.json",
        OUTPUT_DIR / "culture_summary.json",
        *(
            OUTPUT_DIR / f"{file_name}.json"
            for file_name in CULTURE_CATEGORY_FILENAME_MAP.values()
        ),
    ]

    for file_path in old_files:
        if file_path.exists():
            file_path.unlink()
            print(f"기존 파일 삭제: {file_path}")

def save_category_files(
    grouped_items: Dict[str, List[Dict[str, Any]]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for category_name, items in grouped_items.items():
        safe_name = CULTURE_CATEGORY_FILENAME_MAP.get(
            category_name,
            "uncategorized",
        )

        save_json(items, OUTPUT_DIR / f"{safe_name}.json")


# ======================================================
# 11. 전체 실행
# ======================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("문화 API 전체 오퍼레이션 데이터 수집 시작")
    print("=" * 80)
    print(f"BASE_URL: {BASE_URL}")
    print(f"ENDPOINTS: {ENDPOINTS}")
    print(f"설정 시작일: {START_DATE}")
    print(f"실제 조회 시작일: {QUERY_START_DATE}")
    print(f"조회 종료일: {END_DATE}")
    print(f"저장 위치: {OUTPUT_DIR}")
    print(f"H000 도서문화 포함 여부: {INCLUDE_H000_BOOK_CULTURE}")
    print(f"livelihood 조회 여부: {USE_LIVELIHOOD}")

    # 0. 이전 output 결과 정리
    clean_previous_output()

    # 1. 오퍼레이션별 전체 수집
    if USE_LIVELIHOOD:
        livelihood_items = collect_livelihood_items()
    else:
        print("\n문화캘린더정보 목록조회는 기간 필터가 약해서 건너뜁니다.")
        livelihood_items = []

    period_items = collect_period_items()
    area_items = collect_area_items()
    realm_items = collect_realm_items()

    raw_counts = {
        "livelihood": len(livelihood_items),
        "period": len(period_items),
        "area": len(area_items),
        "realm": len(realm_items),
    }

    print("\n" + "=" * 80)
    print("목록 수집 완료")
    print("=" * 80)

    for operation, count in raw_counts.items():
        print(f"{operation}: {count}개")

    # 2. seq 중복 제거
    seq_list = get_unique_seq_list(
        livelihood_items,
        period_items,
        area_items,
        realm_items,
    )

    print(f"중복 제거된 seq 개수: {len(seq_list)}")

    # 3. 상세정보 조회
    if FETCH_DETAILS:
        detail_items = collect_detail_items(seq_list)
    else:
        detail_items = []

    raw_counts["detail"] = len(detail_items)

    # 4. seq 기준 병합
    merged_items = merge_items_by_seq(
        livelihood_items,
        period_items,
        area_items,
        realm_items,
        detail_items,
    )

    print("\n" + "=" * 80)
    print("중복 제거 및 병합 완료")
    print("=" * 80)
    print(f"병합 후 개수: {len(merged_items)}개")

    # 5. 분류 및 좌표 정리
    normalized_items = normalize_items(merged_items)

    # 6. 종료일자가 이미 지난 데이터 제외
    normalized_items, expired_excluded_count = filter_not_expired_items(normalized_items)

    print("\n" + "=" * 80)
    print("종료일자 기준 필터링 완료")
    print("=" * 80)
    print(f"종료일자가 지난 데이터 제외 개수: {expired_excluded_count}개")
    print(f"저장 대상 데이터 개수: {len(normalized_items)}개")

    # 7. 대분류별 저장 데이터 생성
    category_save_items = group_items_by_main_category_for_save(normalized_items)

    # 8. summary 생성
    summary = make_summary(
        items=normalized_items,
        raw_counts=raw_counts,
        expired_excluded_count=expired_excluded_count,
    )

    # 9. 최종 저장
    save_category_files(category_save_items)
    save_json(summary, OUTPUT_DIR / "culture_summary.json")

    print("\n" + "=" * 80)
    print("최종 저장 요약")
    print("=" * 80)
    print(f"전체 저장 데이터: {len(normalized_items)}개")
    print(f"종료일 지난 데이터 제외: {expired_excluded_count}개")
    print(f"지도 표시 가능 진행 중 축제 데이터: {summary['mapFestivalCount']}개")

    print("\n대분류별 개수")
    for category_name, count in summary["countByMainCategory"].items():
        print(f"- {category_name}: {count}개")

    print("\n저장 파일")
    print(f"- {OUTPUT_DIR / 'culture_summary.json'}")
    print(f"- {OUTPUT_DIR} (영문 카테고리별 JSON)")

    print("\n완료되었습니다.")
