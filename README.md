# Microsoft Foundry 고객 Hands-on Workshop

**[고객용 실습자 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/)** · **[SE 운영자 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html)**

약 **50명의 고객이 5시간 동안** Microsoft Foundry를 직접 실습하는 워크샵을 위한 가이드입니다. 운영자가 **Internal Guest 계정, 고객별 Azure 리소스 그룹(RG), 필요한 RBAC 역할·구독 사전 설정까지** 준비해 제공합니다. **Foundry·프로젝트·모델·관측성 등 필요한 리소스는 참가자가 본인 RG 안에 직접 생성**합니다.

| 가이드 | 대상·내용 |
|---|---|
| [운영자 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html) | SE팀: **부여할 역할 → A 스크립트 / B 포털 수동 → 공통 필수 점검 → 인계·지원·종료** |
| [실습자 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/) | 고객: **시작 전 배정값 확인 → 본인 RG 안에 직접 생성 → 실행·추적**, 공통 계정·권한·문제 대응 참고 |

| 담당 | 작업 |
|---|---|
| 운영자 · 사전 준비 | 계정·RG 생성, 역할 할당, 필수 리소스 공급자 등록, MFA·지역·모델 쿼터·접근 격리 점검 |
| 참가자 · 실습 | Foundry 리소스·프로젝트 생성, 모델 배포, 에이전트 생성·실행, Application Insights 연결, Monitor·Traces 확인 |
| 운영자 · 종료 후 | 로그 보존과 완료 기록 확인, 승인된 정책에 따른 권한 회수·계정 차단·리소스 정리 |

## SE 준비: A 스크립트 일괄 / B 포털 수동

**50명 반복 운영은 [A · 스크립트 일괄 준비](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#automation)를 권장합니다.** 소규모 수동 준비는 [B · 포털 절차](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#portal)를 따릅니다. 같은 참가자 환경에 A/B를 중복 실행하지 않습니다. HTML은 실행 절차·권한·장애 대응의 참조 문서입니다.

참가자에게 줄 역할은 **본인 RG의 Contributor·Foundry User + 구독의 Cognitive Services Usages Reader**, Entra 관리자 역할은 **없음**입니다. [정확한 역할·Scope](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#participant-roles)와 [SE 자신의 권한](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#operator-roles)을 구분하세요. 두 방법 모두 [인계 전 6가지 필수 점검](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#preflight)을 수행합니다.

아래는 **A의 실행 예시**입니다. Azure Cloud Shell **Bash의 영구 저장소**, Linux/macOS 또는 WSL에서 **Python 3.11+·Azure CLI**를 사용합니다. 추가 Python 패키지는 없습니다.

```bash
git clone https://github.com/junwoojeong100/internal-guest-hands-on-guide.git
cd internal-guest-hands-on-guide
cp config/workshop.example.json config/workshop.local.json
# local.json의 테넌트·구독·고유 workshopId·지역·인원을 확인/수정합니다.
# 아래 따옴표 안을 local.json의 실제 tenantId로 바꿉니다.
az login --tenant "REPLACE_WITH_TENANT_ID"

# 기본값: 읽기 전용 계획. 계정·RG·역할·암호 파일을 생성하지 않습니다.
python3 scripts/provision_workshop.py --config config/workshop.local.json

# 검토한 계획을 실제 적용합니다.
python3 scripts/provision_workshop.py --config config/workshop.local.json --apply

# 생성 결과를 실제 Graph/ARM API에서 다시 읽어 검증합니다. 실패 시 종료 코드 1.
python3 scripts/verify_workshop.py --config config/workshop.local.json
```

50명 설정이면 **Internal Guest 50개 + RG 50개 + 직접 RBAC 150개**가 대상입니다. UPN은 `<workshopId>-001@<테넌트 초기 도메인>`, RG는 `rg-<workshopId>-001`부터입니다. 역할은 **본인 RG의 Contributor·Foundry User + 구독의 Cognitive Services Usages Reader**뿐이며 필요한 RP도 등록합니다. Foundry·프로젝트·모델·로그 자원은 **생성하지 않습니다**.

같은 설정·실행 폴더로 다시 실행하면 누락분만 보완하고 **암호를 재설정하지 않습니다**. 다른 계정/RG를 채택하거나 추가 권한을 자동 삭제하지 않으며 충돌 시 중단합니다. 새 행사에는 새 `workshopId`를 사용하고, 적용 후 인원·지역 등 설정을 바꾸거나 실행 기록을 지우지 마세요. 다른 기기에서 같은 워크샵을 동시에 실행하지 않습니다.

**비공개 결과:** `.workshop-runs/<workshopId>/credentials.private.csv`는 초기 암호가 포함된 민감 파일입니다. `state.private.json`도 암호를 포함하는 복구 기록이며, `verification.private.json`은 검증 결과입니다. 폴더 0700·파일 0600, Git 제외·Pages 배포 제외로 보호합니다. 승인된 비공개 저장소에 백업하고, 전체 CSV를 고객에게 보내지 마세요. 참가자별 초기 암호는 승인된 별도 경로로만 전달합니다. Cloud Shell 임시 저장소에서는 복구 기록이 사라질 수 있습니다.

**A의 검증 범위:** 계정 유형·활성·소유권, RG·지역·태그, 정확한 역할·Scope, 대상 구독의 하위·상위 범위/그룹 경유 추가 Azure 권한, 활성 Entra 역할, RP를 검사합니다. Usages Reader의 실제 정의도 확인합니다. 소유권 마커·이름·태그가 다른 **B의 수동 환경에는 전용 검증 스크립트를 그대로 적용하지 않으며**, 운영 대장·Entra·IAM Check access로 대조합니다. 두 방법 모두 다른 구독·테넌트, PIM eligible·향후 그룹 변경, 로그인·MFA·정책·실제 포털 접근·Foundry E2E·TPM·50명 부하는 별도 점검 대상입니다. **검증 PASS가 개최 승인이나 로그인 성공을 대신하지 않습니다.**

오프라인 자동화 테스트는 실제 Azure에 접속하지 않습니다.

```bash
python3 -m unittest discover -s tests -v
```

실습자 가이드에는 **63장 실제 화면, 3분 요약 영상, 51분 전체 영상**이 포함되며 두 가이드 모두 **라이트/다크 테마**를 지원합니다. 다른 고객 실습을 만들 때는 [계정·권한 공통 기준](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#responsibilities)과 [문제 대응표](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#troubleshooting)를 계속 참조하고, 실습 본문·모델·생성 자원만 별도로 구성하세요.

모델 배포 단계에는 [경량 모델 그룹 배정·TPM 입력 안내](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#lightweight-models)를 포함합니다. SE는 [모델별 쿼터·50명 분산 예시](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#model-groups)를 참고해 실제 잔여량을 확인하고, 참가자는 배정된 모델 **하나만** 직접 배포합니다. 기존 화면·영상은 GPT-5 mini 검증 예시로 유지합니다.

> 현재 자료는 **Internal Guest 1명의 E2E 검증**을 바탕으로 합니다. 50명 환경이 이미 준비되었거나 동시 부하 검증이 완료되었다는 의미는 아닙니다. 실제 워크샵 전에는 쿼터·동시 부하·비용·MFA 정책·구독 오퍼의 고객 교육 사용 허용 여부를 별도로 확인해야 합니다.

`main`에 푸시하면 GitHub Actions가 오프라인 자동화 테스트를 통과한 뒤 HTML·영상·공개 스크립트·예제 설정만 빌드하여 GitHub Pages에 자동 배포합니다. CI는 Azure 계정·RG·역할을 생성하지 않습니다.
