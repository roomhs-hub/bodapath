# 업무 인수인계 시스템

퇴사자 → 신규 담당자 업무 인수인계용 웹 애플리케이션. 자세한 설계 배경은 `업무인수인계_시스템_설계서.md`를 참고하세요.

## 로컬 개발 환경 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # 값 채우기 (APP_PASSWORD, SECRET_KEY 등)

# 로컬에서 빠르게 확인만 하려면 DATABASE_URL을 지우면 SQLite(instance/dev.db)로 자동 동작합니다.
python wsgi.py
```

브라우저에서 http://localhost:5000 접속 → `.env`의 `APP_PASSWORD`로 로그인.

## Docker로 실행 (PostgreSQL 포함)

```bash
cp .env.example .env   # 값 채우기
docker compose up -d --build
```

`app` 컨테이너가 5000번 포트로 뜨고, `db` 컨테이너(PostgreSQL)와 같은 네트워크로 통신합니다.

## 폰트 적용

`app/static/fonts/` 폴더에 아래 파일을 복사하세요 (원본: `Y:\HONGSIK\06.AI놀이터\스타일가이드자료\폰트-이미지\`).

- KIMM_bold.ttf
- NanumGothic.ttf
- NanumGothicBold.ttf
- NanumGothicLight.ttf

## NAS 배포 (GitHub Actions)

1. GitHub Private 저장소 생성 후 이 프로젝트를 push합니다.
2. 저장소 Settings → Secrets and variables → Actions에서 아래 Secret을 등록합니다.
   - `NAS_HOST`, `NAS_PORT`, `NAS_USER`, `NAS_SSH_KEY` (기존 프로젝트와 공용 값 재사용)
   - `NAS_DEPLOY_PATH` (예: `/volume2/docker/업무인수인계`)
3. NAS에 SSH 접속하여 `NAS_DEPLOY_PATH` 위치에 이 저장소를 최초 1회 clone하고, `.env` 파일을 직접 만들어 둡니다(저장소에는 커밋되지 않으므로 서버에서 직접 작성).
4. DSM 제어판 → 로그인 포털 → 고급 → 역방향 프록시에서 `bodapath.siki.kr:443` → `localhost:5000` 규칙을 등록합니다(이미 등록 완료됨).
5. `main` 브랜치에 push하면 GitHub Actions가 자동으로 SSH 접속 → `git pull` → `docker compose up -d --build`를 실행합니다.

## 필드/화면 구성

- 로그인 → 입력 → 리스트 → 수정 → 통합검색 → 관리자(필드관리 포함)
- 관리자 화면에서 필드 사용/미사용, 필수 여부, 순서, 신규 필드 추가, 선택항목 관리, CSV 백업이 가능합니다.
