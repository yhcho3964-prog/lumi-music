# LU:MI Music Library — Claude 작업 가이드

`yhcho3964-prog/lumi-music` 저장소의 신곡 등록 자동화 환경입니다. Netlify 배포 URL: https://lumi-music.netlify.app

## 신곡 등록 워크플로우 (사용자가 가장 자주 요청하는 작업)

### 트리거
사용자가 다음 중 하나를 말하면 등록 절차를 시작:
- "등록해줘", "신곡 등록", "이 곡 올려줘", "register"
- 별다른 지시 없이 `drop/` 폴더에 새 MP3 + 가사 파일을 두고 메시지를 보내는 경우

### 입력
- `drop/` 폴더 안에 **MP3 1개 + 텍스트 가사 1개** (.txt 또는 .lrc)
- 파일명은 보통 `원제 (보조제).mp3` 형식 — 보조제가 비어 있으면 적절히 번역해서 제안

### Claude가 해야 할 일 (대화 안에서 수행)

1. **drop/ 폴더 스캔** — MP3와 가사 파일을 찾는다. 여러 개 있으면 사용자에게 어느 쌍인지 확인.
2. **가사 파일 읽기** → 원곡 언어 자동 감지 (한글/일본어/스페인어/영어).
3. **제목 파싱**:
   - `원제 (보조제).mp3` 패턴에서 추출
   - `titleKr` = 원곡 언어의 제목, `titleEn` = 보조 제목 (한국어 곡이면 영문, 외국어 곡이면 한국어)
4. **다음 트랙 번호 결정** — `index.html`의 `TRACKS` 배열에서 `num` 최댓값 + 1.
5. **가사 번역** — Claude가 직접 번역해서 다음 언어를 채운다 (별도 API 호출 없음):
   - 항상 `ko`, `en`, `es` 포함
   - 원곡 언어가 그 외(예: `ja`)면 원곡 언어도 포함
   - 절 구조 유지, 시적 표현 살리기
   - 섹션 라벨은 언어별 관례 사용:
     - ko: `1절`, `2절`, `후렴`, `브리지`, `아웃트로`
     - en: `Verse 1`, `Verse 2`, `Chorus`, `Bridge`, `Outro`
     - es: `Verso 1`, `Verso 2`, `Estribillo`, `Puente`, `Outro`
     - ja: `1番`, `2番`, `サビ`, `ブリッジ`, `アウトロ`
6. **태그 제안** — 가사·제목·분위기를 참고해서 다음 중 골라 제안:
   - `k-indie`, `ballad`, `jazz`, `neo-classical`, `j-indie`, `world`
   - 사용자 확인을 받고 진행
7. **registration.json 작성** — `drop/registration.json` 으로 저장 (스키마는 register_song.py 상단 docstring 참고).
8. **register_song.py 실행** — `python register_song.py drop/registration.json`. 스크립트가 ffprobe·gh release upload·index.html 갱신·git push·파일 정리까지 모두 수행.
9. **결과 보고** — 트랙 번호, GitHub Release URL, Netlify 배포 안내(30초).

### 사용자 확인이 필요한 단계
- 제목 파싱 결과 (titleKr / titleEn)
- 원곡 언어 (감지 결과)
- 태그 (장르) 선택
- 가사 번역 미리보기는 생략 가능하나 길거나 모호한 부분은 짧게 확인 요청

태그·언어가 명백할 땐 짧은 한 줄 요약으로 컨펌만 받고 진행.

### 안전 장치
- 같은 트랙 번호로 이미 등록된 게 있는지 검사
- `gh release upload` 가 `--clobber` 로 덮어쓰니, 같은 파일명이 있으면 알려주고 사용자 확인
- git push 실패 시 (예: 충돌) 상태를 정확히 보고 — `--force`는 절대 사용 금지

## 저장소 구조

```
lumi-music/
├── index.html               # 단일 페이지 — TRACKS 배열에 곡 메타 + 가사 다국어
├── register_song.py         # 비대화형 등록 스크립트
├── drop/                    # 신곡 입력 폴더 (이 폴더 자체는 비어 있게)
│   ├── README.md
│   └── processed/{num}/     # 등록된 곡의 원본 파일 보관 (.gitignore)
├── auto_lumi.py             # (구) 대화형 등록 스크립트 — 더 이상 사용 X
├── CLAUDE.md                # 이 파일
└── .gitignore
```

`index (8).html`, `index (9).html` — 과거 실수 커밋. 새 작업과 무관, 건드리지 않음.

## TRACKS 데이터 스키마

각 트랙은 `index.html` 안의 `TRACKS = [...]` 배열 원소:

```js
{
  num: 12, origLang: "ko",
  titleKr: "원곡 언어의 제목", titleEn: "보조 제목",
  duration: "3:45",
  tags: ["k-indie","ballad"],
  src: "https://github.com/yhcho3964-prog/lumi-music/releases/download/v1.0/12.Slug.mp3",
  lyrics: {
    ko: [{ section:"1절", lines:["...", "..."] }, ...],
    en: [{ section:"Verse 1", lines:[...] }, ...],
    es: [{ section:"Verso 1", lines:[...] }, ...]
  }
}
```

## 배포 도구

- **MP3 저장**: GitHub Release `v1.0`. URL 패턴: `releases/download/v1.0/{num}.{slug}.mp3`
- **호스팅**: Netlify, main 브랜치 push 시 ~30초 내 자동 배포
- **GitHub 인증**: `gh auth login` (yhcho3964-prog 계정)
- **필수 CLI**: `ffmpeg`, `ffprobe`, `gh`, `git`, `python` (+ 표준 라이브러리만)

## 자주 묻는 작업

- "곡 N개 보여줘" → `index.html`의 `TRACKS` 배열에서 `num:`을 grep
- "트랙 N번 가사 수정" → `index.html`에서 해당 트랙 블록을 Edit
- "태그 추가/변경" → 같은 곳에서 `tags:[...]` 수정 후 git push
- "사이트 안 열려요" → Netlify 상태 확인은 사용자에게 안내, Claude는 코드만 점검
