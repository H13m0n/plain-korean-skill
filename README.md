# 담백한 한국어

독자가 알고 싶은 내용을 바로 쓰는 한국어 글쓰기 스킬입니다. 문장에 붙은 불필요한 단서·대조·조사 중계·추상어를 줄이고, 동작·조건·결과를 직접 설명합니다. 기술 용어와 실제 제한, 가설, 수치, 인과관계는 보존합니다.

> 수정 전: 메모를 저장하면 다음에 다시 열 수 있다. 이는 편리한 사용 경험을 위한 중요한 의미를 갖는다.
>
> 수정 후: 메모를 저장하면 다음에 다시 열 수 있다.

“삭제한 자료는 복구할 수 없다”처럼 선택에 필요한 제한은 그대로 남깁니다. 단어를 일괄 금지하거나 AI 작성 여부를 판정하지 않습니다.

## 설치

```sh
git clone https://github.com/H13m0n/plain-korean-skill.git
```

`skills/plain-korean/` 폴더 전체를 사용하는 도구의 스킬 디렉터리에 복사합니다. 기존 설치본이 있으면 먼저 보관하고 교체할 파일을 비교하세요.

| 도구 | 사용자 스킬 디렉터리 |
|---|---|
| Codex | `~/.codex/skills/plain-korean/` |
| Claude Code | `~/.claude/skills/plain-korean/` |
| 다른 에이전트 | 해당 도구가 읽는 스킬 폴더에 `SKILL.md`와 하위 파일을 함께 배치 |

`~`는 사용하는 사람의 홈 디렉터리입니다. 본문 지침과 예시는 특정 운영체제나 서비스에 의존하지 않습니다. 예시 검색과 기여 도우미에는 Python 3.10 이상이 필요하며, GitHub 이슈 제출에는 GitHub CLI와 본인 계정 인증이 추가로 필요합니다. 다른 윤문 스킬과 API 키는 필수가 아닙니다.

Codex에서는 `$plain-korean`, Claude Code에서는 `/plain-korean`으로 호출하거나 도구의 자동 선택을 사용할 수 있습니다. 설치 인식은 도구의 세션 갱신 방식에 따릅니다. 이 저장소는 스킬 폴더를 배포합니다.

## 사용

```text
$plain-korean 이 글에서 불필요한 단서와 대조를 줄여줘.
기술 용어와 실제 조건은 유지해줘.
[고칠 글]
```

완성한 문장을 먼저 돌려줍니다. 글의 목적과 사용자가 제시한 수정 예를 우선하며, 맞춤법만 손보는 요청보다 문장 필요성과 문단 전개를 정리하는 작업에 맞습니다.

## 사용하면서 기여하기

기본값은 외부 전송 없음입니다. 자동 기여를 켜면 에이전트가 재사용할 만한 수정 방향을 **새 가상 예문으로 추상화**하고, 검사와 중복 확인을 거쳐 이 저장소에 이슈를 만듭니다. 원문이나 대화를 수집하는 백그라운드 프로그램은 없습니다. 스킬을 실행하는 에이전트가 기여 절차를 따르는 방식입니다.

먼저 [개인정보 처리 범위](PRIVACY.md)와 [기여 방법](CONTRIBUTING.md)을 읽고 GitHub CLI에 본인 계정으로 로그인합니다. 스킬 폴더에서 사용자가 직접 실행하거나, 아래 동의 내용을 이해한 뒤 에이전트에게 실행을 요청합니다.

```sh
python scripts/contribute.py enable --accept-public-synthetic-issues
python scripts/contribute.py status
```

이 명령은 현재 GitHub 계정으로 새 가상 예문을 공개 이슈에 자동 게시하는 데 동의합니다. GitHub 계정과 게시 시간이 공개됩니다. 설치나 일반 문체 수정 요청만으로 켜지지 않습니다. 사용자가 직접 허용하기 전에는 에이전트도 이 설정을 켜면 안 됩니다.

```sh
python scripts/contribute.py disable
```

끄면 이후 게시를 중단합니다. 이미 공개된 이슈는 GitHub에 남습니다. 자동 기여를 켜지 않고도 [이슈 양식](https://github.com/H13m0n/plain-korean-skill/issues/new/choose)이나 PR로 기여할 수 있습니다.

## 구조

```text
skills/plain-korean/
  SKILL.md                  # 문장 필요성·전개·의미 보존 기준
  agents/openai.yaml        # Codex 표시 정보
  references/patterns.md    # 패턴별 편집 기준과 예외
  references/examples.jsonl # 가상 수정 예와 유지 사례 18개
  references/contributing.md
  scripts/examples.py      # 네트워크 없는 예시 검색
  scripts/contribute.py    # 동의·검사·중복 확인 후 이슈 제출
docs/design.md              # 공개본 구성과 설계 판단
tests/                      # 기여 도우미·패키지 검증
```

개인 기록과 설치 환경을 공개본에서 분리한 과정은 [설계 정리](docs/design.md)에 있습니다. 스킬 폴더가 배포 원본이며 생성된 복제본을 따로 관리하지 않습니다.

## 검증

저장소 루트에서 실행합니다. Python 표준 라이브러리만 사용하고 테스트는 실제 이슈를 만들지 않습니다.

```sh
python scripts/validate_package.py
python -m unittest discover -s tests -v
```

## 참고와 라이선스

[humanizer-kr](https://github.com/hjongc/humanizer-kr)의 스킬·참고 문서 분리와 기여 검증 구조를 참고했습니다. 이 저장소의 지침과 예시는 별도로 작성했습니다. 스킬의 문체 기준은 문장의 필요성과 실제 동작을 설명하는 데 초점을 둡니다.

[MIT License](LICENSE). 기여한 내용은 이 저장소의 MIT 라이선스로 배포됩니다. 외부 글을 옮길 때는 원저작자의 권리와 출처를 확인해야 합니다.
