# Codespaces · Copilot CLI · MCP 실습 가이드

GitHub Codespaces에서 **GitHub Copilot CLI**를 설치하고, Codespace를 만든 계정과 **다른 계정**으로 로그인한 뒤 **Microsoft Learn · Azure · Playwright(headless) MCP**를 연결하는 **선택 심화 실습 가이드**입니다. [GitHub 실습자 가이드](../github-copilot.html)의 Copilot CLI 시작 절과 도움말에서 링크하며, 가이드 4종과 별개라 가이드 전환 메뉴에는 없습니다.
Codespace 생성(계정 A) → CLI 설치 → Copilot 로그인(계정 B) → MCP 3종 등록 → 동작 확인 → 정리까지 한 페이지(단일 HTML)에 담았고, **서로 다른 두 계정(A ≠ B)**으로 모든 단계를 직접 실행해 검증했습니다.

## 가이드 열기

**▶ 웹에서 보기: <https://junwoojeong100.github.io/internal-guest-hands-on-guide/github-copilot-cli-codespaces/>**

오프라인으로 보려면 [`index.html`](./index.html)을 내려받아 브라우저에서 엽니다.

- 스크린샷·스타일·스크립트가 모두 들어 있는 **단일 파일**이라 외부 리소스 없이(오프라인에서도) 열립니다. 상단의 ‘GitHub 실습자 가이드’ 링크만 사이트 안에서 동작합니다.
- 라이트/다크 테마는 OS 설정을 따르고, 우측 상단 버튼으로 바꿀 수 있습니다. 선택은 다른 가이드와 같은 브라우저 저장값(`internal-guest-guide-theme`)을 공유합니다.
- 리포의 HTML 파일은 GitHub 웹에서 소스 코드로 보입니다. 렌더링된 화면은 위 주소를 사용하세요.
- 본문의 `account-a`·`account-b`는 실제 GitHub 사용자명을 가린 표기이며, 스크린샷의 사용자명과 Codespace 이름도 이미지에서 같은 방식으로 가렸습니다([변경 내용](../assets/onboarding/ATTRIBUTION.txt)). 계정 A는 Codespace를 만든 계정, 계정 B는 Copilot CLI에 로그인하는 계정이며 서로 다른 계정입니다. 두 계정이 같은 경우는 검증하지 않았습니다.

## 저장소 구성

```
github-copilot-cli-codespaces/
├── index.html                  # 최종 산출물(빌드 결과, 단일 파일) — 게시되는 파일
├── src/
│   └── index.src.html          # 소스 템플릿 — 수정은 여기서
├── assets/                     # 인라인되는 스크린샷 (게시하지 않음)
│   ├── shot-codespaces-home.jpg
│   ├── shot-trust.jpg
│   └── shot-terminal.jpg
├── build.py                    # 소스 + 이미지 → index.html
└── README.md
```

## 수정과 빌드

```bash
# 1) github-copilot-cli-codespaces/src/index.src.html 을 수정
# 2) 저장소 루트에서 빌드하고 미리보기 (표준 라이브러리만 사용)
python3 github-copilot-cli-codespaces/build.py
open github-copilot-cli-codespaces/index.html
# 3) 소스와 산출물 HTML을 함께 커밋하고 푸시 → 자동으로 배포됩니다
```

- `index.html`은 **빌드 산출물**입니다. 직접 고치지 말고 항상 `src/`를 고친 뒤 빌드하세요. 둘이 어긋나면 다음 빌드에서 수정이 사라지고, 저장소 테스트(`python3 -m unittest discover -s tests -v`)가 실패합니다.
- 소스의 `{{IMG:이름}}`은 `assets/이름.(jpg|png|webp)`를 `data:` URI로 인라인합니다.
- 스크린샷 위 강조 박스(`.hl`)는 이미지 대비 % 좌표(`left/top/width/height`)입니다. 스크린샷을 바꾸면 좌표도 다시 맞추세요.
- 색상은 모두 `--cp-*` CSS 변수로 지정되어 있습니다. 색을 직접 쓰지 말고 변수를 사용하세요.
- 스크린샷을 바꿀 때는 사용자명·토큰·Codespace 이름 같은 식별자를 이미지 픽셀에서 가리고, [ATTRIBUTION](../assets/onboarding/ATTRIBUTION.txt)에 변경 내용을 적으세요.

## 배포 (GitHub Pages)

이 폴더에는 별도 워크플로가 없습니다. `main`에 푸시하면 저장소 루트의 [`.github/workflows/pages.yml`](../.github/workflows/pages.yml)이 테스트를 통과한 뒤 `index.html`을 **같은 경로**(`github-copilot-cli-codespaces/index.html`)로 사이트에 게시합니다.

- 저장소 경로와 게시 경로가 같아야 GitHub 실습자 가이드의 상대 링크가 테스트와 실제 사이트에서 모두 맞습니다. `src/`·`assets/`·`build.py`는 게시하지 않습니다.
- 빌드는 CI에서 하지 않습니다. 커밋된 `index.html`이 그대로 게시되며, 소스의 최신 빌드가 아니면 테스트가 실패합니다.
- Pages 응답은 `cache-control: max-age=600`이라 새 버전이 보이기까지 브라우저 캐시로 최대 10분 걸릴 수 있습니다. 강력 새로고침(`Cmd/Ctrl+Shift+R`)하면 바로 보입니다.
- 설정: Settings → Pages → Build and deployment → Source = **GitHub Actions**. 수동 실행은 Actions 탭 → Build and deploy GitHub Pages → Run workflow.

## 유지보수 체크리스트

시간이 지나면 달라질 수 있어 주기적으로 다시 확인해야 하는 항목입니다. 확인하면 본문 하단 “검증 기록” 표와 날짜도 함께 갱신하세요.

| 항목 | 가이드의 현재 내용 | 다시 확인하는 방법 |
| --- | --- | --- |
| 계정 구성 (A ≠ B) | Codespace 소유 계정(A)과 Copilot 로그인 계정(B)이 다른 경우. 첫 실행은 주입된 `GITHUB_TOKEN`으로 A에 자동 인증됨 | 새 Codespace에서 첫 `copilot` 실행 후 `/user list`의 `(active)`가 A인지 확인 |
| Copilot CLI 버전·설치 | `npm install -g @github/copilot`, 1.0.105 | 새 Codespace에서 설치 후 `copilot --version`, `copilot update` |
| 대안 설치 (Node.js·npm 없음) | apt `nodejs npm` = Node 18.19.1 · npm 9.2.0(Ubuntu 24.04)이라 일반 사용자의 `npm install -g`는 `EACCES`. 설치 스크립트 `curl -fsSL https://gh.io/copilot-install \| bash`는 `~/.local/bin`에 설치. Azure MCP는 Node 22 이상, nvm v0.40.8 | Node.js·npm·`copilot`이 없는 Ubuntu 컨테이너(또는 Codespace)에서 같은 명령을 다시 실행. `npm view @azure/mcp engines`, `gh api repos/nvm-sh/nvm/releases/latest --jq .tag_name` |
| 로그인 흐름 | device code 로그인, 코드를 승인한 브라우저의 계정으로 등록됨, 키체인 없을 때 평문 저장 질문 | 두 번째 계정으로 `/login` 후 `/user list`의 `(active)` 확인 |
| `/logout` 동작 | 1.0.105에서는 토큰이 지워지지 않음(문서와 다름). GitHub 실습자 가이드는 1.0.108 기준으로 공용 PC에서 `/logout`을 안내함 | 1.0.108 이상에서 `/logout` 후 `/user list`와 `~/.copilot/config.json` 확인. 결과가 다르면 두 가이드를 함께 고침 |
| Microsoft Learn MCP | `https://learn.microsoft.com/api/mcp`, 도구 3개 | `copilot mcp add` 후 `/mcp`에서 도구 수와 실제 호출 |
| Azure MCP | `@azure/mcp@latest` 4.0.0-beta.4, 도구 73개, `--read-only` · `--namespace` · `--tool` 옵션 | `npx -y @azure/mcp@latest server start --help` |
| Azure MCP 비대화형 | `copilot -p`는 모델 호출(sampling) 승인 대기로 멈춤 | 같은 프롬프트를 `-p`와 대화형에서 각각 실행 |
| Playwright MCP | `@playwright/mcp@latest` 0.0.83, `--headless`, 도구 25개, Chrome 설치 필요 | `npx -y playwright install chrome` 후 `copilot -s -p`로 페이지 열기 |
| Codespaces UI | Blank 템플릿, `Trust Folder & Continue`, `⋯ → Delete` 확인 창 | 화면과 스크린샷(`assets/`) 대조 |
| Codespaces 기본값 | 유휴 30분 중지, 최대 12시간, 30일 보존 | [공식 문서](https://docs.github.com/en/codespaces) 확인 |
| Pages 설정 | Source = GitHub Actions, HTTPS 강제 (사이트 전체 설정) | `gh api repos/junwoojeong100/internal-guest-hands-on-guide/pages` |

## 검증 환경 (2026.10.31 KST)

| 구성 요소 | 버전 |
| --- | --- |
| Codespace 이미지 | Ubuntu 24.04.5 LTS (x86_64, 2 vCPU, 7.8 GiB) |
| Node.js / npm | v24.22.2 / 11.19.1 |
| GitHub Copilot CLI | 1.0.105 |
| `@azure/mcp` (latest) | 4.0.0-beta.4 |
| `@playwright/mcp` (latest) | 0.0.83 |
| Google Chrome | 156.0.8078.79 |

## 참고 문서

- [Getting started with GitHub Copilot CLI](https://docs.github.com/en/copilot/get-started/cli-quickstart)
- [Authenticating GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli)
- [Adding MCP servers for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
- [Get started with the Microsoft Learn MCP Server](https://learn.microsoft.com/en-us/training/support/mcp-get-started)
- [Integrate Azure MCP Server with GitHub Copilot CLI](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/how-to/github-copilot-cli)
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
