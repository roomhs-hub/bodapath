# 로컬 미리보기 전용 실행 스크립트
# - 운영(NAS) DB에는 절대 연결하지 않고, 이 PC 안의 임시 SQLite DB만 사용합니다.
# - 운영과 별개의 포트(5050)에서 실행되어 배포된 사이트와 충돌하지 않습니다.
# - .env 파일이 있어도 아래 값들이 항상 우선 적용됩니다 (운영 DB 오염 방지).

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$env:APP_PASSWORD = "local1234"
$env:SECRET_KEY = "local-preview-secret-key"
$env:FLASK_DEBUG = "1"
$env:PORT = "5050"
$env:DATABASE_URL = "sqlite:///$PSScriptRoot/instance/dev_local.db"

if (-not (Test-Path ".venv")) {
    Write-Host "가상환경(.venv)이 없어 새로 만듭니다..."
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

Write-Host "필요한 패키지를 설치/업데이트합니다..."
pip install -q -r requirements.txt

Write-Host ""
Write-Host "==============================================="
Write-Host " 로컬 미리보기 서버를 시작합니다."
Write-Host " 접속 주소: http://127.0.0.1:5050"
Write-Host " 로그인 비밀번호: local1234"
Write-Host " 종료하려면 이 창에서 Ctrl+C 를 누르세요."
Write-Host "==============================================="
Write-Host ""

python wsgi.py
