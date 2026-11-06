# Microsoft Foundry 고객 Hands-on Workshop

**[고객용 실습자 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/)** · **[SE 운영자 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html)**

약 **50명의 고객이 5시간 동안** Microsoft Foundry를 직접 실습하는 워크샵을 위한 가이드입니다. 운영자가 **Internal Guest 계정, 고객별 Azure 리소스 그룹(RG), 필요한 RBAC 역할·구독 사전 설정까지** 준비해 제공합니다. **Foundry·프로젝트·모델·관측성 등 필요한 리소스는 참가자가 본인 RG 안에 직접 생성**합니다.

| 가이드 | 대상·내용 |
|---|---|
| [운영자 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html) | SE팀: 계정·RG·RBAC·RP·쿼터 준비, 리허설·격리 검증, 인계 템플릿, 권한 지원·장애 대응·승인된 종료 |
| [실습자 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/) | 고객: 공통 계정 유형·필수 RBAC·기능별 추가 요건·문제 대응 + 배정 RG 안에서 직접 생성하는 실제 포털 실습 |

| 담당 | 작업 |
|---|---|
| 운영자 · 사전 준비 | 계정·RG 생성, 역할 할당, 필수 리소스 공급자 등록, MFA·지역·모델 쿼터·접근 격리 점검 |
| 참가자 · 실습 | Foundry 리소스·프로젝트 생성, 모델 배포, 에이전트 생성·실행, Application Insights 연결, Monitor·Traces 확인 |
| 운영자 · 종료 후 | 로그 보존과 완료 기록 확인, 승인된 정책에 따른 권한 회수·계정 차단·리소스 정리 |

실습자 가이드에는 **63장 실제 화면, 3분 요약 영상, 51분 전체 영상**이 포함되며 두 가이드 모두 **라이트/다크 테마**를 지원합니다. 다른 고객 실습을 만들 때는 [계정·권한 공통 기준](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#responsibilities)과 [문제 대응표](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#troubleshooting)를 계속 참조하고, 실습 본문·모델·생성 자원만 별도로 구성하세요.

모델 배포 단계에는 [경량 모델 그룹 배정·TPM 입력 안내](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#lightweight-models)를 포함합니다. SE는 [모델별 쿼터·50명 분산 예시](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#model-groups)를 참고해 실제 잔여량을 확인하고, 참가자는 배정된 모델 **하나만** 직접 배포합니다. 기존 화면·영상은 GPT-5 mini 검증 예시로 유지합니다.

> 현재 자료는 **Internal Guest 1명의 E2E 검증**을 바탕으로 합니다. 50명 환경이 이미 준비되었거나 동시 부하 검증이 완료되었다는 의미는 아닙니다. 실제 워크샵 전에는 쿼터·동시 부하·비용·MFA 정책·구독 오퍼의 고객 교육 사용 허용 여부를 별도로 확인해야 합니다.

`main`에 푸시하면 GitHub Actions가 HTML과 영상 자산을 빌드하고 GitHub Pages에 자동 배포합니다.
