# AppleTag Tracker 🍎

내 Apple ID로 등록된 AirTag(애플태그) 중 **선택한 태그의 위치를 5분마다 자동으로
기록**하고, 누적된 경로를 **웹 지도(OpenStreetMap)** 위에 표시하는 도구입니다.

## 동작 방식

Apple은 AirTag 위치에 대한 **공식 공개 API를 제공하지 않습니다.** 이 프로젝트는
macOS의 "나의 찾기(Find My)" 앱이 남기는 로컬 캐시 파일을 읽어서 위치를 가져옵니다:

```
~/Library/Caches/com.apple.findmy.fmipcore/Items.data
```

즉, **AirTag와 같은 Apple ID로 로그인된 Mac에서** 실행해야 하며, "나의 찾기" 앱이
백그라운드에서 위치를 갱신하고 있어야 합니다.

```
┌──────────────┐   5분마다    ┌──────────────┐         ┌─────────────┐
│ Find My 캐시 │ ─읽기─────▶ │  Python 백엔드 │ ─저장─▶ │  SQLite DB  │
│ (Items.data) │            │   (FastAPI)    │         │ (경로 이력) │
└──────────────┘            └──────┬─────────┘         └─────────────┘
                                   │ REST API
                                   ▼
                            ┌──────────────┐
                            │ 웹 지도 (Leaflet│
                            │ + OpenStreetMap)│
                            └──────────────┘
```

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행

### 1) 실제 Mac에서 (실데이터)

iCloud에 로그인하고 "나의 찾기" 앱을 한 번 이상 실행한 뒤:

```bash
python run.py
```

브라우저에서 http://127.0.0.1:8000 접속.

### 2) Mac이 아닌 환경에서 (샘플 데이터로 미리보기)

```bash
APPLETAG_ITEMS_PATH=sample/Items.data python run.py
```

## 사용법

1. 왼쪽 사이드바에 등록된 AppleTag 목록이 표시됩니다.
2. 추적하고 싶은 태그의 체크박스를 켭니다 → 선택이 저장되고 5분마다 위치가 기록됩니다.
3. 지도에 각 태그의 이동 경로가 색깔별 선과 점으로 표시됩니다. (가장 큰 점 = 최신 위치)
4. "지금 위치 기록" 버튼으로 즉시 한 번 샘플링할 수 있습니다.

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `APPLETAG_ITEMS_PATH` | `~/Library/Caches/com.apple.findmy.fmipcore/Items.data` | FindMy 캐시 경로 |
| `APPLETAG_DB_PATH` | `./tracking.db` | SQLite 경로 |
| `APPLETAG_POLL_INTERVAL` | `300` (5분) | 폴링 주기(초) |
| `APPLETAG_HOST` | `127.0.0.1` | 서버 호스트 |
| `APPLETAG_PORT` | `8000` | 서버 포트 |

## 참고 / 한계

- 위치 갱신 빈도는 결국 Apple의 "나의 찾기" 네트워크에 달려 있습니다. 5분마다 캐시를
  읽지만, 캐시 자체가 갱신되지 않았다면 같은 위치가 중복 저장되지 않도록 처리합니다.
- 본인 소유 기기의 위치 확인 용도로만 사용하세요.

## 구조

```
backend/
  config.py     설정 (환경변수)
  findmy.py     Items.data 읽기/파싱
  database.py   SQLite (선택 상태 + 위치 이력)
  scheduler.py  5분 폴링 루프
  app.py        FastAPI (REST + 정적 프론트엔드)
frontend/
  index.html, app.js, style.css   Leaflet 지도 UI
sample/Items.data   테스트용 샘플 데이터
run.py              실행 진입점
```
