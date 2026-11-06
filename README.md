# Microsoft Foundry 고객 Hands-on Workshop

**[HTML 실습 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/)**

약 **50명의 고객이 5시간 동안** Microsoft Foundry를 직접 실습하는 워크샵을 위한 가이드입니다. 운영자가 **Internal Guest 계정, 고객별 Azure 리소스 그룹(RG), 필요한 RBAC 역할**을 미리 준비해 제공하고, 참가자는 배정된 환경에서 Azure Portal과 Foundry Portal로 실습합니다.

| 담당 | 작업 |
|---|---|
| 운영자 · 사전 준비 | 계정·RG 생성, 역할 할당, 필수 리소스 공급자 등록, MFA·지역·모델 쿼터·접근 격리 점검 |
| 참가자 · 실습 | Foundry 리소스·프로젝트 생성, 모델 배포, 에이전트 생성·실행, Application Insights 연결, Monitor·Traces 확인 |
| 운영자 · 종료 후 | 로그 보존과 완료 기록 확인, 승인된 정책에 따른 권한 회수·계정 차단·리소스 정리 |

가이드에는 **63장 실제 화면, 3분 요약 영상, 51분 전체 영상, 라이트/다크 테마**가 포함되어 있습니다. [운영자·실습자 권한 및 작업 구분](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#responsibilities)도 확인하세요.

> 현재 자료는 **Internal Guest 1명의 E2E 검증**을 바탕으로 합니다. 50명 환경이 이미 준비되었거나 동시 부하 검증이 완료되었다는 의미는 아닙니다. 실제 워크샵 전에는 쿼터·동시 부하·비용·MFA 정책·구독 오퍼의 고객 교육 사용 허용 여부를 별도로 확인해야 합니다.

`main`에 푸시하면 GitHub Actions가 HTML과 영상 자산을 빌드하고 GitHub Pages에 자동 배포합니다.
