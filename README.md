# EP Tutoring Daily Sheet

선생님이 튜터링 요약을 작성 → 원장님에게 이메일 발송 → 원장님이 검토·수정 후
학부모(To)와 학생(Cc)에게 발송하는 2단계 흐름입니다.

## 앱 두 개

| 앱 | 누가 | 실행 명령 |
|---|---|---|
| `app.py` | 선생님 | `streamlit run app.py` |
| `review_app.py` | 원장님 | `streamlit run review_app.py --server.port 8502` |

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

## 파일 구조

```
app.py                 선생님 입력 폼
review_app.py          원장님 검토·발송 UI
config.py              경로 / .env / 구글 인증 설정
src/report.py          리포트 필드 정의와 이메일 HTML·텍스트 생성 (두 앱 공용)
src/store.py           제출 리포트 저장 + 발송 상태 (pending_reports.json)
src/mailer.py          SMTP 발송 (To/Cc)
src/students.py        Google Sheet 학생 명부 읽기
src/auth.py            구글 OAuth
test_logic.py          검증용 테스트 (python test_logic.py)
```

`credentials.json`, `token_tutoring.json`, `.env`, `pending_reports.json`은
git에 올라가지 않습니다.
