#!/usr/bin/env python3
"""
register_song.py — LU:MI 신곡 비대화형 등록 스크립트
====================================================
사용법:
    python register_song.py drop/registration.json

JSON 스키마:
{
  "mp3_path":  "drop/Song.mp3",          # 저장소 기준 상대경로 또는 절대경로
  "num":       12,                        # index.html 의 다음 트랙 번호
  "origLang":  "ko",                      # ko / en / es / ja
  "titleKr":   "원곡 제목 (원문)",        # 원곡 언어의 제목
  "titleEn":   "보조 제목",               # 한국어 곡이면 영문, 외국어 곡이면 한국어
  "duration":  "3:45",                    # 생략 시 ffprobe 로 자동 추출
  "tags":      ["k-indie","ballad"],
  "slug":      "Song.Title",              # 생략 시 titleEn 에서 자동 생성
  "lyrics": {                             # 4개 언어 모두 필수
    "ko": [{"section":"1절","lines":["..","..",".."]}, ...],
    "en": [{"section":"Verse 1","lines":[...]}, ...],
    "es": [{"section":"Verso 1","lines":[...]}, ...],
    "ja": [{"section":"1番","lines":[...]}, ...]
  }
}

처리 과정:
  ① ffprobe → 재생시간
  ② gh release upload v1.0 ← MP3 직접 업로드
  ③ index.html 의 TRACKS 배열에 새 트랙 추가
  ④ "N Tracks · 2025" 라벨 갱신
  ⑤ git add / commit / push  → Netlify 자동 배포
  ⑥ 처리된 파일은 drop/processed/{num}/ 으로 이동
"""

import os, sys, json, re, subprocess, shutil
from pathlib import Path

REPO_DIR     = Path(__file__).parent.resolve()
INDEX_HTML   = REPO_DIR / "index.html"
GITHUB_REPO  = "yhcho3964-prog/lumi-music"
GITHUB_TAG   = "v1.0"
RELEASE_BASE = f"https://github.com/{GITHUB_REPO}/releases/download/{GITHUB_TAG}"

REQUIRED_LANGS = ("ko", "en", "es", "ja")

# 전역 git 설정이 다른 사용자 이름으로 되어 있을 수 있어 commit 시 명시적으로 override
COMMIT_NAME  = "yhcho3964-prog"
COMMIT_EMAIL = "yhcho3964@gmail.com"

def info(m): print(f"  > {m}")
def ok(m):   print(f"  [OK] {m}")
def err(m):  print(f"  [ERROR] {m}", file=sys.stderr); sys.exit(1)
def step(n,m): print(f"\n[{n}] {m}")


def probe_duration(mp3: Path) -> str:
    r = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1", str(mp3)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        err(f"ffprobe failed: {r.stderr.strip()}")
    secs = float(r.stdout.strip())
    return f"{int(secs // 60)}:{int(secs % 60):02d}"


def upload_release(mp3: Path) -> str:
    r = subprocess.run(
        ["gh","release","upload",GITHUB_TAG,str(mp3),
         "--repo",GITHUB_REPO,"--clobber"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        err(f"gh release upload failed:\n{r.stderr.strip()}")
    return f"{RELEASE_BASE}/{mp3.name}"


def render_track_js(cfg: dict, src: str) -> str:
    lyr_blocks = []
    for lang, verses in cfg["lyrics"].items():
        v_parts = []
        for v in verses:
            ls = ",".join(json.dumps(l, ensure_ascii=False) for l in v["lines"])
            sec = json.dumps(v["section"], ensure_ascii=False)
            v_parts.append(f'{{section:{sec},lines:[{ls}]}}')
        lyr_blocks.append(f'      {lang}:[' + ",".join(v_parts) + ']')

    tags_js = "[" + ",".join(json.dumps(t) for t in cfg["tags"]) + "]"

    return (
        '  ,{\n'
        f'    num:{cfg["num"]}, origLang:"{cfg["origLang"]}", '
        f'titleKr:{json.dumps(cfg["titleKr"], ensure_ascii=False)}, '
        f'titleEn:{json.dumps(cfg["titleEn"], ensure_ascii=False)},\n'
        f'    duration:"{cfg["duration"]}", tags:{tags_js}, src:"{src}",\n'
        f'    lyrics:{{\n' + ",\n".join(lyr_blocks) + '\n    }\n  }'
    )


def update_index(cfg: dict, src: str):
    html = INDEX_HTML.read_text(encoding="utf-8")

    marker = "];\n\nconst TAG_LABEL="
    if marker not in html:
        err("index.html structure mismatch — marker `];\\n\\nconst TAG_LABEL=` not found")

    new_track = render_track_js(cfg, src)
    html = html.replace(marker, new_track + "\n" + marker, 1)

    # "11 Tracks · 2025" → "12 Tracks · 2025"
    html, n = re.subn(r'\d+ Tracks · 2025', f'{cfg["num"]} Tracks · 2025', html)
    if n == 0:
        info("Track count label not found — skipped")

    INDEX_HTML.write_text(html, encoding="utf-8")


def git_run(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git","-C",str(REPO_DIR), *args],
                          capture_output=True, text=True)


def git_push(title_kr: str):
    commit_args = [
        "-c", f"user.name={COMMIT_NAME}",
        "-c", f"user.email={COMMIT_EMAIL}",
        "commit", "-m", f"Add track: {title_kr}",
    ]
    for label, args in [
        ("add",    ["add","index.html"]),
        ("commit", commit_args),
        ("push",   ["push"]),
    ]:
        r = git_run(*args)
        if r.returncode != 0:
            err(f"git {label} failed:\n{r.stderr.strip() or r.stdout.strip()}")


def make_slug(cfg: dict) -> str:
    if cfg.get("slug"):
        s = cfg["slug"]
    else:
        s = cfg["titleEn"]
    s = re.sub(r"[^\w\-.]", ".", s)
    s = re.sub(r"\.+", ".", s).strip(".")
    return s or f"track{cfg['num']}"


def main():
    if len(sys.argv) < 2:
        err("Usage: python register_song.py <config.json>")

    cfg_path = Path(sys.argv[1]).resolve()
    if not cfg_path.exists():
        err(f"Config not found: {cfg_path}")

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for k in ("mp3_path","num","origLang","titleKr","titleEn","tags","lyrics"):
        if k not in cfg:
            err(f"Missing required JSON key: {k}")

    missing_langs = [l for l in REQUIRED_LANGS if l not in cfg["lyrics"]]
    if missing_langs:
        err(f"lyrics 에 빠진 언어: {', '.join(missing_langs)} "
            f"(필수: {', '.join(REQUIRED_LANGS)})")
    empty_langs = [l for l in REQUIRED_LANGS if not cfg["lyrics"][l]]
    if empty_langs:
        err(f"lyrics 가 비어 있는 언어: {', '.join(empty_langs)}")

    if cfg["origLang"] not in REQUIRED_LANGS:
        err(f"origLang 은 {REQUIRED_LANGS} 중 하나여야 함: {cfg['origLang']}")

    mp3 = Path(cfg["mp3_path"])
    if not mp3.is_absolute():
        mp3 = (REPO_DIR / cfg["mp3_path"]).resolve()
    if not mp3.exists():
        err(f"MP3 not found: {mp3}")

    print(f"\n=== Track #{cfg['num']}: {cfg['titleKr']} ({cfg['titleEn']}) ===")

    if not cfg.get("duration"):
        step("1","ffprobe — 재생시간 추출")
        cfg["duration"] = probe_duration(mp3)
        ok(f"duration = {cfg['duration']}")
    else:
        info(f"duration (제공됨) = {cfg['duration']}")

    # rename MP3 to canonical {num}.{slug}.mp3 before upload
    slug = make_slug(cfg)
    canonical_name = f"{cfg['num']}.{slug}.mp3"
    upload_path = mp3.parent / canonical_name
    if upload_path != mp3:
        if upload_path.exists():
            upload_path.unlink()
        shutil.copy2(mp3, upload_path)
    info(f"upload filename: {canonical_name}")

    step("2","gh release upload (MP3)")
    src = upload_release(upload_path)
    ok(f"uploaded → {src}")

    step("3","index.html 의 TRACKS 배열 갱신")
    update_index(cfg, src)
    ok(f"트랙 #{cfg['num']} 추가됨, 'N Tracks' 라벨 = {cfg['num']}")

    step("4","git add / commit / push")
    git_push(cfg["titleKr"])
    ok("push 완료 → Netlify 자동 배포 시작")

    step("5","처리 파일 정리")
    processed = REPO_DIR / "drop" / "processed" / str(cfg["num"])
    processed.mkdir(parents=True, exist_ok=True)

    drop_dir = (REPO_DIR / "drop").resolve()
    # MP3, MP3 canonical copy, registration.json + drop/ 안의 다른 모든 동반 파일
    # (README.md 와 processed/ 디렉토리는 제외)
    to_move = {mp3, upload_path, cfg_path}
    for f in drop_dir.iterdir():
        if f.is_dir(): continue
        if f.name == "README.md": continue
        to_move.add(f.resolve())

    for f in to_move:
        if f.exists():
            dest = processed / f.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(f), dest)
    ok(f"이동 완료 → drop/processed/{cfg['num']}/")

    print(f"\n🎵 등록 완료!  https://lumi-music.netlify.app  (30초 후 반영)\n")


if __name__ == "__main__":
    main()
