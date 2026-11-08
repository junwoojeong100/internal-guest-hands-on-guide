# Microsoft Foundry 고객 Hands-on Workshop

**[고객용 실습자 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/)** · **[SE 운영자 가이드 바로 열기 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html)**

**[GitHub 조직 가입 · Copilot 준비 가이드 →](https://junwoojeong100.github.io/internal-guest-hands-on-guide/github-copilot.html)** · A 관리자 초대 / B 사용자 가입 신청 → 초대 수락 → 조직 Copilot 권한 확인 → 브라우저 질문 실행

약 **50명의 고객이 5시간 동안** Microsoft Foundry를 직접 실습하는 워크샵을 위한 가이드입니다. 운영자가 **Internal Guest 계정, 고객별 Azure 리소스 그룹(RG), 필요한 RBAC 역할·구독 사전 설정까지** 준비해 제공합니다. **Foundry·프로젝트·모델·관측성 등 필요한 리소스는 참가자가 본인 RG 안에 직접 생성**합니다.

| 가이드 | 대상·내용 |
|---|---|
| [운영자 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html) | SE팀: **부여할 역할 → A 스크립트 / B 포털 수동 → 공통 필수 점검 → 인계·지원·종료** |
| [실습자 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/) | 고객: **배정값 확인 → 첫 로그인·암호 변경·MFA 등록 → 본인 RG 안에 직접 생성 → 실행·추적**, 공통 계정·권한·문제 대응 참고 |
| [GitHub 조직·Copilot 가이드](https://junwoojeong100.github.io/internal-guest-hands-on-guide/github-copilot.html) | 고객: **A 초대 수락 / B 가입 신청 후 승인·초대 수락 → 조직 Copilot 좌석 확인 → 브라우저 사용**, 관리자 초대·좌석·정책 준비 포함 |

| 담당 | 작업 |
|---|---|
| 운영자 · 사전 준비 | 계정·RG 생성, 역할 할당, 필수 리소스 공급자 등록, MFA·지역·모델 쿼터·접근 격리 점검 |
| 참가자 · 실습 | Foundry 리소스·프로젝트 생성, 모델 배포, 에이전트 생성·실행, Application Insights 연결, Monitor·Traces 확인 |
| 운영자 · 종료 후 | 로그 보존과 완료 기록 확인, 승인된 정책에 따른 권한 회수·계정 차단·리소스 정리 |

**참가자 필수 첫 실습:** 로그인 계정은 **본인 UPN과 별도 경로로 받은 초기 암호**입니다. **첫 암호 변경·MFA 등록은 본인이 완료**하고, 변경한 암호·본인 MFA로 재로그인해 대상 테넌트·구독·배정 RG를 확인합니다. [단계별 첫 로그인 실습 안내](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#first-sign-in)를 먼저 따르세요. 인증 화면은 보안상 녹화에 포함하지 않았습니다.

첫 로그인·MFA는 **실제 화면 → 번호별 입력·버튼 → 다음 상태**의 7단계입니다. 익명 Microsoft 로그인 캡처 1장과 공식 문서 화면 9장을 사용하며 재구성 인증·초대 그림은 제거했습니다. QR 데이터와 개인 식별 정보는 제외하고, GitHub는 실제 계정 메뉴에서 사용자명·조직 멤버십을 확인하도록 안내합니다. [출처·확대/가림·재사용 조건](assets/onboarding/ATTRIBUTION.txt)을 제공하며 기존 63장 녹화·검증 기록은 유지합니다.

## SE 준비: A 스크립트 일괄 / B 포털 수동

**50명 반복 운영은 [A · 스크립트 일괄 준비](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#automation)를 권장합니다.** 소규모 수동 준비는 [B · 포털 절차](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#portal)를 따릅니다. 같은 참가자 환경에 A/B를 중복 실행하지 않습니다. HTML은 실행 절차·권한·장애 대응의 참조 문서입니다.

참가자에게 줄 역할은 **본인 RG의 Contributor·Foundry User + 구독의 Cognitive Services Usages Reader**, Entra 관리자 역할은 **없음**입니다. [정확한 역할·Scope](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#participant-roles)와 [SE 자신의 권한](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#operator-roles)을 구분하세요. 두 방법 모두 [인계 전 6가지 필수 점검](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#preflight)을 수행합니다.

**신규 Internal Guest 생성 운영자:** 대상 테넌트의 활성 **User Administrator가 최소 권한**이며, 기존 **Global Administrator도 가능**합니다. Azure Owner나 외부 초대용 Guest Inviter만으로는 Internal Guest 신규 생성 권한을 대신할 수 없습니다.

**인계 전 운영자 필수 리허설:** 계정 생성·스크립트 검증 PASS와 별개로, **실제 고객이 사용할 교육망과 같은 기기 조건에서 MFA 미등록 테스트 전용 Guest 2개의 최초 로그인·암호 변경·본인 MFA 등록·재로그인**을 확인합니다. 직원용 망·강사 전용 VPN이나 이미 MFA가 등록된 계정으로 대체하지 않습니다. 미확인·차단 상태에서는 인계를 보류합니다. [실제 교육망 인증 리허설 기준](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#network-mfa-rehearsal)을 따르고 테스트 계정은 고객에게 배정하지 않습니다.

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

실습자 가이드에는 **63장 실제 화면, 3분 요약 영상, 51분 전체 영상**이 포함되며 모든 가이드가 **라이트/다크 테마**를 지원합니다. 다른 고객 실습을 만들 때는 [계정·권한 공통 기준](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#responsibilities)과 [문제 대응표](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#troubleshooting)를 계속 참조하고, 실습 본문·모델·생성 자원만 별도로 구성하세요.

**일반 실습은 현재 가장 많은 TPM을 확보한 `gpt-6.1-terra`를 기본 모델로 사용하고 공유 쿼터를 개인별로 배분합니다.** 참가자는 [배정 TPM 입력 안내](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#lightweight-models)에 따라 일반 실습용 모델 **하나만** 직접 배포합니다. SE는 [terra TPM 배분·50명 계산 예시](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#model-groups)를 참고해 실제 잔여량에서 운영 여유를 뺀 뒤 개인별 TPM을 확정합니다. **Optimizer 등 특정 모델을 요구하는 설정은 지정 모델·버전을 유지**하고 해당 모델 풀의 배포 개수·TPM을 별도 배정합니다. 기존 화면·영상은 GPT-5 mini 검증 기록으로 유지하며 terra 검증 자료로 바꾸지 않습니다.

> 현재 자료는 **Internal Guest 1명의 E2E 검증**을 바탕으로 합니다. 50명 환경이 이미 준비되었거나 동시 부하 검증이 완료되었다는 의미는 아닙니다. 실제 워크샵 전에는 쿼터·동시 부하·비용·MFA 정책·구독 오퍼의 고객 교육 사용 허용 여부를 별도로 확인해야 합니다.

`main`에 푸시하면 GitHub Actions가 오프라인 자동화 테스트를 통과한 뒤 HTML·영상·공개 스크립트·예제 설정만 빌드하여 GitHub Pages에 자동 배포합니다. CI는 Azure 계정·RG·역할을 생성하지 않습니다.
