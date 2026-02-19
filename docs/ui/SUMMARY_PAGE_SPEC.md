# SUMMARY_PAGE_SPEC

## PR0 범위
- 이 문서는 Summary 페이지 구현 기준을 정의한다.
- PR0는 문서 추가만 수행하며 동작 변경은 하지 않는다.

## 렌더링 컨텍스트
- FastAPI `GET /dashboard`에서 `src/bloom/ui_dashboard.html`을 읽어 `HTMLResponse`로 반환.
- 프론트는 단일 HTML + inline JS/CSS 구조.
- 데이터는 `/api/*` fetch로 렌더링.
- 차트 라이브러리는 사용하지 않고 `<canvas>` 커스텀 렌더러를 사용.

## PR1 요구사항
- `/ui-kit` 또는 `/dashboard?mock=1` 미리보기 페이지 제공.
- `docs/ui/fixtures/summary.sample.json` fixture 기반으로 백엔드/DB 없이 항상 렌더링.
- 상태 토글 4개 제공:
  - `loading`
  - `empty`
  - `normal`
  - `high-capacity-active` (`39600` active 시나리오)
- Summary 차트/테이블/노트 UI 검증 가능해야 함.

## PR2 요구사항 (차트 + 필터)
### 차트
- X축: `09:00~17:00` 고정
- X major: 1시간 라벨
- X minor: 10분 그리드
- Y min: `0`
- Y max: `active 최대 capacity`를 만단위 올림
- Tooltip (2줄)
  1) `HH:mm`
  2) `{siteId} · {kw} kW ({tmoPct}%)`
     - `tmoPct` 소수점 1자리
     - `capacity=0`이면 `%` 생략

### 필터
- 준중앙/비중앙 전체 체크 + 사이트 개별 체크 동시 지원
- 합집합 필터
- tri-state(checked/unchecked/indeterminate) 유지

## PR3 요구사항 (테이블 인라인 편집)
- mock 기반으로 먼저 구현
- Enter autosave UX
- 저장 성공 시:
  - row 오른쪽 `Saved ✓` 1~1.5초 표시
  - 해당 셀 하이라이트
- 성공 로그 형식:
  - `[HH:mm:ss] {siteId} {field} : {old} → {new} (user:{optional})`
- `cancel`은 당일 스케줄 취소 의미

## PR4 요구사항 (API)
- `GET /api/meta` (KST 날짜)
- `GET /api/summary`
- `PATCH /api/schedule` (`logLine` 포함)
- `GET /api/export.xlsx`
- 권한:
  - `Operator`만 PATCH/export 가능
  - `Supporter`/`Viewer`는 read-only
