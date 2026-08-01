# EP Tutoring Daily Sheet

선생님이 튜터링 요약을 작성 → 원장님에게 이메일 발송 → 원장님이 검토·수정 후
학부모(To)와 학생(Cc)에게 발송하는 2단계 흐름입니다.

## 앱 두 개

| 앱 | 누가 | 주소 |
|---|---|---|
| `app.py` | 선생님 | http://localhost:8501 |
| `review_app.py` | 원장님 | http://localhost:8502 |

**`start_apps.bat` 을 더블클릭하면 두 앱이 한 번에 뜹니다.** 최소화된 창 두 개가
남는데, 그 창을 닫으면 앱이 꺼집니다. 직접 실행하려면:

```bash
streamlit run app.py
streamlit run review_app.py --server.port 8502
```

선생님이 Submit을 누르면 리포트가 `pending_reports.json`에 "검토 대기"로 쌓이고,
동시에 원장님 이메일(`RECEIVER_EMAIL`)로 발송됩니다. 원장님은 검토 앱에서 그
리포트를 열어 항목별로 수정한 뒤 학부모에게 보냅니다. 보내고 나면 "발송 완료"로
표시되어 중복 발송을 막습니다.

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

1. 왼쪽 사이드바에서 **Pending / Sent / All** 선택
2. 상단에서 리포트 선택 (🟡 = 검토 대기, ✅ = 발송 완료)
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

## 웹사이트에 바로가기 링크 걸기

원장님 웹사이트에 이런 링크를 두면 검토 앱이 바로 열립니다.

```html
<a href="http://localhost:8502/" target="_blank" rel="noopener">튜터링 리포트 검토</a>
```

**이 링크는 앱이 실행 중인 그 PC에서만 동작합니다.** `localhost` 는 "지금 이 컴퓨터"를
뜻하므로, 다른 사람이 웹사이트에서 이 링크를 클릭하면 자기 컴퓨터의 8502 를 찾다가
실패합니다. 원장님 전용 바로가기로 쓰는 건 문제없지만, 남과 공유하는 링크로는
동작하지 않습니다.

링크를 누르기 전에 `start_apps.bat` 이 실행돼 있어야 합니다. PC를 켤 때마다 자동으로
띄우려면 `start_apps.bat` 의 바로가기를 시작프로그램 폴더에 넣으면 됩니다
(`Win+R` → `shell:startup`).

## 파일 구조

```
start_apps.bat         두 앱을 한 번에 실행
app.py                 선생님 입력 폼
review_app.py          원장님 검토·발송 UI
config.py              경로 / .env / 구글 인증 설정
src/report.py          리포트 필드 정의와 이메일 HTML·텍스트 생성 (두 앱 공용)
src/store.py           제출 리포트 저장 + 발송 상태 (Reports Google Sheet)
src/mailer.py          SMTP 발송 (To/Cc)
src/students.py        Google Sheet 학생 명부 읽기
src/auth.py            구글 OAuth
test_logic.py          검증용 테스트 (python test_logic.py)
```

`credentials.json`, `token_tutoring.json`, `.env`, `pending_reports.json`은
git에 올라가지 않습니다.
