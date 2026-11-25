# 용우일정표

일간·주간·월간·연간이 한 번에 연동되는 연간일정표 웹앱(PWA)입니다.
음력과 한국 공휴일을 표시하고, 메모·사진·파일을 붙여 두고, A4로 인쇄하고,
구글 드라이브로 PC와 안드로이드폰의 일정을 자동으로 맞출 수 있습니다.

- 주소: <https://travelsketch.github.io/customer-ledger/yongwoo-schedule/>
- 같은 저장소의 다른 앱: 루트(용우고객관리대장) · `yongwoo-cashbook/` · `yongwoo-note/`

## 무엇을 할 수 있나

| 기능 | 내용 |
| --- | --- |
| 네 가지 일정표 | 상단 탭으로 **일간 · 주간 · 월간 · 연간**을 바로 바꿉니다. 어느 뷰에서 저장하든 같은 일정 데이터를 보므로 모든 뷰에 즉시 나타납니다. |
| 월간 | 달력 칸마다 양력 날짜 + 음력(`음 10.17`, 초하루·보름 강조) + 공휴일 이름 + 일정 칩. 날짜를 누르면 아래(PC는 오른쪽)에 그 날 일정과 `+ 추가`가 나옵니다. |
| 주간 | 일~토 7일 카드. 날짜마다 양력·음력·공휴일과 일정·메모·첨부 미리보기, `＋ 추가` 버튼. |
| 일간 | 그 날의 큰 양력·음력 헤더와 일정 카드 전체 내용(메모, 사진 썸네일, 파일 칩). |
| 연간 | 12개월 미니 달력을 한눈에. 일정이 있는 날은 색 점과 건수, 오늘·일요일 강조. 날짜를 누르면 그 날 일정 확인·추가, 월 이름을 누르면 월간으로 이동. |
| 메모형 일정 | 제목 + 여러 줄 메모 + 색상 태그, 종일 또는 시작~끝 시간, 여러 날 일정. |
| 사진·파일 | `📷 사진 촬영`(후면 카메라), `🖼️ 사진 첨부`, `📎 파일 첨부`(PDF 등 일반 파일). 사진은 긴 변 1600px·JPEG 80%로 자동 압축해 IndexedDB에 저장하고, 미리보기·크게 보기·내려받기·삭제가 됩니다. |
| 인쇄 | 지금 보는 뷰 그대로 A4 인쇄 미리보기(사진·메모 포함 여부 선택). |
| 백업 | 일정·사진·파일 전체를 JSON 파일 하나로 내려받고 복원합니다. |
| 검색 | 제목·메모·날짜·음력·공휴일·첨부 파일명으로 찾습니다. |
| PC·폰 동기화 | `☁️ 구글 드라이브 연결`을 기기마다 한 번 누르면 이후 저장·수정·삭제가 자동으로 오갑니다(앱 전용 공간, 내 드라이브 목록에는 보이지 않음). |

## 음력·공휴일

- 음력은 **한국천문연구원(KASI) 월력요항 표**를 앱 안에 넣어 계산합니다(1900~2050년).
  브라우저 내장 중국력과 한국 음력이 하루 어긋나는 해가 있어, 한국 기준 표를 그대로 씁니다.
  (예: 2026-10-11 = 음 9.1 — 중국력으로는 음 9.2, 2026-11-25 = 음 10.17)
- 공휴일은 양력 고정 공휴일 + 음력 공휴일(설날·추석 연휴, 부처님오신날) + **대체공휴일 규칙**
  (연휴가 토·일과 겹치거나 공휴일끼리 겹치면 다음 첫 평일)으로 계산합니다.
- 선거일은 확인된 날만 넣었습니다(2024-04-10, 2025-06-03, 2026-06-03). 정부가 따로 정하는
  임시공휴일은 자동 계산 대상이 아닙니다.

## 자료가 어디에 저장되나

- 일정: 브라우저 `localStorage` (`yongwooSchedule.events.v1`)
- 사진·파일: `IndexedDB` (`yongwoo-schedule` 의 `attachments`)
- 드라이브를 연결하면: 내 구글 드라이브의 **앱 전용 공간(appDataFolder)** 에 `yongwoo-schedule-sync.json`
  한 파일로 저장(한 개 8MB·합계 30MB까지). 기기별로 한 번 승인하면 됩니다.
- 병합 기준: 일정은 `updatedAt`, 삭제는 `deletedAt`(tombstone) — 양쪽에서 고친 내용이 섞여도
  최신 것으로 맞춰집니다.

## 파일

```
index.html              앱 전체(외부 CDN 없음, 빌드 결과물)
manifest.webmanifest    PWA 이름·아이콘·테마
sw.js                   서비스 워커(오프라인 열기)
icon.svg / icon-192.png / icon-512.png / icon-512-maskable.png
build.py                index.html 조립 스크립트
lunar-table.txt         음력 표(KASI, 1900~2050)
src/                    화면·코드 원본(app.css, app.html, core/store/render/editor/ui.js)
test/                   검증 스크립트와 음력 정답 자료
preview-mobile.png      휴대폰(412x915) 월간 화면
preview-yearly.png      PC(1280) 연간 화면 — 12개월 한눈에
preview-day.png / preview-week.png / preview-pc.png / preview-print.png
```

화면 캡처의 일정은 모두 **가상의 예시**입니다(실제 고객 정보 없음).

## 고치고 다시 올리기

```bash
python3 apps/yongwoo-schedule/build.py            # src → index.html
LD_LIBRARY_PATH=/workspace/scratch/chromedeps/root/usr/lib/x86_64-linux-gnu \
  python3 apps/yongwoo-schedule/test/ui-test.py   # 화면·동작 자동 검증
python3 apps/yongwoo-schedule/test/check-lunar.py # 음력·공휴일 대조
bash deploy/yongwoo-schedule-deploy.sh            # main·gh-pages 두 브랜치에 배포
```

`test/ui-test.py` 는 412×915(안드로이드폰)과 1280×800(PC)에서 네 뷰 전환·연동, 음력 정확성,
메모 입력·수정·삭제, 사진 자동 압축, PDF 첨부, 인쇄, 백업·복원, 드라이브 동기화(모의 서버),
서비스 워커, 콘솔 오류 0건을 확인합니다.
