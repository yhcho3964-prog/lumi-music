#!/usr/bin/env python3
"""
read_docx.py — .docx 파일에서 가사 텍스트 추출

사용법:
    python read_docx.py "drop/Song.docx"

표준 라이브러리만 사용 (zipfile + xml.etree). 별도 설치 불필요.

.docx 는 사실 zip 안에 word/document.xml 이 들어 있는 구조.
각 단락 <w:p> 안의 <w:t> 텍스트를 이어 붙이고, 단락 사이에 빈 줄을 둠.
빈 단락은 절 구분자로 보존.
"""
import sys, zipfile, re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_text(docx_path: Path) -> str:
    if not docx_path.exists():
        sys.exit(f"파일 없음: {docx_path}")
    if docx_path.suffix.lower() != ".docx":
        sys.exit(f".docx 파일이 아닙니다: {docx_path}")

    with zipfile.ZipFile(docx_path) as z:
        try:
            xml_data = z.read("word/document.xml")
        except KeyError:
            sys.exit("word/document.xml 을 찾을 수 없음 (.docx 구조가 아닐 수 있음)")

    root = ET.fromstring(xml_data)
    paragraphs = []
    for p in root.iter(f"{{{NS['w']}}}p"):
        runs = []
        for elem in p.iter():
            tag = elem.tag.split("}", 1)[-1]
            if tag == "t" and elem.text:
                runs.append(elem.text)
            elif tag == "tab":
                runs.append("\t")
            elif tag == "br":
                runs.append("\n")
        paragraphs.append("".join(runs).strip())

    # 연속 빈 단락 → 한 줄로 압축, 단락 사이 빈 줄 유지
    text = "\n".join(paragraphs)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python read_docx.py <file.docx>")
    path = Path(sys.argv[1])
    sys.stdout.reconfigure(encoding="utf-8")
    print(extract_text(path))


if __name__ == "__main__":
    main()
