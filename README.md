<div align="center">

<img src="frontend/src/assets/images/logo.png" alt="GotYA Logo" width="180" />

# 🎰 GotYA — 문화 취향 큐레이션 서비스

**"오늘 뭐 하지?"** — 13문항의 취향 테스트로 나의 문화 취향 유형을 찾고,<br/>
영화 · 도서 · 문화생활 콘텐츠를 AI가 큐레이션해 주는 웹 서비스

![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?logo=vite&logoColor=white)
![Pinia](https://img.shields.io/badge/Pinia-3.0-FFD859?logo=pinia&logoColor=black)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.16-A30000?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Local%20Development-orange)

</div>

---

## 📖 프로젝트 개요

주말이나 퇴근 후에 **"오늘 뭐 하지?"** 를 검색하다 보면, 정작 취향에 맞지 않는 콘텐츠만 잔뜩 보게 됩니다.
영화·도서·전시/공연 정보는 각각 다른 서비스에 흩어져 있고, 추천 로직은 대부분 "인기순"에 머물러 있기 때문입니다.

**GotYA**는 이 문제를 *취향*이라는 하나의 축으로 묶어 해결합니다.

1. 사용자는 13문항의 **취향 테스트**를 진행하고, 6가지 문화 취향 유형 중 하나를 부여받습니다.
2. 취향 유형과 좋아요/싫어요 반응 데이터를 근거로 **LLM이 콘텐츠를 큐레이션**합니다.
3. 영화·도서·문화생활을 한곳에서 탐색하고, **전국 문화지도**에서 내 지역의 공연·전시·축제를 확인합니다.

> 뽑기 기계(Gotcha)에서 캡슐이 나오듯, 취향에 맞는 콘텐츠를 하나씩 건져 올린다는 의미에서 **GotYA**라는 이름을 붙였습니다.

---

## ✨ 주요 기능

### 🎯 취향 테스트 & 유형 진단
13개의 A/B 문항에 답하면 문항별 점수 규칙(`TasteScoreRule`)이 합산되어 6가지 문화 취향 유형 중 하나가 결정됩니다.
질문·유형·점수 정책은 모두 DB에 저장되어 있어 코드 수정 없이 테스트 구성을 바꿀 수 있습니다.

### 🤖 AI 기반 콘텐츠 추천
취향 유형에서 도출한 키워드로 후보군을 추린 뒤(`candidate_selector`), LLM에 프로필을 전달해 추천 결과를 생성합니다(`recommendation_service`).
사용자가 남긴 **좋아요/싫어요 피드백**이 후속 추천의 입력으로 다시 반영됩니다.

### 🎬 콘텐츠 라운지 (영화 · 도서 · 문화생활)
알라딘 도서 데이터, 영화 데이터, 문화행사 데이터를 통합 스키마(`ContentItem` + 타입별 Detail)로 관리합니다.
무한 스크롤·상세 모달·찜하기·좋아요/싫어요를 지원합니다.

### 🗺️ 전국 문화지도
Kakao Map SDK와 시·도 GeoJSON 폴리곤을 결합해 지역별 **공연/전시/축제** 분포를 시각화하고, 지역을 클릭하면 해당 지역 행사 목록을 조회합니다.

### 💬 커뮤니티 & 마이페이지
게시글·댓글 CRUD(작성자 권한 검증 포함), 찜 목록 관리, "다시 보지 않기" 콘텐츠 관리, 프로필 수정을 제공합니다.

---

## 🛠 기술 스택

| 구분 | 기술 |
| --- | --- |
| **Frontend** | Vue 3 (Composition API), Vite 6, Vue Router 4, Pinia 3, Axios, Kakao Map JavaScript SDK |
| **Backend** | Django 5.2, Django REST Framework 3.16, dj-rest-auth, django-allauth, django-cors-headers |
| **Database** | SQLite 3 (개발 환경 기본값) |
| **AI / 외부 API** | OpenAI 호환 LLM 엔드포인트(GMS), 알라딘 도서 API, TourAPI 문화행사, Kakao Map |
| **인증** | DRF Token Authentication (`Authorization: Token <key>`) |

---

## 🚀 시작하기 (Getting Started)

### 사전 요구 사항

| 항목 | 권장 버전 |
| --- | --- |
| Python | 3.11 이상 |
| Node.js | 18 이상 |
| npm | 9 이상 |

> 문화지도 기능을 사용하려면 **Kakao Developers JavaScript 키**가, AI 추천 기능을 사용하려면 **OpenAI 호환 LLM 엔드포인트와 키**가 필요합니다.

### 1️⃣ 저장소 클론

```bash
git clone <repository-url>
cd gotya-culture-curation
```

### 2️⃣ 백엔드 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# DB 마이그레이션
cd backend
python manage.py migrate

# 취향 테스트 설정 + 영화/도서/문화 데이터 일괄 적재
python manage.py sync_all_contents

# 개발 서버 실행 (http://127.0.0.1:8000)
python manage.py runserver
```

<details>
<summary>📦 데이터 적재 명령어를 개별 실행하려면</summary>

```bash
python manage.py sync_taste_config   # 취향 유형 · 질문 · 점수 규칙
python manage.py sync_movies         # 영화 데이터
python manage.py sync_books          # 도서 데이터 (알라딘)
python manage.py sync_cultures       # 문화행사 데이터
```

</details>

### 3️⃣ 백엔드 환경 변수

**프로젝트 루트**에 `.env` 파일을 만들고 LLM 추천에 필요한 값을 채웁니다.
(`config/settings.py`가 `python-dotenv`로 루트 `.env`와 `backend/tastes/.env`를 순서대로 로드하며, 값이 없으면 AI 추천 기능만 비활성화됩니다.)

```dotenv
GMS_API_URL=https://<your-openai-compatible-endpoint>
GMS_API_KEY=<your-api-key>
GMS_MODEL=gpt-5-nano            # 선택, 기본값 gpt-5-nano
GMS_TIMEOUT_SECONDS=20          # 선택, 기본값 20
GMS_CANDIDATES_PER_TYPE=30      # 선택, 기본값 30
```

### 4️⃣ 프론트엔드 설정

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

`frontend/` 디렉터리에 `.env` 파일을 만들고 Kakao 지도 키를 설정합니다.

```dotenv
VITE_KAKAO_MAP_JS_KEY=<kakao-javascript-key>
```

> Vite 개발 서버가 `/api` 요청을 `http://127.0.0.1:8000`으로 프록시하므로, **백엔드와 프론트엔드를 함께 실행**해야 합니다.

### 5️⃣ 빌드

```bash
cd frontend
npm run build       # dist/ 생성
npm run preview     # 빌드 결과 미리보기
```

---

## 💡 사용법 (Usage)

### 화면 흐름

```
홈 (/)
 └─ 취향 테스트 시작 (/taste-test)
     └─ 13문항 응답 (/taste-test/questions)
         └─ 유형 결과 + AI 추천 (/taste-test/recommendations)
             ├─ 콘텐츠 라운지 (/movies · /books · /cultures)
             ├─ 전국 문화지도 (/cultures/map)
             ├─ 커뮤니티 (/community)
             └─ 마이페이지 (/mypage) — 찜 목록 · 숨긴 콘텐츠 · 프로필 수정
```

로그인이 필요한 라우트는 `router/index.js`의 네비게이션 가드가 보호하며, 미인증 시 `redirect` 쿼리를 붙여 로그인 페이지로 이동합니다.

### API 예시

```bash
# 1. 로그인 — 토큰 발급
curl -X POST http://127.0.0.1:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"login_id": "gotya", "password": "your-password"}'

# 2. 취향 테스트 결과 제출 (등록된 13개 질문에 모두 답변해야 합니다)
curl -X POST http://127.0.0.1:8000/api/tastes/test/results/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"answers": [{"question_id": 1, "answer": "A"}, {"question_id": 2, "answer": "B"}]}'

# 3. AI 추천 생성 (per_type: 유형별 추천 개수, 기본 3)
curl -X POST http://127.0.0.1:8000/api/tastes/recommendations/generate/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"per_type": 3}'

# 4. 영화 목록 조회 (페이지네이션)
curl "http://127.0.0.1:8000/api/movies/?page=1"
```

### 주요 API 엔드포인트

| 도메인 | 엔드포인트 | 설명 |
| --- | --- | --- |
| 인증 | `POST /api/accounts/signup/` · `login/` · `logout/`<br/>`GET /api/accounts/me/` | 회원가입 · 로그인 · 로그아웃 · 내 정보 |
| 취향 테스트 | `GET /api/tastes/test/config/`<br/>`POST /api/tastes/test/results/`<br/>`GET /api/tastes/test/results/latest/` | 테스트 설정 조회 · 결과 제출 · 최근 결과 |
| 추천 | `GET /api/tastes/recommendations/preview/`<br/>`POST /api/tastes/recommendations/generate/` | 추천 미리보기 · AI 추천 생성 |
| 반응 | `GET/POST /api/tastes/bookmarks/`, `bookmarks/toggle/`<br/>`POST /api/tastes/feedback/` | 찜하기 · 좋아요/싫어요 |
| 콘텐츠 | `GET /api/movies/`, `/api/books/`, `/api/cultures/`<br/>`GET /api/cultures/regions/summary/` | 목록·상세 조회 · 지역별 문화행사 요약 |
| 커뮤니티 | `GET/POST /api/community/posts/`<br/>`GET/PUT/DELETE /api/community/posts/<id>/`<br/>`/api/community/comments/<id>/` | 게시글 · 댓글 CRUD |

관리자 페이지는 `http://127.0.0.1:8000/admin/` 에서 확인할 수 있습니다.

---

## 📂 폴더 구조

```text
gotya-culture-curation/
├─ backend/                      # Django REST API
│  ├─ config/                    # settings · urls · wsgi/asgi
│  ├─ accounts/                  # 커스텀 User, 회원가입/로그인/프로필
│  ├─ tastes/                    # 취향 테스트 · 추천 · 찜/피드백 (핵심 도메인)
│  │  ├─ services/
│  │  │  ├─ taste_test_service.py       # 응답 채점 → 유형 판정
│  │  │  ├─ profile_builder.py          # 사용자 취향 프로필 구성
│  │  │  ├─ candidate_selector.py       # 추천 후보군 선별
│  │  │  ├─ gms_client.py               # LLM 엔드포인트 클라이언트
│  │  │  ├─ recommendation_mapping.py   # 유형 ↔ 콘텐츠 매핑 규칙
│  │  │  └─ recommendation_service.py   # 추천 파이프라인 오케스트레이션
│  │  └─ management/commands/    # sync_taste_config, sync_all_contents
│  ├─ movies/ · books/ · cultures/   # 콘텐츠 도메인 (models·views·sync 커맨드)
│  ├─ community/                 # 게시글 · 댓글 · 작성자 권한
│  ├─ fixtures/                  # 초기 데이터 / 더미 데이터
│  └─ manage.py
│
├─ frontend/                     # Vue 3 + Vite SPA
│  └─ src/
│     ├─ api/index.js            # axios 인스턴스 · 토큰 인터셉터
│     ├─ router/index.js         # 라우트 정의 · 인증 가드
│     ├─ stores/                 # Pinia (auth · tasteTest · recommendations 등)
│     ├─ views/                  # 페이지 단위 컴포넌트
│     ├─ components/             # AppHeader, CultureMap
│     ├─ utils/loadKakaoMap.js   # Kakao Map SDK 지연 로딩
│     └─ assets/                 # 테마 CSS · 폰트 · 이미지 · GeoJSON
│
├─ docs/PROJECT_REPORT.md        # 팀 인수인계서 · ERD · 개발 회고
├─ requirements.txt
└─ README.md
```

> 데이터베이스 ERD와 팀 단위 개발 기록은 [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md)에 정리되어 있습니다.

---

## 🤝 기여 방법 (Contributing)

기여는 언제나 환영합니다! 아래 절차를 따라주세요.

1. 이 저장소를 **Fork** 합니다.
2. 기능 브랜치를 생성합니다. — `git checkout -b feat/amazing-feature`
3. 변경 사항을 커밋합니다. — `git commit -m "feat: 멋진 기능 추가"`
4. 브랜치에 푸시합니다. — `git push origin feat/amazing-feature`
5. **Pull Request**를 생성합니다.

### 커밋 컨벤션

| Prefix | 용도 |
| --- | --- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `style` | 코드 포맷팅 (기능 변경 없음) |
| `refactor` | 코드 리팩터링 |
| `chore` | 빌드·설정 등 기타 작업 |

---

## 📄 라이선스 (License)

현재 저장소에는 별도의 `LICENSE` 파일이 없습니다. 배포 계획에 맞춰 팀에서 라이선스를 정한 뒤 루트에 `LICENSE` 파일을 추가해 주세요.

> ⚠️ 단, `frontend/src/assets/fonts/`의 폰트(예: [Mulmaru-LICENSE.txt](frontend/src/assets/fonts/Mulmaru-LICENSE.txt))와
> 알라딘·TourAPI·Kakao 등 외부 API로 수집한 데이터는 각 제공처의 라이선스 및 이용약관을 따릅니다.

---

<div align="center">

**GotYA** — 오늘 뭐 하지? 🎰

</div>
