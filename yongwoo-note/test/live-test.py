"""배포된 실제 주소 검증 — https://travelsketch.github.io/customer-ledger/yongwoo-note/"""
import time
from playwright.sync_api import sync_playwright

BASE = "https://travelsketch.github.io/customer-ledger/yongwoo-note/"
results = []


def check(name, cond, detail=""):
    results.append((bool(cond), name, detail))
    print(("  ✅ " if cond else "  ❌ ") + name + (f" — {detail}" if detail else ""))


logs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 412, "height": 915}, device_scale_factor=2, has_touch=True, locale="ko-KR")
    page = ctx.new_page()
    page.on("console", lambda m: logs.append((m.type, m.text)))
    page.on("pageerror", lambda e: logs.append(("pageerror", str(e))))

    print("\n[실제 주소]")
    page.goto(BASE, wait_until="load")
    page.wait_for_timeout(1200)
    check("주소 그대로 열림", page.url.rstrip("/") == BASE.rstrip("/"), page.url)
    check("제목", page.title() == "용우노트", page.title())
    check("상단 제목", page.locator(".brand-tx h1").inner_text() == "용우노트")
    check("빈 상태/목록 렌더", page.locator("#folderBar .fchip").count() == 8)

    man = page.evaluate("fetch('./manifest.webmanifest').then(r=>r.json())")
    check("manifest name", man["name"] == "용우노트" and man["short_name"] == "용우노트")
    check("start_url 상대경로", man["start_url"] == "./index.html", man["start_url"])
    check("scope 상대경로", man["scope"] == "./", man["scope"])

    for f in ["index.html", "manifest.webmanifest", "sw.js", "icon.svg", "icon-192.png", "icon-512.png", "icon-512-maskable.png"]:
        r = page.evaluate(f"fetch('./{f}').then(r=>r.status)")
        check(f"{f} 200", r == 200, str(r))

    sw = page.evaluate("navigator.serviceWorker.getRegistration().then(r=>r ? (r.active? 'active':'waiting') : 'none')")
    check("서비스 워커 활성", sw in ("active", "waiting"), str(sw))

    print("\n[실제 주소 — 노트 작성·오프라인]")
    page.click("#fab")
    page.wait_for_timeout(400)
    page.fill("#edTitle", "배포 확인 노트")
    page.click("#edBody")
    page.keyboard.type("실제 주소에서 적었습니다")
    page.keyboard.press("Enter")
    page.click("#tbTodo")
    page.keyboard.type("할 일")
    page.wait_for_timeout(1100)
    page.click("#edBack")
    page.wait_for_timeout(900)
    check("노트 저장·카드 표시", page.locator("#pinList .card-note, #noteList .card-note").count() == 1)
    check("카드 제목", page.evaluate("!!S.notes.find(n => n.title === '배포 확인 노트')"))

    page.evaluate("addSamples()")
    page.wait_for_timeout(2200)
    page.evaluate("document.querySelector('#toast').hidden = true")
    page.screenshot(path="/workspace/scratch/live-note-list.png")
    page.evaluate("() => { const n = S.notes.find(x => x.folderId === 'f-farm'); openEditor(n, false); }")
    page.wait_for_timeout(700)
    page.evaluate("document.querySelector('#edTools').scrollLeft = 0")
    page.screenshot(path="/workspace/scratch/live-note-editor.png")
    page.click("#edBack")
    page.wait_for_timeout(800)
    page.evaluate("() => { const n = S.notes.find(x => x.folderId === 'f-farm'); openPrint([n]); }")
    page.wait_for_timeout(900)
    check("인쇄 미리보기(실제 주소)", page.locator("#previewPaper .print-note").count() == 1)
    page.screenshot(path="/workspace/scratch/live-note-print.png")
    page.click("#printClose")
    page.wait_for_timeout(500)

    page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=20000)
    page.reload(wait_until="load")
    page.wait_for_timeout(800)
    ctx.set_offline(True)
    page.reload(wait_until="load")
    page.wait_for_timeout(1200)
    check("오프라인에서도 열림", page.locator(".brand-tx h1").inner_text() == "용우노트")
    check("오프라인 노트 유지", page.locator("#pinList .card-note, #noteList .card-note").count() >= 4,
          str(page.locator("#pinList .card-note, #noteList .card-note").count()))
    page.screenshot(path="/workspace/scratch/live-note-offline.png")
    ctx.set_offline(False)
    page.wait_for_timeout(500)

    errs = [m for m in logs if m[0] in ("error", "pageerror")]
    check("콘솔 오류 0건", len(errs) == 0, str(errs[:4]))

    print("\n[다른 앱이 그대로인지]")
    for url, name in [("https://travelsketch.github.io/customer-ledger/", "용우고객관리대장"),
                      ("https://travelsketch.github.io/customer-ledger/yongwoo-cashbook/", "용우입출금관리대장")]:
        p2 = ctx.new_page()
        p2.goto(url, wait_until="domcontentloaded")
        p2.wait_for_timeout(800)
        t = p2.title()
        check(f"{name} 정상", name in t, t)
        p2.close()

    ctx.close()
    b.close()

ok = sum(1 for r in results if r[0])
print(f"\n결과: {ok}/{len(results)} 통과")
