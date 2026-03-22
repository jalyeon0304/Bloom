# 급전지시 대시보드 로직 명세서 (최신)

## 1) 그룹 규칙
- **준중앙 대상 현장(고정 4개)**: `SKK046`, `SKK056`, `SKK144`, `SKK167`
- **비중앙 대상 현장**: 위 4개를 제외한 현장

## 2) 초기 입력값
### 준중앙
- site ID
- 고객 제출 출력값(kW)
- 제출 최소 출력값(min kW)
- 제출 최대 출력값(max kW)
- **(토글)** target time 사용 여부
  - ON이면 `min_target_minutes`, `max_target_minutes`를 각각 입력
  - OFF이면 시간 조건 없이 ±5% 판정만 수행

### 비중앙
- site ID
- 고객 제출 출력값(kW)
- 목표 최소출력 `target_pct` (예: 40/60/0(off))
- 제한 시간 `deadline_minutes`

## 3) 시초(시작출력) 처리
- 프로그램 시작 버튼 클릭 시 활성화된 각 site의 시초값(open output)을 기록
- 시초값은 제출값 대비 편차 계산과 경보에 사용

## 4) 판정 로직
### 준중앙 판정
- 기본 범위 조건: 현재 출력이 아래 범위 중 하나에 들어야 함
  - `min_power_kw ± 5%`
  - `max_power_kw ± 5%`
- target time OFF:
  - 위 범위 조건 기준으로 즉시 성공/실패 판정
- target time ON:
  - `min` 범위 도달 시각이 `min_target_minutes` 이내
  - `max` 범위 도달 시각이 `max_target_minutes` 이내
  - 두 조건 모두 충족 시 성공

### 비중앙 판정
- `target_kw = nameplate_kw * target_pct / 100`
- 제한 시간 내에 `target_kw` 도달(이하)이면 성공
- 시간 내 미도달이면 실패

## 5) 공통 경보 규칙
- 조건: `abs(시초출력 / 고객제출출력 * 100 - 100) >= 10`
- 동작: 해당 site 행 빨간 하이라이트 + 편차 수치 빨간 강조

## 6) 화면 구성 권장
1. 상단: 그룹 탭 + 프로그램 시작(시초기록) 버튼
2. 좌측: 선택 site 실시간 그래프
3. 우측: 장바구니(+추가)
4. 하단 표:
   - site ID, 구분, 판정
   - Nameplate, 제출, 시초, 시초-제출 편차
   - 준중앙(min/max 값, 비율, min/max target time)
   - 비중앙(target%, target kW, 제한시간)
