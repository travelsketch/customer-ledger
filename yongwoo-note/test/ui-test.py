"""
용우노트 웹앱 자동 검증 (Playwright + 로컬 HTTP 서버, 모바일 412x915)
- 노트 작성·서식(굵게/기울임/밑줄/형광펜/글자크기/글머리/체크리스트)·페이지 스타일
- 폴더 추가·이동·삭제, 핀 고정, 즐겨찾기, 검색, 정렬, 보기 전환
- 사진 첨부 자동 압축(긴 변 1600px·JPEG 80%), 카메라 입력, 손글씨 그리기
- 휴지통(복구·영구 삭제), 인쇄 미리보기/A4 인쇄, JSON 백업·복원, TXT 내보내기
- 구글 드라이브 동기화 엔진(모의 서버), 오프라인(PWA) 동작, 콘솔 오류 0건
실행: python3 apps/yongwoo-note/test/ui-test.py
"""
import json
import socketserver
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8814
BASE = f"http://127.0.0.1:{PORT}"
ART = ROOT / ".test-artifacts"
ART.mkdir(exist_ok=True)

results = []
errors = []


def check(name, cond, detail=""):
    ok = bool(cond)
    results.append((ok, name, detail))
    if not ok:
        errors.append(f"{name} :: {detail}")
    print(("  ✅ " if ok else "  ❌ ") + name + (f" — {detail}" if detail else ""))


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


def serve():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# ── 시험용 큰 사진(2400x1800, 노이즈) — 자동 압축 확인용 ─────────────
def make_big_photo():
    path = ART / "big-photo.jpg"
    if path.exists():
        return path
    import random
    random.seed(7)
    img = Image.new("RGB", (2400, 1800))
    px = img.load()
    for y in range(0, 1800, 4):
        for x in range(0, 2400, 4):
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            for dy in range(4):
                for dx in range(4):
                    px[x + dx, y + dy] = (r, g, b)
    img.save(path, quality=95)
    return path


DRIVE_MOCK = r"""
(function () {
  window.google = {
    accounts: {
      oauth2: {
        initTokenClient: function (cfg) {
          return {
            requestAccessToken: function () {
              window.__drive.tokenCalls = (window.__drive.tokenCalls || 0) + 1;
              setTimeout(function () { cfg.callback({ access_token: 'FAKE_TOKEN', expires_in: 3600 }); }, 5);
            }
          };
        }
      }
    }
  };
  window.__drive = window.__drive || { store: { file: null }, log: [], uploads: 0 };
  var realFetch = window.fetch.bind(window);
  function jsonRes(obj, status) {
    return new Response(JSON.stringify(obj), { status: status || 200, headers: { 'Content-Type': 'application/json' } });
  }
  window.fetch = function (url, opts) {
    var u = String(url);
    opts = opts || {};
    if (u.indexOf('googleapis.com') < 0) return realFetch(url, opts);
    var method = (opts.method || 'GET').toUpperCase();
    window.__drive.log.push(method + ' ' + u.slice(0, 90));
    if (u.indexOf('/drive/v3/files?') >= 0 && u.indexOf('spaces=appDataFolder') >= 0) {
      var has = !!window.__drive.store.file;
      return Promise.resolve(jsonRes({ files: has ? [{ id: 'F1', name: 'yongwoo-note-sync.json', modifiedTime: '2026-11-23T00:00:00Z', size: '100' }] : [] }));
    }
    if (u.indexOf('upload/drive/v3/files?uploadType=multipart') >= 0) {
      var body = String(opts.body || '');
      var parts = body.split('\r\n\r\n');
      var last = parts[parts.length - 1].replace(/\r\n--[^\r\n]*--\s*$/, '');
      window.__drive.store.file = last;
      window.__drive.uploads++;
      return Promise.resolve(jsonRes({ id: 'F1' }));
    }
    if (u.indexOf('upload/drive/v3/files/F1?uploadType=media') >= 0) {
      window.__drive.store.file = String(opts.body || '');
      window.__drive.uploads++;
      return Promise.resolve(jsonRes({ id: 'F1' }));
    }
    if (u.indexOf('/drive/v3/files/F1?alt=media') >= 0) {
      return Promise.resolve(new Response(window.__drive.store.file || '', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    }
    return Promise.resolve(jsonRes({ error: 'mock-miss ' + u }, 404));
  };
})();
"""


def main():
    httpd = serve()
    big_photo = make_big_photo()
    console = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 412, "height": 915},
            device_scale_factor=2,
            has_touch=True,
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            accept_downloads=True,
        )
        ctx.add_init_script(DRIVE_MOCK)
        page = ctx.new_page()
        page.on("console", lambda m: console.append((m.type, m.text)))
        page.on("pageerror", lambda e: console.append(("pageerror", str(e))))

        def goto():
            page.goto(f"{BASE}/index.html", wait_until="load")
            page.wait_for_timeout(500)

        print("\n[1] 기본 화면")
        goto()
        check("앱 제목", page.title() == "용우노트", page.title())
        check("상단 제목", page.locator(".brand-tx h1").inner_text() == "용우노트")
        check("빈 상태 안내", page.locator("#empty").is_visible())
        chips = page.locator("#folderBar .fchip").all_inner_texts()
        check("기본 폴더 4개 + 전체·즐겨찾기·휴지통", len(chips) == 8 and "업무" in chips and "고객" in chips and "농장" in chips and "개인" in chips, str(chips))

        man = page.evaluate("fetch('./manifest.webmanifest').then(r=>r.json())")
        check("manifest 이름", man["name"] == "용우노트" and man["short_name"] == "용우노트", man.get("name"))
        sizes = [i.get("sizes") for i in man["icons"]]
        check("manifest 아이콘 192/512/maskable", "192x192" in sizes and "512x512" in sizes and any(i.get("purpose") == "maskable" for i in man["icons"]), str(sizes))
        check("매니페스트 링크", page.locator("link[rel=manifest]").count() == 1)
        sw_ready = page.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!r)")
        check("서비스 워커 등록", sw_ready)
        for f in ["icon.svg", "icon-192.png", "icon-512.png", "icon-512-maskable.png"]:
            ok = page.evaluate(f"fetch('./{f}').then(r=>r.ok)")
            check(f"아이콘 접근 {f}", ok)

        print("\n[2] 노트 작성과 서식")
        page.click("#fab")
        page.wait_for_timeout(350)
        check("새 노트 편집기 열림", page.locator("#editor").is_visible())
        page.fill("#edTitle", "검증용 업무 노트")
        page.click("#edBody")
        page.keyboard.type("첫째 줄입니다")
        page.keyboard.press("Enter")
        page.keyboard.type("둘째 줄입니다")
        page.keyboard.press("Enter")
        page.keyboard.type("굵은글씨")
        page.keyboard.down("Shift")
        for _ in range(4):
            page.keyboard.press("ArrowLeft")
        page.keyboard.up("Shift")
        page.click("#tbBold")
        page.wait_for_timeout(100)
        check("굵게 적용", page.evaluate("!!document.querySelector('#edBody b, #edBody strong, #edBody span[style*=\"font-weight\"]')"))
        page.click("#tbItalic")
        check("기울임 적용", page.evaluate("!!document.querySelector('#edBody i, #edBody em, #edBody span[style*=\"italic\"]')"))
        page.click("#tbUnder")
        check("밑줄 적용", page.evaluate("!!document.querySelector('#edBody u, #edBody span[style*=\"underline\"]')"))
        page.click("#tbHl")
        check("형광펜 적용", page.evaluate("!!document.querySelector('#edBody span[style*=\"background-color\"], #edBody mark')"))

        page.click("#edBody")
        page.keyboard.press("Control+End")
        page.keyboard.press("Enter")
        page.click("#tbSize")
        page.wait_for_timeout(250)
        check("글자 크기 시트 열림", page.locator("#sheetModal").is_visible() and page.locator("[data-size]").count() == 4)
        page.click("[data-size='6']")
        page.wait_for_timeout(200)
        page.keyboard.type("큰 글씨")
        check("글자 크기 적용", page.evaluate("!!document.querySelector('#edBody span[style*=\"font-size\"], #edBody font')"))

        page.keyboard.press("Enter")
        page.click("#tbBullet")
        page.keyboard.type("글머리 항목")
        check("글머리 기호 목록", page.evaluate("!!document.querySelector('#edBody ul li')"))

        page.keyboard.press("Enter")
        page.keyboard.press("Enter")
        page.click("#tbTodo")
        page.keyboard.type("할 일 첫번째")
        page.wait_for_timeout(200)
        check("체크리스트 삽입", page.locator("#edBody .todo").count() >= 1)
        page.locator("#edBody .todo .ck").first.click()
        page.wait_for_timeout(150)
        check("체크 표시 토글", page.evaluate("document.querySelector('#edBody .todo').classList.contains('done')"))
        page.locator("#edBody .todo .ck").first.click()
        check("체크 해제", page.evaluate("!document.querySelector('#edBody .todo').classList.contains('done')"))

        page.evaluate("openStylePick()")
        page.wait_for_timeout(250)
        page.click("[data-style='yellow']")
        page.wait_for_timeout(250)
        check("페이지 스타일 적용", page.evaluate("document.querySelector('#paper').classList.contains('p-yellow')"))

        page.wait_for_timeout(1100)
        check("자동 저장 표시", page.locator("#edState").inner_text().startswith("저장됨"), page.locator("#edState").inner_text())
        page.click("#edBack")
        page.wait_for_timeout(700)
        check("목록으로 복귀 + 노트 카드", page.locator("#noteList .card-note").count() == 1)
        check("카드 제목", page.locator("#noteList .cn-title").first.inner_text() == "검증용 업무 노트")
        check("카드 폴더 표시", page.locator("#noteList .tag-folder").first.inner_text() == "업무")

        print("\n[3] 폴더 · 핀 · 즐겨찾기 · 검색 · 보기/정렬")
        page.click("#folderBar [data-folder='__add']")
        page.wait_for_timeout(300)
        page.fill("#newFolderName", "건강")
        page.click("#newFolderAdd")
        page.wait_for_timeout(500)
        check("새 폴더 추가", "건강" in page.locator("#folderBar").inner_text())

        page.locator("#pinList .card-note, #noteList .card-note").first.click()
        page.wait_for_timeout(400)
        page.click("#edFolderName")
        page.wait_for_timeout(300)
        custom = page.evaluate("S.folders.find(f=>f.name==='건강').id")
        page.click(f"[data-pick-folder='{custom}']")
        page.wait_for_timeout(600)
        check("노트 폴더 이동", page.locator("#edFolderName").inner_text() == "건강")
        page.click("#edPin")
        page.click("#edStar")
        page.wait_for_timeout(700)
        page.click("#edBack")
        page.wait_for_timeout(700)
        page.click("#folderBar [data-folder='all']")
        page.wait_for_timeout(300)
        check("핀 고정 영역", page.locator("#pinSection").is_visible() and page.locator("#pinList .card-note").count() == 1)
        check("핀 아이콘 표시", "📌" in page.locator("#pinList .cn-flags").first.inner_text())
        page.click("#folderBar [data-folder='star']")
        page.wait_for_timeout(300)
        check("즐겨찾기 필터", page.locator("#noteList .card-note, #pinList .card-note").count() == 1)

        page.click("#folderBar [data-folder='all']")
        page.click("#btnSearch")
        page.wait_for_timeout(200)
        page.fill("#q", "둘째")
        page.wait_for_timeout(300)
        check("본문 검색", page.locator("#pinList .card-note, #noteList .card-note").count() == 1)
        page.fill("#q", "없는단어")
        page.wait_for_timeout(300)
        check("검색 결과 없음 안내", page.locator("#empty").is_visible())
        page.click("#qClear")
        page.wait_for_timeout(300)
        check("검색 지우기", page.locator("#pinList .card-note, #noteList .card-note").count() == 1)
        page.click("#btnSearch")
        page.wait_for_timeout(200)

        page.click("#btnView")
        page.wait_for_timeout(250)
        check("목록 보기 전환", "list" in (page.locator("#noteList").get_attribute("class") or ""))
        page.screenshot(path=str(ROOT / "screenshot-list.png"))
        page.click("#btnView")
        page.wait_for_timeout(200)

        page.click("#btnSort")
        page.wait_for_timeout(200)
        check("정렬 전환(제목순)", "제목순" in page.locator("#btnSort").inner_text())
        page.click("#btnSort")
        page.wait_for_timeout(200)

        print("\n[4] 사진·PDF 첨부와 자동 압축")
        page.locator("#pinList .card-note, #noteList .card-note").first.click()
        page.wait_for_timeout(400)
        page.set_input_files("#filePick", str(big_photo))
        page.wait_for_timeout(3500)
        info = page.evaluate("""() => { const a = S.atts[0]; return a ? {n:a.name, t:a.type, size:a.size, w:a.width, h:a.height} : null; }""")
        check("사진 첨부 저장", info is not None, str(info))
        orig = big_photo.stat().st_size
        check("자동 압축(용량 감소)", info and info["size"] < orig // 3, f"{orig} -> {info['size'] if info else '-'}")
        dims = page.evaluate("""() => new Promise(res => { const a = S.atts[0]; const img = new Image(); img.onload = () => res({w: img.naturalWidth, h: img.naturalHeight}); img.src = URL.createObjectURL(a.blob); })""")
        check("긴 변 1600px 이하", max(dims["w"], dims["h"]) <= 1600 and dims["w"] > 100, str(dims))
        check("JPEG 로 저장", info and info["t"] == "image/jpeg", info["t"] if info else "")
        check("첨부 띠 표시", page.locator("#attBlock").is_visible() and page.locator("#attStrip .att-item").count() == 1)
        cap = page.get_attribute("#camPick", "capture")
        acc = page.get_attribute("#camPick", "accept")
        check("카메라 입력 capture=environment", cap == "environment" and acc == "image/*", f"{cap} / {acc}")
        check("PDF 선택 허용", "application/pdf" in (page.get_attribute("#filePick", "accept") or ""))

        page.locator("#attStrip .att-item").first.click()
        page.wait_for_timeout(400)
        check("사진 크게 보기", page.locator("#viewerModal").is_visible() and page.locator("#viewerBody img").count() == 1)
        page.screenshot(path=str(ROOT / "screenshot-viewer.png"))
        page.click("#viewerClose")
        page.wait_for_timeout(300)

        print("\n[5] 손글씨 그리기")
        page.click("#tbDraw")
        page.wait_for_timeout(400)
        box = page.locator("#drawCanvas").bounding_box()
        page.mouse.move(box["x"] + 70, box["y"] + 140)
        page.mouse.down()
        for i in range(30):
            page.mouse.move(box["x"] + 70 + i * 7, box["y"] + 140 + (i % 6) * 14)
        page.mouse.up()
        page.wait_for_timeout(200)
        page.screenshot(path=str(ROOT / "screenshot-draw.png"))
        before = page.locator("#attStrip .att-item").count()
        page.click("#drawSave")
        page.wait_for_timeout(1200)
        check("그림이 첨부로 저장", page.locator("#attStrip .att-item").count() == before + 1)
        check("본문에 그림 삽입", page.evaluate("!!document.querySelector('#edBody img.in-img[data-att]')"))
        check("그림 data-att 저장", page.evaluate("S.ed.body.indexOf('data-att') >= 0"))
        check("그림에 blob 주소는 저장하지 않음", page.evaluate("S.ed.body.indexOf('blob:') < 0"))
        undos = page.evaluate("DW.list.length")
        check("그리기 스트로크 기록", undos >= 1, str(undos))

        page.click("#edBack")
        page.wait_for_timeout(800)
        note_id = page.evaluate("S.notes[0].id")
        check("저장 후 카드 썸네일", page.locator("#noteList .cn-thumb, #pinList .cn-thumb").count() >= 1)

        print("\n[6] 인쇄 미리보기 · A4 인쇄")
        page.evaluate("openEditor(S.notes[0], false)")
        page.wait_for_timeout(400)
        page.click("#edMenu")
        page.wait_for_timeout(300)
        page.click("[data-e='print']")
        page.wait_for_timeout(700)
        check("인쇄 미리보기 열림", page.locator("#printModal").is_visible())
        paper = page.locator("#previewPaper").inner_text()
        check("인쇄 제목 '용우노트'", "용우노트" in paper)
        check("인쇄 본문 포함", "검증용 업무 노트" in paper and "둘째 줄입니다" in paper)
        check("인쇄물 체크리스트", page.locator("#previewPaper .todo").count() >= 1)
        check("인쇄물 그림", page.locator("#previewPaper .pn-body img").count() >= 1)
        page.screenshot(path=str(ROOT / "screenshot-print.png"))
        page.evaluate("(() => { document.querySelector('#previewPaper').style.zoom = '1'; })()")
        page.emulate_media(media="print")
        page.wait_for_timeout(300)
        vis_print = page.evaluate("getComputedStyle(document.querySelector('#printRoot')).display")
        vis_list = page.evaluate("getComputedStyle(document.querySelector('#listView')).display")
        check("인쇄 모드에서 인쇄물만 보임", vis_print == "block" and vis_list == "none", f"{vis_print}/{vis_list}")
        page.pdf(path=str(ROOT / "preview-print.pdf"), format="A4", print_background=True)
        page.emulate_media(media="screen")
        page.wait_for_timeout(200)
        page.click("#printClose")
        page.wait_for_timeout(400)

        print("\n[7] 텍스트·JSON 내보내기와 복원")
        page.click("#edMenu")
        page.wait_for_timeout(300)
        with page.expect_download() as dl:
            page.click("[data-e='txt']")
        d = dl.value
        check("TXT 파일 이름", d.suggested_filename.startswith("용우노트-") and d.suggested_filename.endswith(".txt"), d.suggested_filename)
        txt_path = ART / "note.txt"
        d.save_as(str(txt_path))
        txt = txt_path.read_text(encoding="utf-8")
        check("TXT 내용", "검증용 업무 노트" in txt and "둘째 줄입니다" in txt and "☐ 할 일 첫번째" in txt, txt[:80].replace("\n", " "))

        page.wait_for_timeout(300)
        page.click("#edBack")
        page.wait_for_timeout(700)
        page.click("#btnMenu")
        page.wait_for_timeout(300)
        with page.expect_download() as dl2:
            page.click("[data-m='backup']")
        d2 = dl2.value
        check("JSON 백업 파일 이름", d2.suggested_filename == f"용우노트-백업-{time.strftime('%Y-%m-%d')}.json", d2.suggested_filename)
        backup_path = ART / "backup.json"
        d2.save_as(str(backup_path))
        data = json.loads(backup_path.read_text(encoding="utf-8"))
        check("백업 내용", data["app"] == "yongwoo-note" and len(data["notes"]) == 1 and len(data["attachments"]) >= 2, f"{len(data.get('notes', []))} notes / {len(data.get('attachments', []))} files")
        check("백업에 그림 데이터 포함", any(a.get("data") for a in data["attachments"]))

        data["notes"].append({
            "id": "restore-test-1", "title": "복원된 노트", "body": "<div>복원 확인</div>",
            "folderId": "f-me", "tags": ["복원"], "pinned": False, "starred": False, "style": "white",
            "createdAt": int(time.time() * 1000), "updatedAt": int(time.time() * 1000),
            "deletedAt": 0, "sample": False,
        })
        restore_path = ART / "restore.json"
        restore_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        page.set_input_files("#restorePick", str(restore_path))
        page.wait_for_timeout(400)
        check("복원 확인 창", page.locator("#confirmModal").is_visible())
        page.click("#confirmYes")
        page.wait_for_timeout(900)
        titles = page.locator("#noteList .cn-title, #pinList .cn-title").all_inner_texts()
        check("복원 후 노트 추가", "복원된 노트" in titles, str(titles))

        print("\n[8] 휴지통")
        page.evaluate("deleteNote(S.notes.find(n=>n.title==='복원된 노트').id)")
        page.wait_for_timeout(500)
        page.click("#folderBar [data-folder='trash']")
        page.wait_for_timeout(400)
        check("휴지통에 노트", page.locator("#noteList .card-note.trash").count() == 1)
        check("복구·영구삭제 버튼", page.locator("[data-act='restore']").count() == 1 and page.locator("[data-act='perm']").count() == 1)
        page.screenshot(path=str(ROOT / "screenshot-trash.png"))
        page.click("[data-act='restore']")
        page.wait_for_timeout(600)
        check("휴지통 복구", page.locator("#noteList .card-note.trash").count() == 0)
        page.click("#folderBar [data-folder='all']")
        page.wait_for_timeout(300)
        check("복구된 노트가 목록에", "복원된 노트" in page.locator("#noteList").inner_text())
        page.click("#folderBar [data-folder='trash']")
        page.wait_for_timeout(300)

        print("\n[8b] 폴더 삭제(노트 이동)와 선택 인쇄")
        page.evaluate("addFolder('임시')")
        page.wait_for_timeout(500)
        tmp_id = page.evaluate("(S.folders.find(f => f.name === '임시') || {}).id")
        check("임시 폴더 생성", bool(tmp_id), str(tmp_id))
        page.evaluate("openEditor(S.notes.find(n => n.title === '복원된 노트'), false)")
        page.wait_for_timeout(400)
        page.click("#edFolderName")
        page.wait_for_timeout(300)
        page.click(f"[data-pick-folder='{tmp_id}']")
        page.wait_for_timeout(500)
        page.click("#edBack")
        page.wait_for_timeout(800)
        page.click("#folderBar [data-folder='__add']")
        page.wait_for_timeout(400)
        page.click(f"[data-delfolder='{tmp_id}']")
        page.wait_for_timeout(400)
        page.click("#confirmYes")
        page.wait_for_timeout(900)
        check("폴더 삭제 후 칩 사라짐", "임시" not in page.locator("#folderBar").inner_text())
        moved = page.evaluate("(S.notes.find(n => n.title === '복원된 노트') || {}).folderId")
        check("폴더 삭제 시 노트는 개인으로 이동", moved == "f-me", str(moved))
        check("노트 자체는 남음", page.evaluate("!!S.notes.find(n => n.title === '복원된 노트' && !n.deletedAt)"))

        page.click("#folderBar [data-folder='all']")
        page.wait_for_timeout(300)
        page.click("#btnSelect")
        page.wait_for_timeout(200)
        cards = page.locator("#pinList .card-note, #noteList .card-note")
        cards.nth(0).click()
        cards.nth(1).click()
        page.wait_for_timeout(300)
        check("선택 모드 표시", page.locator("#selBar").is_visible() and "2개 선택" in page.locator("#selCount").inner_text())
        page.click("#selPrint")
        page.wait_for_timeout(900)
        check("선택한 노트 인쇄", page.locator("#previewPaper .print-note").count() == 2, str(page.locator("#previewPaper .print-note").count()))
        page.click("#printClose")
        page.wait_for_timeout(500)

        print("\n[9] 구글 드라이브 동기화 (모의 서버)")
        ok = page.evaluate("NoteDrive.connect().then(()=>true).catch(e=>String(e && e.message))")
        page.wait_for_timeout(600)
        check("드라이브 연결", ok is True, str(ok))
        payload = page.evaluate("JSON.parse(window.__drive.store.file || 'null')")
        check("앱 전용 파일 업로드", payload and payload.get("app") == "yongwoo-note", str(payload)[:60] if payload else "")
        check("파일 이름", payload and payload.get("app") == "yongwoo-note")
        names = [i.get("title") for i in payload.get("items", []) if i.get("kind") == "note"]
        check("업로드 내용에 노트", "검증용 업무 노트" in names, str(names))
        check("업로드 내용에 폴더(건강)", any(i.get("name") == "건강" for i in payload.get("items", [])))
        check("첨부 파일 동기화", len(payload.get("files", [])) >= 2, str(len(payload.get("files", []))))
        check("상태 표시 연결됨", page.locator("#driveText").inner_text().startswith("연결됨"), page.locator("#driveText").inner_text())

        # 다른 기기에서 올린 새 노트를 받아오는지
        remote = json.loads(json.dumps(payload))
        now = int(time.time() * 1000) + 5000
        remote["rev"] = now
        remote["items"].append({
            "kind": "note", "id": "remote-note-1", "title": "다른 기기 노트", "body": "<div>드라이브에서 받음</div>",
            "folderId": "f-farm", "tags": [], "pinned": False, "starred": False, "style": "white",
            "createdAt": now, "updatedAt": now, "deletedAt": 0, "sample": False, "upd": now,
        })
        page.evaluate("""(remote) => {
            window.__drive.store.file = JSON.stringify(remote);
            const st = JSON.parse(localStorage.getItem('yongwooNote.drive.v1') || '{}');
            const s2 = JSON.parse(localStorage.getItem('yongwooNote.sync.v1') || '{}');
            st.lastSyncRev = Number(s2.rev) || 0;
            localStorage.setItem('yongwooNote.drive.v1', JSON.stringify(st));
        }""", remote)
        page.evaluate("NoteDrive.sync(true)")
        page.wait_for_timeout(1200)
        check("다른 기기 노트 받기", page.evaluate("!!S.notes.find(n=>n.id==='remote-note-1')"))
        check("받은 노트 내용", page.evaluate("(S.notes.find(n=>n.id==='remote-note-1')||{}).title === '다른 기기 노트'"))

        # 영구 삭제 → 삭제 표시(tombstone)가 업로드되는지
        page.evaluate("deleteNoteNow('remote-note-1')")
        page.wait_for_timeout(300)
        page.evaluate("NoteDrive.sync(true)")
        page.wait_for_timeout(1200)
        payload2 = page.evaluate("JSON.parse(window.__drive.store.file || 'null')")
        check("삭제 표시(tombstone) 전송", payload2 and "remote-note-1" in (payload2.get("deleted") or {}), str(list((payload2.get('deleted') or {}).keys()))[:80])

        page.click("#driveBarBtn")
        page.wait_for_timeout(400)
        check("드라이브 관리 시트", page.locator("#sheetModal").is_visible() and "동기화 상태" in page.locator("#sheetBody").inner_text())
        page.screenshot(path=str(ROOT / "screenshot-drive.png"))
        page.click("#sheetClose")
        page.wait_for_timeout(300)

        print("\n[10] 샘플 노트 화면(검증용 캡처)")
        page.evaluate("addSamples()")
        page.wait_for_timeout(2200)
        page.click("#folderBar [data-folder='all']")
        page.wait_for_timeout(400)
        page.screenshot(path=str(ART / "sample-list.png"))
        page.evaluate("() => { const n = S.notes.find(x => x.folderId === 'f-farm'); openEditor(n, false); }")
        page.wait_for_timeout(700)
        page.screenshot(path=str(ART / "sample-editor.png"))
        page.click("#edBack")
        page.wait_for_timeout(900)

        print("\n[11] 상태 유지·재접속·오프라인")
        page.evaluate("""() => {
            const st = JSON.parse(localStorage.getItem('yongwooNote.drive.v1') || '{}');
            st.on = false; localStorage.setItem('yongwooNote.drive.v1', JSON.stringify(st));
        }""")
        before_count = page.evaluate("S.notes.length")
        page.reload(wait_until="load")
        page.wait_for_timeout(900)
        check("새로 열어도 노트 유지", page.evaluate("S.notes.length") >= before_count, f"{before_count} → {page.evaluate('S.notes.length')}")
        check("새로 열어도 폴더 유지", "건강" in page.locator("#folderBar").inner_text())

        page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=15000)
        page.reload(wait_until="load")
        page.wait_for_timeout(800)
        ctx.set_offline(True)
        page.reload(wait_until="load")
        page.wait_for_timeout(1000)
        check("오프라인에서도 앱 열림", page.locator(".brand-tx h1").inner_text() == "용우노트")
        check("오프라인에서도 노트 보임", page.locator("#noteList .card-note, #pinList .card-note").count() >= 3)
        page.screenshot(path=str(ROOT / "screenshot-offline.png"))
        page.evaluate("openEditor(S.notes[0], false)")
        page.wait_for_timeout(400)
        check("오프라인에서 편집기 열림", page.locator("#editor").is_visible())
        page.click("#edBack")
        page.wait_for_timeout(700)
        ctx.set_offline(False)

        # 콘솔 오류
        errs = [m for m in console if m[0] in ("error", "pageerror")]
        net_errs = [m for m in console if m[0] == "warning" and "서비스 워커" in m[1]]
        check("콘솔 오류 0건", len(errs) == 0, str(errs[:4]))
        check("페이지 오류 0건", not [m for m in console if m[0] == "pageerror"], str([m for m in console if m[0] == "pageerror"][:3]))

        ctx.close()
        browser.close()
    httpd.shutdown()

    print("\n" + "=" * 60)
    ok_n = sum(1 for r in results if r[0])
    print(f"결과: {ok_n}/{len(results)} 통과")
    if errors:
        print("실패 항목:")
        for e in errors:
            print("  -", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
