# API_CONTRACT

## 공통
- Base URL: `/`
- Content-Type: `application/json` (xlsx export 제외)
- Role 헤더: `X-Role` (`Operator` | `Supporter` | `Viewer`)
  - 미지정 시 `Viewer` 처리

---

## GET /api/meta
KST 기준 메타 정보 조회.

### Response 200
```json
{
  "timezone": "Asia/Seoul",
  "kst_date": "2026-01-01",
  "generated_at": "2026-01-01T09:30:00+09:00"
}
```

---

## GET /api/summary
Summary 페이지용 데이터 조회.

### Query
- `state` (optional): `loading|empty|normal|high-capacity-active`

### Response 200
```json
{
  "summary": {
    "site_id": "SKK167",
    "group_type": "준중앙",
    "nameplate_kw": 39600,
    "submitted_output_kw": 33000,
    "open_output_kw": 32100,
    "current_output_kw": 30550,
    "note": "...",
    "warning": "..."
  },
  "sites": [
    {"site_id":"SKK046","group":"준중앙","active":true,"capacity_kw":19800}
  ],
  "series": [
    {"measured_at":"2026-01-01T09:30:00","kw":30550}
  ],
  "table": [
    {"site_id":"SKK167","field":"target_kw","value":"12000","status":"active"}
  ],
  "logs": [
    "[09:30:00] SKK167 target_kw : 11000 → 12000 (user:operator)"
  ]
}
```

---

## PATCH /api/schedule
스케줄 값 수정(인라인 저장).

### AuthZ
- `Operator`만 허용
- `Supporter`/`Viewer`는 403

### Request
```json
{
  "site_id": "SKK167",
  "field": "target_kw",
  "value": "12000",
  "user": "operator"
}
```

### Response 200
```json
{
  "ok": true,
  "site_id": "SKK167",
  "field": "target_kw",
  "old": "11000",
  "new": "12000",
  "logLine": "[09:30:00] SKK167 target_kw : 11000 → 12000 (user:operator)",
  "saved_at": "2026-01-01T09:30:00+09:00"
}
```

---

## GET /api/export.xlsx
Summary 데이터 엑셀 다운로드.

### AuthZ
- `Operator`만 허용
- `Supporter`/`Viewer`는 403

### Response 200
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- attachment filename: `summary_export.xlsx`
