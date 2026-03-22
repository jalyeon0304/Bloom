# 하이브리드 운영 시 사용자 구동 로직

이 문서는 "기본은 사내 VPN 사용자", "예외는 중앙 승인형 사용자"를 함께 운영할 때의 실제 사용 흐름을 설명합니다.


## 0) 초기 입력(필수)
1. 운영자는 대상 현장의 `site_id` 마스터를 먼저 등록/보유
2. 현장은 `준중앙/비중앙` 그룹으로 사전 구분
3. 사용자는 웹에서 `+ 추가`로 현장을 활성화하며, 현장별로 아래 3개 값을 입력
   - 고객 제출 출력량(`submitted_output_kw`)
   - (준중앙) `min_power_kw`, `max_power_kw` (+ 필요 시 `min/max target time` 토글 입력)
   - (비중앙) `target_pct`, `deadline_minutes`
4. 활성화가 끝나면 `프로그램 시작(시초기록)` 버튼을 눌러 시초(시작발전량) 기록 시작

---

## 1) 공통 시스템 동작 (백엔드)
1. 중앙 서버(사내망/VPN 가능 위치)가 Webview를 주기적으로 크롤링
2. 수집 데이터(이벤트/발전량)를 내부 DB에 저장
3. 사용자 단말은 Webview에 직접 붙지 않고, 중앙 서버 대시보드/API만 조회

---

## 2) 사용자 구동 플로우 A: 사내 VPN 가능 사용자
1. 사용자가 사내 VPN 연결
2. Bloom 대시보드 접속 (`/dashboard`)
3. 필요 시 로그인(사내 계정/SSO)
4. 대시보드에서 그룹 탭(준중앙/비중앙), 현장 리스트, 실시간 그래프 확인
5. CSV/XLSX 다운로드

핵심 포인트:
- 가장 단순한 경로
- 모바일보다 사내 PC 사용자가 많은 조직에 적합

---

## 3) 사용자 구동 플로우 B: VPN 불가/모바일 사용자 (중앙 승인형)
1. 사용자(휴대폰/외부)가 로그인 요청 생성
   - `POST /api/auth/login-request`
2. 운영자(당신)가 승인 대기 목록 확인
   - `GET /api/auth/pending`
3. 운영자가 요청 승인
   - `POST /api/auth/approve/{request_id}`
4. 사용자 단말이 토큰 교환
   - `POST /api/auth/token`
5. 발급된 토큰으로 대시보드/API 조회

핵심 포인트:
- 단말은 VPN 없이도 중앙 서버 데이터 조회 가능
- 승인/만료/차단 정책이 중요

---

## 4) 역할별 책임
- 운영자
  - 승인/거절, 이상 접속 차단, 감사로그 점검
- 일반 사용자
  - 대시보드 조회, 현장 상태 확인, 기록물 다운로드
- 시스템
  - 데이터 수집, 지표 계산(목표 대비/시초 대비), API 제공

---

## 5) 실패 시 처리 로직 (권장)
- 승인요청 만료(예: 3분) -> 재요청 안내
- 토큰 만료(예: 8시간) -> 재로그인/재승인
- 중앙 서버 장애 -> 읽기 전용 캐시 화면 + 장애 공지
- Webview 수집 실패 -> 마지막 정상 수집 시각 표시 + 경고 배지

---

## 6) 현재 코드와 매핑
- 대시보드: `GET /dashboard`
- 마스터 현장 조회: `GET /api/master-sites`
- 현장 활성화(+): `POST /api/sites/activate`
- 프로그램 시작/시초기록: `POST /api/session/start`
- 프로그램 상태: `GET /api/session/status`
- 현장 목록 API: `GET /api/sites`
- 시계열 API: `GET /api/series/{site_id}`
- 승인형 인증 API:
  - `POST /api/auth/login-request`
  - `GET /api/auth/pending`
  - `POST /api/auth/approve/{request_id}`
  - `POST /api/auth/token`

> 주의: 현재 인증 저장소는 인메모리 데모입니다. 운영 적용 시 DB/Redis/JWT/TLS/감사로그가 필요합니다.


## 7) 최신 도메인 규칙 반영
- 준중앙 고정 대상: `SKK046`, `SKK056`, `SKK144`, `SKK167`
- 비중앙: 그 외 site
- 준중앙 성공조건: `min/max` 각 기준의 ±5% 이내
- 비중앙 성공조건: target%(0/40/60 등)로 계산된 target kW를 제한 시간 내 도달
