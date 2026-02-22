# API Contract

## Headers (role)
- X-User-Role: operator|viewer
- X-User-Name: string (optional)

## GET /api/meta
Response:
{
  "timezone": "Asia/Seoul",
  "serverDateKst": "YYYY-MM-DD",
  "baselineTime": "10:00",
  "endTime": "17:00"
}

## GET /api/summary?date=YYYY-MM-DD
- If date is omitted, use serverDateKst.
Response (minimal):
{
  "date": "YYYY-MM-DD",
  "timezone": "Asia/Seoul",
  "baselineTime": "10:00",
  "endTime": "17:00",
  "summary": {},
  "timeseriesBySiteId": { "SKK167": [{ "measured_at": "YYYY-MM-DDTHH:mm:ss+09:00", "kw": 12345 }] },
  "series": [{ "measured_at": "YYYY-MM-DDTHH:mm:ss+09:00", "kw": 12345 }],
  "table": [{ "label": "Date", "value": "YYYY-MM-DD" }],
  "yMaxKw": 30000,
  "sites": [
    {
      "siteId": "SKK167",
      "siteName": "Chungju",
      "group": "non|semi",
      "capacityKw": 39600,
      "isActive": false,
      "isCanceled": false,
      "baselineKw1000": 1200,
      "rmccStart": "10:10",
      "start": "10:30",
      "finish": "11:30",
      "minKw": 5000,
      "maxKw": null
    }
  ],
  "userNote": "",
  "systemLogs": []
}

## PATCH /api/schedule
Auth: operator only
Request:
{
  "date": "YYYY-MM-DD",
  "siteId": "SKK167",
  "field": "start|finish|rmccStart|minKw|maxKw|isCanceled|isActive",
  "value": "10:10"  // or number/bool depending on field
}
Response:
{
  "ok": true,
  "updated": { "siteId": "SKK167", "field": "start", "value": "10:10" },
  "logLine": "[09:12:03] SKK167 start : 10:00 → 10:10 (user:홍길동)"
}

## GET /api/export.xlsx?date=YYYY-MM-DD
Auth: operator only
Response: binary xlsx (Content-Disposition attachment)


## GET /api/history?siteId=...&from=YYYY-MM-DD&to=YYYY-MM-DD
- Append-only snapshot history (JSONL source: `data/dispatch_history.jsonl`).
- Returns latest-first items for the site/date range.

## GET /api/history/summary?siteId=...&from=YYYY-MM-DD
- Returns count summary from `from` date:
  - `createdCount`, `updatedCount`, `canceledCount`
