# 2대 PC 운영 설치 순서 (현재 PC=사용자 시운전, VPN PC=중앙 서버)

요구사항: 현재 PC에서는 사내 VPN 불가, VPN 가능한 다른 PC가 서버 역할 수행.

---

## 🧒 완전 초보(처음 프로그래밍)용 한 줄 요약
- **서버 PC**는 "데이터를 모으는 컴퓨터"예요.
- **사용자 PC**는 "화면만 보는 컴퓨터"예요.
- 즉, 중요한 설치는 서버 PC에서 먼저 합니다.

---

## 🏗 현재 조건(3~4명/사내망) 기준 추천 배포 구조
- **서버 위치**: 내 PC(임시 운영)
- **접속 방식**: 팀원 브라우저에서 `http://내PC_IP:8000`
- **네트워크 범위**: 사내망/로컬 서브넷만 허용
- **운영 방식**: Docker Desktop + `docker compose up -d`

구조:

```text
[내 PC: Docker로 서버 실행]
        ↓
http://내PC_IP:8000
        ↓
[팀원 3~4명 브라우저 접속]
```

왜 이 구성이 현실적인가?
- 인원 3~4명 + 사내망이면 성능/운영 부담이 낮음
- Docker로 환경충돌 줄이고, 추후 서버 이전도 쉬움
- 로그인만 붙여도 초기 운영 보안 수준이 충분히 확보됨

---

## 🚀 서버 PC를 "처음 켠 직후" 실행하는 절차 (OS별로 분리)

아래는 **매일 아침 PC를 켠 뒤** 바로 따라하는 절차입니다.

### A. Windows 서버 PC (PowerShell 기준)

#### A-1) 무엇을 열어야 하나?
- **PowerShell**을 엽니다. (권장: 관리자 권한)

#### A-2) 프로젝트 폴더로 이동
```powershell
cd C:\Users\jh240902\bloom
```

> 중요: `bloom` 폴더 **안에서** 실행해야 합니다. `C:\Users\jh240902` 상위 폴더에서 실행하면 예전 설치본이 잡힐 수 있습니다.

#### A-3) 기존 8000 포트 서버 정리(있을 때만)
```powershell
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  $listenerPid = $listener.OwningProcess
  Stop-Process -Id $listenerPid -Force
}
```

#### A-4) 가상환경 활성화 + 서버 실행
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn --app-dir src bloom.main:app --host 0.0.0.0 --port 8000
```

#### A-5) 새 PowerShell 창에서 상태 확인
```powershell
(Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing).Content
(Invoke-WebRequest http://127.0.0.1:8000/dashboard -UseBasicParsing).StatusCode
```

#### A-6) 사용자 접속 주소
- 서버 로컬: `http://127.0.0.1:8000/dashboard`
- 다른 PC: `http://<서버IP>:8000/dashboard`
- 서버 IP 확인 명령:
```powershell
ipconfig
```

---

### B. Ubuntu 서버 PC (Terminal 기준)

#### B-1) 무엇을 열어야 하나?
- **Ubuntu Terminal** (`Ctrl + Alt + T`)

#### B-2) 프로젝트 폴더로 이동
```bash
cd ~/Bloom
```

#### B-3) 가상환경 활성화 + 서버 실행
```bash
source .venv/bin/activate
python -m uvicorn --app-dir src bloom.main:app --host 0.0.0.0 --port 8000
```

#### B-4) 새 Terminal에서 상태 확인
```bash
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:8000/dashboard
```

#### B-5) 사용자 접속 주소
```bash
hostname -I
```
- 예: `http://10.20.30.40:8000/dashboard`

---

## 🔐 로그인/보안 최소 기준 (반드시 적용)

### 로그인
- 최소: 로그인 페이지 + 계정 검증 + 세션 유지
- 권장: 비밀번호 해시(bcrypt) + JWT/세션 만료 + 접속 로그

### Windows 방화벽
- 인바운드에서 **8000 포트 허용**
- 범위는 **로컬 서브넷만** 허용
- 외부 인터넷 대역은 차단

### 운영 수칙
- 관리자 권한으로 앱 직접 실행하지 않기
- 80 포트 대신 3000/8000 사용
- 개인 PC가 꺼지면 서비스도 중단됨(임시 운영 한계)

---

## ❗ 지금 코드 기준 "계속 수집 중인가요?" 답변
결론부터:
- **아직은 자동 크롤링이 계속 도는 상태가 아닙니다.**
- 현재는 `uvicorn`으로 API/대시보드 서버가 켜져 있고, 데모 데이터 응답이 동작하는 단계입니다.
- Webview 실제 로그인/파싱/주기 저장 스케줄러는 운영 전 구현 항목입니다.

왜 이렇게 보냐면:
- `src/bloom/crawler/webview_client.py`는 골격(stub) 상태
- `main.py`에는 APScheduler/Celery 같은 주기 작업 등록 코드가 없음

즉, 지금 서버 PC를 켜두면:
- ✅ 대시보드/API 제공
- ❌ Webview를 24시간 자동 수집/저장 (아직 미구현)

---

## 🧠 램/가상메모리 걱정은?
현재 단계(3~4명, 사내망, 데모 API)에서는 보통 크게 문제되지 않습니다.

실무 기준으로는 아래를 권장합니다.
1. **최소 메모리 권장**: 8GB 이상(권장 16GB)
2. **동시 접속 3~4명**: FastAPI 자체 부하는 낮은 편
3. **주의 지점**: 브라우저 자동화(Playwright) 크롤러를 붙이면 메모리 사용량이 증가
4. **가상메모리(페이지파일)**: Windows 기본 자동 관리 ON 유지 권장

### 서버 PC에서 바로 체크하는 법
- RAM/CPU: 작업 관리자 > 성능 탭
- Docker 메모리: Docker Desktop > Settings > Resources
- DB 상태: `docker compose ps`
- 앱 상태: `curl http://127.0.0.1:8000/health`

### 운영 안정화 팁
- 시작은 60초 수집 주기(추후 실제 크롤러 연결 시)
- 장애 대비: 하루 1회 앱/DB 상태 점검
- 장기 운영 전: 개인 PC -> 사내 VM/서버로 이전 권장

---

## 🔍 "어디서, 어떻게 확인해요?" 빠른 확인표
| 확인할 것 | 어디서 확인? | 확인 방법 |
|---|---|---|
| 서버 프로그램이 켜졌는지 | 서버 PC 터미널 | `curl http://127.0.0.1:8000/health` |
| 사이트 목록이 내려오는지 | 서버 PC 터미널 | `curl http://127.0.0.1:8000/api/master-sites` |
| 대시보드 화면이 뜨는지 | 서버 PC 브라우저 | `http://127.0.0.1:8000/dashboard` 접속 |
| 다른 PC에서도 접속되는지 | 사용자 PC 브라우저 | `http://<서버IP>:8000/dashboard` 접속 |
| DB 컨테이너가 살아있는지 | 서버 PC 터미널 | `docker compose ps`에서 `db`가 `Up`인지 확인 |
| 서버 로그가 정상인지 | 서버 PC 터미널 | `journalctl -u bloom -f` (systemd 사용 시) |

> 딱 3개만 먼저 보면 됩니다: `health`, `master-sites`, `dashboard`.

---

## 0) 준비물 체크 (먼저 이것부터)
서버 PC 앞에 앉아서 아래 4개를 준비해 주세요.

1. 인터넷 연결
2. 사내 VPN 연결 가능 상태
3. 설치 권한(관리자 권한) 있는 계정
4. 이 프로젝트의 Git 저장소 주소(예: `https://...`)

---

## 1) 서버 PC에 프로그램 설치하기 (정말 천천히)

> 아래는 **Ubuntu/Linux 기준**입니다.  
> (만약 Windows 서버라면, 마지막에 "Windows 메모"를 참고하세요.)

### 1-1. 터미널 열기
- 키보드에서 `Ctrl + Alt + T`를 눌러 터미널을 엽니다.

### 1-2. Git / Python / Docker 설치
아래 명령을 **한 줄씩** 복사해서 실행하세요.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip docker.io docker-compose-plugin
```

설치 확인:

```bash
git --version
python3 --version
docker --version
docker compose version
```

### 1-3. Docker 실행 준비
```bash
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

- 위 2번째 명령을 실행하면 권한이 바뀝니다.
- **중요:** 터미널을 닫고 다시 열거나, 서버 PC를 한 번 재로그인하세요.

확인:
```bash
docker ps
```

### 1-4. 프로젝트 받기 (clone)
`<repo_url>` 자리에 실제 주소를 넣으세요.

```bash
git clone <repo_url> Bloom
cd Bloom
```

### 1-5. 파이썬 가상환경 만들기
```bash
python3 -m venv .venv
source .venv/bin/activate
```

성공하면 터미널 왼쪽에 `(.venv)`가 보입니다.

### 1-6. 프로젝트 의존성 설치
```bash
pip install -e .
cp .env.example .env
```

### 1-7. 데이터베이스(DB) 실행
```bash
docker compose up -d db
docker compose ps
```

- `db`가 `Up`으로 보이면 성공입니다.

### 1-8. 서버 실행
```bash
source .venv/bin/activate
uvicorn bloom.main:app --host 0.0.0.0 --port 8000
```

- 이 명령을 실행하면 서버가 켜진 상태로 계속 떠 있습니다.
- 이 창은 닫지 마세요(닫으면 서버도 꺼짐).

---

## 2) 서버 PC에서 "정상 동작" 확인
서버 PC에서 새 터미널을 하나 더 열고 아래를 실행하세요.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/master-sites
```

정상이면:
- `/health`는 `{"status":"ok", ...}` 비슷한 JSON이 나옵니다.
- `/api/master-sites`는 site 목록 JSON이 나옵니다.

브라우저 확인:
- 서버 PC 브라우저에서 `http://127.0.0.1:8000/dashboard`

---

## 3) 사용자 PC에서 접속하기

### 3-1. 서버 IP 확인 (서버 PC에서)
```bash
hostname -I
```

예: `10.20.30.40` 같은 값이 나옵니다.

### 3-2. 사용자 PC에서 브라우저 열기
아래 주소로 접속:

- `http://<서버IP>:8000/dashboard`
- 예: `http://10.20.30.40:8000/dashboard`

### 3-3. 화면 테스트 순서
1. `+추가` 버튼으로 site 활성화
2. 제출/최소/최대 값 입력
3. `프로그램 시작(시초기록)` 클릭
4. 그래프와 표가 보이는지 확인
5. 시초-제출 편차 10% 이상이면 빨간 강조가 뜨는지 확인

---

## 4) 매일 켜두기(운영용) - 추천: systemd
테스트가 끝나면 자동실행으로 바꾸는 걸 추천합니다.

### 4-1. 서비스 파일 만들기
```bash
sudo nano /etc/systemd/system/bloom.service
```

아래 내용 붙여넣기(경로/사용자명은 본인 환경에 맞게 수정):

```ini
[Unit]
Description=Bloom FastAPI
After=network.target docker.service

[Service]
WorkingDirectory=/home/<USER>/Bloom
Environment="PATH=/home/<USER>/Bloom/.venv/bin"
ExecStart=/home/<USER>/Bloom/.venv/bin/uvicorn bloom.main:app --host 0.0.0.0 --port 8000
Restart=always
User=<USER>

[Install]
WantedBy=multi-user.target
```

### 4-2. 적용
```bash
sudo systemctl daemon-reload
sudo systemctl enable bloom
sudo systemctl start bloom
sudo systemctl status bloom
```

로그 보기:
```bash
journalctl -u bloom -f
```

---

## 5) 서버 업데이트(코드 바뀌었을 때)
서버 PC에서:

```bash
cd ~/Bloom
git pull
source .venv/bin/activate
pip install -e .
sudo systemctl restart bloom
sudo systemctl status bloom
```

---

## 6) 제일 자주 막히는 문제 6개

1. **`No module named uvicorn`**
   - `source .venv/bin/activate`
   - `pip install -e .`

2. **사용자 PC에서 접속 안 됨**
   - 서버에서 앱 실행 중인지 확인
   - 서버 방화벽에서 8000 포트 허용 확인

3. **DB 연결 실패**
   - `docker compose ps`에서 `db` 상태 확인

4. **docker 권한 에러**
   - `sudo usermod -aG docker $USER` 후 재로그인

5. **VPN 끊김**
   - Webview 수집 중단될 수 있음
   - VPN 자동재연결/알람 필요

6. **서버 재부팅 후 앱 미기동**
   - `systemd` 설정했는지 확인
   - `sudo systemctl status bloom`

---

## 7) 업데이트 주기(권장)
- 기본: 60초
- 급전지시 시간대: 10~30초
- 비상/짧은 시운전: 5~10초(한시적)

`CRAWL_INTERVAL_SECONDS`로 조절합니다.

---

## 8) Windows 서버를 쓰는 경우 메모
- PowerShell 기준으로 진행
- Python, Git, Docker Desktop 먼저 설치
- 가상환경 활성화 명령이 다릅니다:
  - `python -m venv .venv`
  - `.venv\Scripts\activate`
- 나머지 순서는 동일합니다(클론 → 의존성 → DB → uvicorn 실행)

### Windows PowerShell 원샷 재시작 + 버전 확인 스크립트
아래 스크립트는 `8000` 포트 점유 프로세스를 정리하고, 현재 폴더의 코드로 서버를 다시 띄운 뒤,
`/dashboard`가 신버전(`Summary (/dashboard)`)인지 구버전인지 확인합니다.

> 주의: PowerShell의 `$PID`는 예약 변수입니다. 사용자 변수명은 반드시 `$listenerPid`처럼 다른 이름을 사용하세요.

```powershell
$ErrorActionPreference = "Stop"

$ProjectPath = "C:\Users\jh240902\bloom"
$Port = 8000
$HostUrl = "http://127.0.0.1:$Port"

Write-Host "== 1) Stop old listener on port $Port if exists ==" -ForegroundColor Cyan
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $listenerPid = $listener.OwningProcess
    Write-Host "Found listener PID=$listenerPid, stopping..." -ForegroundColor Yellow
    Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
} else {
    Write-Host "No listener on port $Port" -ForegroundColor Green
}

Write-Host "== 2) Move to project and activate venv ==" -ForegroundColor Cyan
Set-Location $ProjectPath
if (!(Test-Path ".\.venv\Scripts\Activate.ps1")) {
    throw "venv not found: $ProjectPath\.venv\Scripts\Activate.ps1"
}
. .\.venv\Scripts\Activate.ps1

Write-Host "== 3) Start uvicorn in background ==" -ForegroundColor Cyan
$job = Start-Process -FilePath "python" `
    -ArgumentList "-m uvicorn --app-dir src bloom.main:app --host 0.0.0.0 --port $Port" `
    -WorkingDirectory $ProjectPath `
    -PassThru

Start-Sleep -Seconds 2

Write-Host "== 4) Verify health/dashboard ==" -ForegroundColor Cyan
$health = Invoke-WebRequest "$HostUrl/health" -UseBasicParsing
if ($health.StatusCode -ne 200) { throw "health check failed: $($health.StatusCode)" }

$healthJson = $health.Content | ConvertFrom-Json
if (-not ($healthJson.PSObject.Properties.Name -contains "mainModulePath")) {
    Write-Host "⚠️ 현재 /health 응답이 구버전 형식(status/env만)입니다. 다른 폴더/이전 프로세스가 실행 중일 가능성이 큽니다." -ForegroundColor Yellow
}

$html = (Invoke-WebRequest "$HostUrl/dashboard" -UseBasicParsing).Content
$hasNew = $html -like "*Summary (/dashboard)*"
$hasOld = $html -like "*급전지시 대시보드 (준중앙/비중앙 분리 로직)*"

Write-Host "Health: $($health.StatusCode)" -ForegroundColor Green
Write-Host "New UI marker found: $hasNew"
Write-Host "Old UI marker found: $hasOld"

if ($hasNew -and -not $hasOld) {
    Write-Host "✅ NEW dashboard is serving." -ForegroundColor Green
} elseif ($hasOld) {
    Write-Host "⚠️ OLD dashboard content detected. Check running path/process." -ForegroundColor Yellow
} else {
    Write-Host "⚠️ Neither marker matched. Inspect raw HTML manually." -ForegroundColor Yellow
}

Write-Host "Server PID: $($job.Id)"
Write-Host "Opening browser..."
Start-Process "$HostUrl/dashboard"

Write-Host "`nDone. If needed, stop server with: Stop-Process -Id $($job.Id) -Force" -ForegroundColor Cyan
```

### `{"status":"ok","env":"dev"}` 만 보일 때(구버전 프로세스 판별)
아래 명령으로 **실제로 8000 포트를 잡고 있는 프로세스의 실행 경로**를 확인하세요.

```powershell
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  $listenerPid = $listener.OwningProcess
  Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid" | Select-Object ProcessId, Name, ExecutablePath, CommandLine
} else {
  Write-Host "8000 포트 리스너가 없습니다."
}
```

`ExecutablePath` / `CommandLine`이 기대한 경로(`C:\Users\jh240902\bloom`)가 아니면,
해당 프로세스를 종료 후 프로젝트 폴더에서 다시 `python -m uvicorn --app-dir src bloom.main:app --host 0.0.0.0 --port 8000`으로 실행하세요.

### 그래도 구버전이면: 강제 정렬(Reset) 5단계
아래 순서를 **그대로** 실행하면, 현재 폴더 코드만 사용하도록 정리됩니다.

```powershell
cd C:\Users\jh240902\bloom

# 1) 8000 포트 점유 프로세스 종료
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) { Stop-Process -Id $listener.OwningProcess -Force }

# 2) venv 활성화
.\.venv\Scripts\Activate.ps1

# 3) 기존 bloom 설치본 제거 후 현재 폴더 editable 재설치
python -m pip uninstall -y bloom
python -m pip install -e .

# 4) 실제 import 경로 확인 (반드시 C:\Users\jh240902\bloom\src\bloom\__init__.py 여야 함)
python -c "import bloom; print(bloom.__file__)"

# 5) 서버 실행 (src 강제)
python -m uvicorn --app-dir src bloom.main:app --host 0.0.0.0 --port 8000
```

위 4번 경로가 다르면, 현재 PowerShell이 다른 폴더를 참조 중인 상태입니다.
