# 06. API 명세서

## 1. 공통 응답 포맷
```json
// 성공
{
  "success": true,
  "data": { ... }
}

// 실패
{
  "success": false,
  "error": "오류 메시지 내용"
}
```

## 2. 대시보드
- `GET /api/dashboard/summary`: 요약 수치 반환
- `GET /api/dashboard/monthly`: 월별 차트용 데이터
- `GET /api/dashboard/people-share`: 인물 비중 데이터
- `GET /api/dashboard/cumulative`: 누적 순자산 데이터

## 3. 인물
- `GET /api/people/`: 인물 목록
- `POST /api/people/merge`: 합치기 (body: `source_ids`, `target_id`)
- `POST /api/people/<id>/split`: 분리 (body: `alias_id`)

## 4. 주식
- `GET /api/stocks/`: 종목별 포트폴리오 상태
- `GET /api/stocks/<id>`: 종목 상세 및 매매 내역

## 5. 업로드
- `POST /api/upload/`: 파일 전송
- `POST /api/upload/preview`: 파일 파싱 및 컬럼 감지 정보 리턴
- `POST /api/upload/import`: 매핑 정보 제출 후 최종 저장 수행
