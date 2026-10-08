# 담백한 한국어

딱딱하고 빙빙 돌리는 한국어 문장을 다듬는 스킬입니다. 글의 뜻과 말투를 살리면서 읽기 편하게 고칩니다.

**업무 메일**

> 수정 전: 초안 작성이 완료된 상태이며, 검토 의견 반영은 아직 진행되지 않았습니다. 확인 후 의견을 전달해 주시면 반영 작업을 진행하겠습니다.
>
> 수정 후: 초안을 써뒀습니다. 읽어보시고 의견을 주시면 반영하겠습니다.

**기술 안내**

> 수정 전: 연결이 끊긴 경우에도 처리 중인 작업은 취소되지 않습니다. 작업 완료 여부에 대한 확인은 재연결 이후에 진행할 수 있습니다.
>
> 수정 후: 연결이 끊겨도 작업은 계속됩니다. 다시 연결한 뒤 완료 여부를 확인하세요.

## 설치

```sh
git clone https://github.com/H13m0n/plain-korean-skill.git
```

`skills/plain-korean/` 폴더 전체를 사용하는 도구의 스킬 디렉터리에 복사하세요. 기존 설치본이 있으면 먼저 보관하고 교체할 파일을 비교하세요.

| 도구 | 복사할 위치 |
|---|---|
| Codex | `~/.codex/skills/plain-korean/` |
| Claude Code | `~/.claude/skills/plain-korean/` |
| 다른 에이전트 | 해당 도구의 스킬 디렉터리 |

`~`는 홈 디렉터리입니다. 설치 후에는 사용하는 도구의 안내에 따라 세션을 갱신하세요.

## 사용

Codex에서는 `$plain-korean`, Claude Code에서는 `/plain-korean`으로 호출합니다. 도구가 작업에 맞춰 스킬을 자동 선택할 수도 있습니다.

```text
$plain-korean 이 글을 자연스럽게 다듬어줘.
기술 용어와 실제 조건은 유지해줘.
[고칠 글]
```

수정한 글을 먼저 보여줍니다. 원하는 말투나 직접 고친 문장을 함께 주면 그에 맞춰 다듬습니다.

## 사용하면서 기여하기

자동 기여를 켜두면 에이전트가 새로 배울 만한 수정 사례를 **가상 예문으로 바꿔** 이 저장소에 제안합니다. 새로 쓴 예문과 설명을 검토하고, 기존 이슈와 겹치는지 확인한 뒤 게시합니다.

자동 기여는 기본적으로 꺼져 있습니다. 사용하려면 Python 3.10 이상과 GitHub CLI를 준비하고, GitHub CLI에 본인 계정으로 로그인하세요. [공개되는 정보](PRIVACY.md)와 [기여 방법](CONTRIBUTING.md)을 읽은 뒤 직접 켜거나 에이전트에게 켜달라고 요청합니다. 스킬 폴더에서 다음 명령을 실행합니다.

```sh
python scripts/contribute.py enable --accept-public-synthetic-issues
python scripts/contribute.py status
```

켜면 가상 예문과 설명이 본인 GitHub 계정으로 공개됩니다. 계정과 게시 시각도 이슈에 남습니다. 이후 새 사례는 이 동의에 따라 자동으로 제출하며, 아래 명령으로 언제든 끌 수 있습니다.

```sh
python scripts/contribute.py disable
```

끄면 이후 게시를 중단합니다. 이미 공개된 이슈는 GitHub에 남습니다. 직접 기여하려면 [이슈 양식](https://github.com/H13m0n/plain-korean-skill/issues/new/choose)이나 PR을 이용하세요.
