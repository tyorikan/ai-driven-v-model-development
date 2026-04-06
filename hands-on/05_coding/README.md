# Step 05: コーディング

## この工程の位置づけ

```
        詳細設計 ──────── 単体テスト
          │                  │
          >>> コーディング <<< ── コードレビュー
```

V字モデルの最下部、**実装工程**です。
詳細設計書を基に、**TDD（テスト駆動開発）でテストコードを先に書き、次に実装コード**を生成します。

---

## やること

詳細設計書を基に、Gemini CLI で以下を TDD の順序で生成します:

1. **テストコード**（Red フェーズ）
2. **実装コード**（Green フェーズ）

---

## 手順

### 1. 作業ディレクトリに移動し、ディレクトリ構成を作成

```bash
cd hands-on/05_coding
mkdir -p tests app/{core,models,schemas,services,api/v1,db}
touch app/__init__.py app/core/__init__.py app/models/__init__.py \
      app/schemas/__init__.py app/services/__init__.py app/db/__init__.py \
      app/api/__init__.py app/api/v1/__init__.py tests/__init__.py
```

### 2. Gemini CLI を対話モードで起動

```bash
gemini
```

### 3. 以下のプロンプトを入力

> このプロンプトは1回でテストコードと実装コードの両方を生成します。
> 末尾の `@../04_detailed_design/detailed_design.md` で詳細設計書が読み込まれます。

````
あなたは Python (FastAPI) のシニアエンジニアで、TDD（テスト駆動開発）の
実践経験が豊富です。

以下の詳細設計書を基に、TDD の手順に従って
テストコードと実装コードを一度に全て生成してください。

## 重要: 生成順序と出力形式

各ファイルを以下の形式で区切って出力してください:

```
--- ファイルパス ---
（コード）
```

### Step 1: テストコード（tests/test_attendance_service.py）を最初に出力

以下のテストケースを含む pytest テストファイルを生成:

#### 正常系テスト（TestCalculateDailySummarySuccess）
1. 固定時間制: 定時退勤（9:00〜18:00）→ 実働8h、残業0h、休憩1h
2. 固定時間制: 2時間残業（9:00〜20:00）→ 実働10h、法定外残業2h
3. 固定時間制: 深夜残業あり（9:00〜23:30）→ 深夜1.5h
4. フレックス制: 月次集計で残業計算（総実労働175h、所定労働日数20日 → 残業15h）

#### 異常系テスト（TestAttendanceErrors）
5. 退勤時刻が出勤時刻より前 → ValidationError
6. 同一日に2回出勤打刻 → DuplicateClockInError
7. 存在しない従業員ID → EmployeeNotFoundError

#### 境界値テスト（TestWorkingHoursBoundary）
8. ちょうど8時間勤務（9:00-18:00、休憩1h）→ 残業0h
9. 8時間1分勤務（9:00-18:01）→ 残業 > 0
10. ちょうど22:00退勤 → 深夜0h
11. 22:01退勤 → 深夜 > 0
12. 6時間ちょうど勤務（9:00-15:00）→ 休憩控除なし
13. 6時間超勤務（9:00-15:01）→ 休憩45分控除

### Step 2: 実装コード（テストが全て通る実装）

以下のファイルを順番に出力:

1. app/core/exceptions.py - EmployeeNotFoundError, DuplicateClockInError, ValidationError
2. app/db/session.py - Base（DeclarativeBase）
3. app/models/employee.py - Employee モデル（SQLAlchemy 2.0 Mapped[]）
4. app/models/attendance.py - AttendanceRecord, DailySummary モデル
5. app/schemas/attendance.py - Pydantic v2 スキーマ
6. app/services/attendance_service.py - AttendanceService（勤怠計算ロジック）

## 勤務時間計算の実装ルール

1. 実労働時間 = 退勤 - 出勤 - 休憩時間
2. 休憩時間の自動控除:
   - 6時間以下: 0分
   - 6時間超〜8時間以下: 45分
   - 8時間超: 60分
3. 法定外残業 = max(0, 実労働時間 - 8時間)
4. 深夜時間 = 22:00〜翌5:00 の勤務時間
5. フレックス残業 = max(0, 月の総実労働 - 所定労働日数 × 8)

## コード生成ルール

- Python 3.12+ の型ヒント構文（list[str], str | None 等）
- SQLAlchemy 2.0 の Mapped[] アノテーション
- Pydantic v2 の model_config = ConfigDict(from_attributes=True)
- pytest + SQLite インメモリ DB（sqlite:///:memory:）
- @pytest.fixture でテストデータ（従業員）を共通化
- 各テストに日本語 Docstring で「何をテストしているか」を記述

## やってはいけないこと
- テストコードなしに実装コードだけを生成しないこと
- except: pass（例外の握りつぶし）を書かないこと
- 型ヒントのない関数を書かないこと

@../04_detailed_design/detailed_design.md
````

### 4. 生成結果をファイルに保存

Gemini CLI の出力から、各ファイルのコードをコピーして対応するパスに保存します。

```
保存先:
  tests/test_attendance_service.py  ← テストコード
  app/core/exceptions.py            ← カスタム例外
  app/db/session.py                 ← Base クラス
  app/models/employee.py            ← Employee モデル
  app/models/attendance.py          ← AttendanceRecord, DailySummary
  app/schemas/attendance.py         ← Pydantic スキーマ
  app/services/attendance_service.py ← メインのビジネスロジック
```

> **ヒント**: Gemini CLI の対話モードでは、出力が長い場合にスクロールが必要です。
> 各ファイルの区切り（`--- ファイルパス ---`）を目印にしてコピーしてください。

### 5. テスト実行

```bash
# テスト実行
python -m pytest tests/test_attendance_service.py -v
```

#### 期待される結果

```
tests/test_attendance_service.py::TestCalculateDailySummarySuccess::test_regular_work_8h PASSED
tests/test_attendance_service.py::TestCalculateDailySummarySuccess::test_overtime_2h PASSED
tests/test_attendance_service.py::TestCalculateDailySummarySuccess::test_midnight_overtime PASSED
tests/test_attendance_service.py::TestCalculateDailySummarySuccess::test_flex_monthly_summary PASSED
tests/test_attendance_service.py::TestAttendanceErrors::test_clock_out_before_clock_in PASSED
tests/test_attendance_service.py::TestAttendanceErrors::test_duplicate_clock_in PASSED
tests/test_attendance_service.py::TestAttendanceErrors::test_non_existent_employee PASSED
tests/test_attendance_service.py::TestWorkingHoursBoundary::test_exact_8h_work PASSED
tests/test_attendance_service.py::TestWorkingHoursBoundary::test_over_8h_1m PASSED
tests/test_attendance_service.py::TestWorkingHoursBoundary::test_exact_2200_clock_out PASSED
tests/test_attendance_service.py::TestWorkingHoursBoundary::test_after_2201_clock_out PASSED
tests/test_attendance_service.py::TestWorkingHoursBoundary::test_exact_6h_no_break PASSED
tests/test_attendance_service.py::TestWorkingHoursBoundary::test_over_6h_45m_break PASSED

13 passed
```

### 6. テストが失敗した場合

テストが FAIL する場合は、エラーメッセージを Gemini CLI に貼り付けて修正を依頼してください:

```
以下のテストが FAIL しています。テストの期待値は正しいので、
実装コードを修正してください:

（エラーメッセージを貼り付け）
```

> **ポイント**: 「テストの期待値は正しい」と明示することで、
> AI がテスト側を変更するのではなく実装側を修正するようになります。

---

## この工程で学ぶこと

| 学習ポイント | 説明 |
|------------|------|
| TDD の実践 | テストを先に書き、テストが通る実装を書く。AI はこの順序を守れる |
| 具体的なテストケースの指示 | 入力値と期待値を明示することで、AI が正確なテストを生成する |
| 境界値テストの重要性 | 8時間ちょうど、22:00ちょうどなど、境界値での動作を検証する |
| AI のエラーへの対応 | テスト失敗時にエラーメッセージを渡して修正させるワークフロー |

---

## 次のステップ

テストが全て PASS したら、[Step 06: コードレビュー](../06_code_review/README.md) に進んでください。
