"""용우노트 화면 예시 그림 만들기 (연습용 샘플 노트만 넣은 깨끗한 상태).

만드는 파일: preview-mobile.png, preview-editor.png, preview-print.png, preview-draw.png
실행: python3 apps/yongwoo-note/test/make-previews.py
"""
import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8817


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={"width": 412, "height": 915},
        device_scale_factor=2,
        has_touch=True,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
    )
    page = ctx.new_page()
    page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
    page.wait_for_timeout(500)
    page.evaluate("addSamples()")
    page.wait_for_timeout(2200)
    page.evaluate("document.querySelector('#toast').hidden = true")
    page.screenshot(path=str(ROOT / "preview-mobile.png"))

    # 편집기 — 손글씨 약도가 들어 있는 농장 노트
    page.evaluate("() => { const n = S.notes.find(x => x.folderId === 'f-farm'); openEditor(n, false); }")
    page.wait_for_timeout(700)
    page.evaluate("document.querySelector('#edTools').scrollLeft = 0")
    page.evaluate("document.querySelector('#edScroll').scrollTop = 0")
    page.wait_for_timeout(300)
    page.screenshot(path=str(ROOT / "preview-editor.png"))

    # 손글씨 패드
    page.click("#tbDraw")
    page.wait_for_timeout(500)
    box = page.locator("#drawCanvas").bounding_box()
    page.mouse.move(box["x"] + 90, box["y"] + 260)
    page.mouse.down()
    for i in range(46):
        page.mouse.move(box["x"] + 90 + i * 5, box["y"] + 260 - int(70 * abs(((i % 18) / 18.0) - 0.5)))
    page.mouse.up()
    page.wait_for_timeout(300)
    page.screenshot(path=str(ROOT / "preview-draw.png"))
    page.click("#drawClose")
    page.wait_for_timeout(300)

    # 인쇄 미리보기
    page.evaluate("() => { const n = S.notes.find(x => x.folderId === 'f-farm'); openPrint([n]); }")
    page.wait_for_timeout(900)
    page.screenshot(path=str(ROOT / "preview-print.png"))

    # 실제 A4 인쇄물(PDF) — 인쇄 모드에서 인쇄물만 나오는지 함께 확인
    page.evaluate("(() => { document.querySelector('#previewPaper').style.zoom = '1'; })()")
    page.emulate_media(media="print")
    page.wait_for_timeout(300)
    page.pdf(path=str(ROOT / "preview-print.pdf"), format="A4", print_background=True)
    page.emulate_media(media="screen")

    ctx.close()
    browser.close()

httpd.shutdown()
print("previews written")
