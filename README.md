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

## SE는 스크립트로 일괄 준비합니다

계정·RG·역할을 포털에서 50번씩 만들지 않습니다. **필요할 때 일괄 생성 → 독립 검증 → 고객 인계**하고, HTML은 권한·설계·장애 대응 참고 문서로 사용합니다.

Azure Cloud Shell **Bash의 영구 저장소**, Linux/macOS 또는 WSL에서 **Python 3.11+·Azure CLI**를 사용합니다. 추가 Python 패키지는 없습니다. SE 실행 계정에는 Entra 사용자 생성, Entra 역할·그룹 조회, Azure RG 생성·역할 할당 권한이 필요합니다. [필요한 SE 권한·전체 실행 안내](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#automation)를 먼저 확인하세요.

```bash
git clone https://github.com/junwoojeong100/internal-guest-hands-on-guide.git
cd internal-guest-hands-on-guide
cp config/workshop.example.json config/workshop.local.json
# local.json의 테넌트·구독·고유 workshopId·지역·인원을 확인/수정합니다.
az login --tenant <tenantId>

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

**검증 범위:** 계정 유형·활성·소유권, RG·지역·태그, 정확한 역할·Scope, 대상 구독의 하위·상위 범위/그룹 경유 추가 Azure 권한, 활성 Entra 역할, RP를 검사합니다. Usages Reader의 실제 정의도 확인해 다른 RG를 읽는 권한이 추가되지 않았는지 점검합니다. 다른 구독·테넌트, PIM eligible·향후 그룹 변경, 로그인·MFA·정책·실제 포털 접근·Foundry E2E·TPM·50명 부하는 별도 리허설 대상입니다. **검증 PASS가 개최 승인이나 로그인 성공을 대신하지 않습니다.**

오프라인 자동화 테스트는 실제 Azure에 접속하지 않습니다.

```bash
python3 -m unittest discover -s tests -v
```

실습자 가이드에는 **63장 실제 화면, 3분 요약 영상, 51분 전체 영상**이 포함되며 두 가이드 모두 **라이트/다크 테마**를 지원합니다. 다른 고객 실습을 만들 때는 [계정·권한 공통 기준](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#responsibilities)과 [문제 대응표](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#troubleshooting)를 계속 참조하고, 실습 본문·모델·생성 자원만 별도로 구성하세요.

모델 배포 단계에는 [경량 모델 그룹 배정·TPM 입력 안내](https://junwoojeong100.github.io/internal-guest-hands-on-guide/#lightweight-models)를 포함합니다. SE는 [모델별 쿼터·50명 분산 예시](https://junwoojeong100.github.io/internal-guest-hands-on-guide/operator.html#model-groups)를 참고해 실제 잔여량을 확인하고, 참가자는 배정된 모델 **하나만** 직접 배포합니다. 기존 화면·영상은 GPT-5 mini 검증 예시로 유지합니다.

> 현재 자료는 **Internal Guest 1명의 E2E 검증**을 바탕으로 합니다. 50명 환경이 이미 준비되었거나 동시 부하 검증이 완료되었다는 의미는 아닙니다. 실제 워크샵 전에는 쿼터·동시 부하·비용·MFA 정책·구독 오퍼의 고객 교육 사용 허용 여부를 별도로 확인해야 합니다.

`main`에 푸시하면 GitHub Actions가 오프라인 자동화 테스트를 통과한 뒤 HTML·영상·공개 스크립트·예제 설정만 빌드하여 GitHub Pages에 자동 배포합니다. CI는 Azure 계정·RG·역할을 생성하지 않습니다.
