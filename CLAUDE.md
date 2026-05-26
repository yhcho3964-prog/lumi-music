# LU:MI Music Library — Claude 작업 가이드

`yhcho3964-prog/lumi-music` 저장소의 신곡 등록 자동화 환경입니다. Netlify 배포 URL: https://lumi-music.netlify.app

## 신곡 등록 워크플로우 (사용자가 가장 자주 요청하는 작업)

### 트리거
사용자가 다음 중 하나를 말하면 등록 절차를 시작:
- "등록해줘", "신곡 등록", "이 곡 올려줘", "register"
- 별다른 지시 없이 `drop/` 폴더에 새 MP3 + 가사 파일을 두고 메시지를 보내는 경우

### 입력 (하위폴더당 한 곡)
```
drop/
├─ 곡제목 A/
│  ├─ Song A (Sub).mp3
│  └─ Song A (Sub)_가사.docx
├─ 곡제목 B/
│  └─ ...
└─ README.md
```
- 각 하위폴더 = 한 곡. 폴더명은 사용자가 알아보기 쉬운 한글 곡명 추천.
- 폴더 안에 **MP3 1개 + Word 가사 1개** (.docx).
- 파일명은 보통 `원제 (보조제).mp3` 형식 — 보조제가 비어 있으면 적절히 번역해서 제안.
- 여러 하위폴더가 있으면 발견 순서대로 **순차 등록**.

### Claude가 해야 할 일 (대화 안에서 수행)

1. **drop/ 스캔** — `processed/` 와 README.md 외 모든 하위폴더 = 등록 대기 곡. 각 폴더에 대해 2~9 단계를 순차 수행. 폴더가 0개면 사용자에게 "drop/곡제목/ 안에 MP3+.docx 넣어주세요" 안내.
2. **가사 추출** — `python read_docx.py "drop/곡제목/<파일>.docx"` 로 텍스트 추출 후 원곡 언어 자동 감지 (한글/일본어/스페인어/영어). .docx는 Read 도구로 직접 못 읽으니 반드시 read_docx.py 경유.
3. **제목 파싱**:
   - `원제 (보조제).mp3` 패턴에서 추출
   - `titleKr` = 원곡 언어의 제목 (한국어/영어/스페인어/일본어 등 어느 것이든 가능)
   - `titleEn` = 보조 제목 (한국어 원곡이면 영문, 외국어 원곡이면 한국어 번역이 일반적이나, 사용자가 명시한 보조제가 있으면 그대로)
   - 보조제가 비어 있거나 모호하면 Claude가 적절한 번역 제목을 제안 후 사용자 확인
4. **다음 트랙 번호 결정** — `index.html`의 `TRACKS` 배열에서 `num` 최댓값 + 1.
5. **가사 번역 — 4개 언어 전부 필수** (Claude가 직접 번역, 외부 API 호출 없음):
   - `lyrics:{}` 에 **반드시 `ko`, `en`, `es`, `ja` 4개 키 모두 존재**해야 함
   - 원곡 언어 가사는 원문 그대로, 나머지 3개 언어는 번역
   - 원곡 → 번역 시 절 구조와 절 개수 유지, 시적 표현·운율·감성 살리기
   - 섹션 라벨은 언어별 관례 사용:
     - ko: `1절`, `2절`, `3절`, `후렴`, `브리지`, `아웃트로`
     - en: `Verse 1`, `Verse 2`, `Verse 3`, `Chorus`, `Bridge`, `Outro`
     - es: `Verso 1`, `Verso 2`, `Verso 3`, `Estribillo`, `Puente`, `Outro`
     - ja: `1番`, `2番`, `3番`, `サビ`, `ブリッジ`, `アウトロ`
   - 같은 의미의 절은 같은 위치에 매핑 (예: 모든 언어에서 3번째 블록이 후렴/Chorus/Estribillo/サビ)
6. **태그 제안** — 가사·제목·분위기를 참고해서 다음 중 골라 제안:
   - `k-indie`, `ballad`, `jazz`, `neo-classical`, `j-indie`, `world`
   - 사용자 확인을 받고 진행
7. **registration.json 작성** — `drop/곡제목/registration.json` 으로 저장 (해당 곡 폴더 안에). `mp3_path` 는 파일명만 적어도 됨 (곡 폴더 기준 해석). 스키마는 register_song.py 상단 docstring 참고.
8. **register_song.py 실행** — `python register_song.py "drop/곡제목/"` (폴더 인자만 줘도 안의 registration.json 자동 탐색). 스크립트가 ffprobe·gh release upload·index.html 갱신·git push·곡 폴더 통째 이동(→ drop/processed/{num}/)까지 모두 수행.
9. **결과 보고** — 트랙 번호, GitHub Release URL, Netlify 배포 안내(30초).
10. **다음 폴더로** — 등록 대기 폴더가 더 있으면 2번 단계로 돌아가 반복. 트랙 번호는 자동 증가 (각 호출마다 index.html 의 max num + 1).

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
├── read_docx.py             # .docx 가사 텍스트 추출 (stdlib only)
├── drop/                    # 신곡 입력 폴더 (이 폴더 자체는 비어 있게)
│   ├── README.md
│   └── processed/{num}/     # 등록된 곡의 원본 파일 보관 (.gitignore)
├── CLAUDE.md                # 이 파일
└── .gitignore
```

`auto_lumi.py` — 클론된 저장소에는 없는 구 대화형 스크립트. `register_song.py` 가 대체.

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
    ko: [{ section:"1절",     lines:["...", "..."] }, ...],
    en: [{ section:"Verse 1", lines:[...] }, ...],
    es: [{ section:"Verso 1", lines:[...] }, ...],
    ja: [{ section:"1番",     lines:[...] }, ...]
  }
}
```

**중요**: 새 트랙은 위 4개 언어 키(`ko`/`en`/`es`/`ja`)를 모두 가져야 함. `register_song.py` 가 검증.

기존 트랙(num 1~11) 중 일부는 ja 누락이 있으나 호환을 위해 그대로 둠. 사용자가 명시적으로 백필 요청 시에만 채움.

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
