# EP Tutoring Daily Sheet

선생님이 튜터링 요약을 작성 → 원장님에게 이메일 발송 → 원장님이 검토·수정 후
학부모(To)와 학생(Cc)에게 발송하는 2단계 흐름입니다.

## 앱 두 개

둘 다 Streamlit Community Cloud에서 돌아갑니다. 원장님 PC를 꺼도 동작합니다.

| 앱 | 누가 | 주소 |
|---|---|---|
| `app.py` | 선생님 | https://3rptsszzfugdsemkjhfugt.streamlit.app/ |
| `review_app.py` | 원장님 | https://rcxpbjjystx82ttljuybcb.streamlit.app/ |

`main` 브랜치에 푸시하면 두 앱 모두 자동으로 재배포됩니다.

로컬에서 확인할 때는:

```bash
streamlit run app.py
streamlit run review_app.py --server.port 8502
```

선생님이 Submit을 누르면 세 가지가 한 번에 일어납니다.

1. 리포트가 Reports 시트에 저장됩니다
2. 원장님 이메일(`RECEIVER_EMAIL`)로 알림이 갑니다
3. **학부모용 메일이 Gmail 임시보관함에 초안으로 만들어집니다** — 발송은 되지 않습니다

원장님은 Gmail에서 초안을 읽고 다듬어 직접 보내시면 됩니다. 검토 앱에서 수정한 뒤
보내는 방법도 그대로 쓸 수 있습니다.

## 최초 설정 (1회)

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 학생 명부 Google Sheet 만들기

새 스프레드시트를 만들고 **탭 이름을 `Students`** 로 바꾼 뒤, 1행에 아래 헤더를
그대로 입력하세요 (열 순서는 상관없고, 대소문자도 무관합니다).

| Student Name | Parent Name | Parent Email | Student Email | Active |
|---|---|---|---|---|
| Eunho Lee | Mrs. Lee | mom@example.com | eunho@example.com | |
| Jihu Park | Mr. Park | dad@example.com | jihu@example.com | |

- **필수**: `Student Name`, `Parent Email`
- **선택**: `Parent Name`(검토 화면에 참고용 표시), `Student Email`(Cc에 자동 입력),
  `Active`(비워두면 활성. `No`를 넣으면 검토 화면에 경고가 뜹니다 — 발송을 막지는 않습니다)
- 학부모 이메일이 두 개면 쉼표로 구분: `mom@x.com, dad@x.com`
- 선생님이 이름(`Eunho`)만 입력해도 성까지 있는 행(`Eunho Lee`)을 찾아줍니다.
  단, 같은 이름으로 시작하는 학생이 둘 이상이면 자동 매칭하지 않고 직접 입력하게 둡니다.

시트 주소가 `https://docs.google.com/spreadsheets/d/AAA111.../edit` 이라면
`AAA111...` 부분이 시트 ID입니다.

### 3. `.env` 설정

```
SENDER_EMAIL=andy.lee@eliteprep.com
SENDER_PASSWORD=<Gmail 앱 비밀번호>
RECEIVER_EMAIL=andy.lee@eliteprep.com

STUDENTS_SPREADSHEET_ID=<위에서 복사한 시트 ID>
```

### 4. 구글 최초 로그인 (1회)

검토 앱을 처음 실행하면 브라우저가 열립니다. **개인 계정
(andyeunholee@gmail.com)** 으로 로그인하세요 — eliteprep.com 업무 계정은 Workspace
관리자가 막아둡니다. 한 번 승인하면 `token_tutoring.json`이 저장되어 다음부터는
자동입니다.

시트는 로그인한 계정이 열 수 있어야 합니다. 개인 계정으로 시트를 만들거나,
그 계정에 시트를 공유해 주세요.

## 검토 앱 사용법

1. 왼쪽 사이드바에서 **Pending / Drafted / Sent / All** 선택
2. 상단에서 리포트 선택 (🟡 = 검토 대기, 📝 = Gmail 초안 생성됨, ✅ = 이 앱에서 발송 완료)
3. 왼쪽에서 항목별로 수정 → 오른쪽 **Preview**가 즉시 갱신됨
4. **To**(학부모)와 **Cc**(학생)는 Google Sheet에서 자동으로 채워짐 — 필요하면 수정
5. **📨 Send to parent** 클릭

앱을 열어둔 채로 선생님이 새 리포트를 제출하면, 15초 안에 사이드바에
**🔔 알림**과 **Load new reports** 버튼이 뜹니다. 편집 중이던 내용이 날아가지 않도록
목록 갱신은 버튼을 눌렀을 때만 일어납니다.

- **💾 Save edits**: 발송하지 않고 수정만 저장
- **⚙️ More**: 발송 완료 건을 다시 대기로 되돌리거나 삭제
- **🔄 Reload roster**: 시트를 수정한 뒤 눌러 새로 읽기 (캐시 5분)

## Streamlit Community Cloud 배포

집·학원 어디서든 열려면 앱을 클라우드에 올려야 합니다. 로컬에서만 쓸 거라면
이 절은 건너뛰세요.

### 준비물

| 항목 | 설명 |
|---|---|
| 서비스 계정 | 클라우드에는 브라우저가 없어서 구글 로그인 창을 띄울 수 없습니다. 사람 대신 인증할 서비스 계정이 필요합니다 |
| 시트 공유 | 서비스 계정은 자기만의 이메일(`...iam.gserviceaccount.com`)을 가집니다. **Students는 뷰어**, **Reports는 편집자**로 그 주소에 공유해야 합니다 |
| Reports 시트 | 리포트가 쌓일 곳. 클라우드는 재시작 시 파일이 지워져서 로컬 JSON을 쓸 수 없습니다 |

### 배포 순서

1. https://share.streamlit.io 에서 GitHub 계정으로 로그인
2. **New app** → 이 저장소 선택 → Main file path에 **`review_app.py`** 입력 → Deploy
3. 앱 화면 우측 하단 **Manage app** → **⋮** → **Settings** → **Secrets** 에 아래를 붙여넣고 저장

```toml
SENDER_EMAIL = "andy.lee@eliteprep.com"
SENDER_PASSWORD = "Gmail 앱 비밀번호"
RECEIVER_EMAIL = "andy.lee@eliteprep.com"
ADMIN_PASSWORD = "검토 앱 비밀번호"

STUDENTS_SPREADSHEET_ID = "명부 시트 ID"
REPORTS_SPREADSHEET_ID = "리포트 시트 ID"

[gcp_service_account]
# service_account.json 의 내용을 그대로 옮겨 적습니다.
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

`private_key` 는 줄바꿈이 `\n` 문자 그대로 들어가야 하고, 전체를 큰따옴표로 감싸야
합니다. JSON 파일에 있는 형태 그대로 복사하면 맞습니다.

4. 선생님 폼도 쓰려면 **New app** 을 한 번 더 눌러 Main file path만 **`app.py`** 로
   지정해 배포합니다. Secrets는 앱마다 따로 넣어야 합니다.

`ADMIN_PASSWORD` 가 없으면 검토 앱은 열리지 않고 오류만 표시합니다. 인터넷에
공개되는 순간 학부모 주소 전체가 노출되고 원장님 계정으로 메일이 나갈 수 있어서,
비워둔 채로는 뜨지 않도록 막아두었습니다.

## 학부모 메일 초안

초안은 **선생님이 제출하는 순간** 만들어집니다 ([app.py](app.py)). 수업이 끝나고
리포트가 올라오면 바로 Gmail 임시보관함에 들어가 있습니다. **아무것도 발송되지
않습니다.**

`daily_drafts.py` 는 그 자리에서 초안 만들기가 실패한 건을 나중에 따라잡기 위한
수동 보완 수단입니다. 예약 실행은 없습니다.

초안의 To/Cc는 명부에서 채웁니다. 이름이 명부와 매칭되지 않으면 **주소를 비운 채로**
초안을 만듭니다 — 엉뚱한 학부모에게 보내는 것보다 낫고, Gmail에서 주소만 넣으면
됩니다.

SMTP에는 초안이라는 개념이 없어서 [src/drafts.py](src/drafts.py)는 IMAP으로
임시보관함에 직접 넣습니다. 발송에 쓰는 앱 비밀번호를 그대로 쓰므로 추가 인증은
필요 없습니다.

초안이 만들어진 리포트는 상태가 `drafted` 가 되어 다음 날 다시 만들어지지 않고,
검토 앱의 **Drafted** 목록에서 볼 수 있습니다. Gmail에서 보내신 것을 이 시스템은
알 수 없으므로, 상태는 `drafted` 에서 멈춥니다.

GitHub Actions에서 돌아갑니다 (`.github/workflows/prepare-drafts.yml`).

### 필요한 GitHub Secrets

저장소 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 값 |
|---|---|
| `SENDER_EMAIL` | 보내는 Gmail 주소 (초안도 이 계정에 생깁니다) |
| `SENDER_PASSWORD` | Gmail 앱 비밀번호 |
| `RECEIVER_EMAIL` | 선생님 제출 알림을 받을 주소 |
| `REPORTS_SPREADSHEET_ID` | 리포트 시트 ID |
| `STUDENTS_SPREADSHEET_ID` | 명부 시트 ID |
| `GCP_SERVICE_ACCOUNT_JSON` | `service_account.json` **파일 내용 전체** |

### 따라잡기 실행

초안이 만들어지지 않은 채 남은 리포트가 있을 때만 필요합니다.

Actions 탭 → **Prepare parent drafts** → **Run workflow**.

로컬에서는:

```bash
python daily_drafts.py --dry-run   # 무엇을 만들지 보기만 함
python daily_drafts.py             # 실제로 초안 생성
```

## 리포트 미제출 독촉 (수업 종료 1시간 후)

캘린더의 `[TUT]` 수업이 끝나고 **60분이 지나도** 같은 날·같은 선생님·같은 학생의
리포트가 없으면, 담당 선생님께 영어로 이메일을 한 통 보냅니다. **수업당 한 번만**
보내고, 보낸 기록은 Reports 스프레드시트의 `Reminders` 탭에 남깁니다.

GitHub Actions가 **15분마다** 확인합니다 (`.github/workflows/remind-missing-reports.yml`).
GitHub 사정으로 몇 분 늦게 돌 수 있어서 실제로는 종료 60~75분 뒤에 도착합니다.

### 캘린더 형식

이벤트 제목이 이 형식이어야 인식됩니다. `[ CLS ]` 그룹 수업이나 메모는 무시합니다.

```
[TUT] Type: ONLINE, Teacher Name: Joseph teacher, Student Name: Zena, Subject: College Essay
canceled by student: [TUT] ...        ← 취소된 수업은 독촉하지 않습니다
```

### 선생님 이메일

Reports 스프레드시트의 **`Teachers` 탭**에서 읽습니다.

| Teacher Name (as in calendar) | Email | Active |
|---|---|---|
| Joseph | joseph@example.com | |

이름은 첫 단어만 비교하므로 캘린더의 `Joseph teacher` 와 폼의 `Joseph O'Hailey` 가
같은 사람으로 잡힙니다. 이메일이 비어 있으면 그 선생님은 건너뛰고 실행 로그에 남깁니다.

### 준비

1. 캘린더 `andy.lee@eliteprep.com` 을 서비스 계정 이메일에 공유 — **"모든 일정 세부정보 보기"**
2. `Teachers` 탭에 선생님 이메일 채우기
3. GitHub Secrets는 초안 워크플로와 같은 것을 씁니다. 추가할 것 없음

리포트와 수업을 맞추는 규칙: 날짜가 같고, 선생님 첫 단어가 같고, 학생 이름의 단어가 한쪽이
다른 쪽에 포함될 때. `Andrew` ↔ `Kyuheon (Andrew) Ahn` 은 잡히고, 오타(`Andrw`)는 못
잡아서 독촉이 한 번 더 갈 수 있습니다.

## 웹사이트에 바로가기 링크 걸기

```html
<a href="https://rcxpbjjystx82ttljuybcb.streamlit.app/" target="_blank" rel="noopener">튜터링 리포트 검토</a>
```

앱이 비공개로 설정돼 있으면, 링크를 누른 사람은 먼저 Streamlit 로그인 화면을 만납니다.
원장님 계정으로 로그인한 기기에서는 어디서든 열리고, 다른 사람은 여기서 막힙니다.
그 뒤에 `ADMIN_PASSWORD` 를 한 번 더 물어봅니다.

무료 플랜은 한동안 접속이 없으면 앱이 잠듭니다. 그 뒤 첫 접속은 깨어나느라 30초쯤
걸립니다.

## 파일 구조

```
app.py                 선생님 입력 폼
daily_drafts.py        놓친 초안 따라잡기 (Actions에서 수동 실행)
remind_missing_reports.py  수업 후 1시간 내 미제출 독촉 (Actions, 15분마다)
review_app.py          원장님 검토·발송 UI
config.py              경로 / .env / 구글 인증 설정
src/report.py          리포트 필드 정의와 이메일 HTML·텍스트 생성 (두 앱 공용)
src/store.py           제출 리포트 저장 + 발송 상태 (Reports Google Sheet)
src/mailer.py          SMTP 발송 (To/Cc)
src/drafts.py          IMAP으로 Gmail 임시보관함에 초안 저장
src/students.py        Google Sheet 학생 명부 읽기
src/teachers.py        Teachers 탭에서 선생님 이메일 읽기
src/calendar_events.py 캘린더의 [TUT] 수업 읽기
src/reminder_log.py    독촉 발송 기록 (Reminders 탭)
src/auth.py            구글 OAuth
test_logic.py          검증용 테스트 (python test_logic.py)
```

`credentials.json`, `token_tutoring.json`, `.env`, `pending_reports.json`은
git에 올라가지 않습니다.
