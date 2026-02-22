from dataclasses import dataclass


@dataclass
class DispatchEvent:
    plant_name: str
    occurred_at: str
    dispatch_type: str
    generation_mw: float


class WebviewClient:
    """Webview 페이지 접근/파싱을 담당하는 최소 골격.

    TODO:
    - 로그인 로직 (VPN 환경 전제)
    - [급전지시] 이벤트 DOM 셀렉터 확정
    - 이벤트 중복 방지 키 생성
    """

    def fetch_latest_dispatch_events(self) -> list[DispatchEvent]:
        # 향후 Playwright 구현으로 교체
        return []
