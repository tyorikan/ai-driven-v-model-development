# Step 05: コーディング

## この工程の位置づけ

```
        詳細設計 ──────── 単体テスト
          │                  │
          >>> コーディング <<< ── コードレビュー
```

V字モデルの最下部、**実装工程**です。
詳細設計書を基に、**TDD（テスト駆動開発）でテストコードを先に書き、次に全層の実装コード**を生成します。
サービス層だけでなく、**API エンドポイント層・スキーマ・アプリケーションエントリポイント**も含む完全な実装を行います。

---

## やること

詳細設計書を基に、AI が自律的に以下を TDD の順序で生成・テスト実行・修正します:

1. **テストコード**（Red フェーズ）
2. **全層の実装コード**（Green フェーズ）-- サービス層 + API 層 + スキーマ
3. **テスト実行と修正**（自律的にグリーンになるまで繰り返す）

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

### 2. 必要なパッケージをインストール

```bash
pip install fastapi sqlalchemy pydantic pytest httpx
```

### 3. Gemini CLI を対話モードで起動

```bash
gemini
```

### 4. 以下のプロンプトを入力

> AI が自律的にファイル生成・テスト実行・修正を一連の作業として実行します。

````
あなたは Python (FastAPI) のシニアエンジニアで、TDD（テスト駆動開発）の
実践経験が豊富です。

以下の詳細設計書を基に、TDD の手順に従って全層の実装を行ってください。

## 以下の 3 つのフェーズを順番に自律的に実行してください

---

### Phase 1: コード生成と保存

以下のファイルを順番に生成し、それぞれ指定パスに保存してください。

#### Step 1: テストコード（最初に生成すること）

**ファイル: tests/test_attendance_service.py**

以下のテストケースを含む pytest テストファイルを生成:

##### 正常系テスト（TestCalculateDailySummarySuccess）
1. 固定時間制: 定時退勤（9:00〜18:00）→ 実働8h、残業0h、休憩1h
2. 固定時間制: 2時間残業（9:00〜20:00）→ 実働10h、法定外残業2h
3. 固定時間制: 深夜残業あり（9:00〜23:30）→ 深夜1.5h
4. フレックス制: 月次集計で残業計算（総実労働175h、所定労働日数20日 → 残業15h）

##### 異常系テスト（TestAttendanceErrors）
5. 退勤時刻が出勤時刻より前 → ValidationError
6. 同一日に2回出勤打刻 → DuplicateClockInError
7. 存在しない従業員ID → EmployeeNotFoundError

##### 境界値テスト（TestWorkingHoursBoundary）
8. ちょうど8時間勤務（9:00-18:00、休憩1h）→ 残業0h
9. 8時間1分勤務（9:00-18:01）→ 残業 > 0
10. ちょうど22:00退勤 → 深夜0h
11. 22:01退勤 → 深夜 > 0
12. 6時間ちょうど勤務（9:00-15:00）→ 休憩控除なし
13. 6時間超勤務（9:00-15:01）→ 休憩45分控除

#### Step 2: 実装コード（全層を生成すること）

以下のファイルを順番に生成:

1. **app/core/exceptions.py** - カスタム例外クラス群
   - 基底クラス `AttendanceError(Exception)` に `error_code: str`, `status_code: int` 属性を持たせる
   - `EmployeeNotFoundError(AttendanceError)`: error_code="EMPLOYEE_NOT_FOUND", status_code=404
   - `DuplicateClockInError(AttendanceError)`: error_code="DUPLICATE_CLOCK_IN", status_code=409
   - `ValidationError(AttendanceError)`: error_code="VALIDATION_ERROR", status_code=400
   - 各クラスの `__init__` で detail メッセージを受け取り `super().__init__(detail)` を呼ぶこと
   - **pass だけのクラスにしないこと**（API 層でステータスコード変換に使う）

2. **app/db/session.py** - DB セッション管理
   - `Base`（DeclarativeBase）
   - `get_db()` ジェネレータ（FastAPI の Depends 用）
   - `DATABASE_URL` 設定（環境変数 or デフォルト SQLite）

3. **app/models/employee.py** - Employee モデル（SQLAlchemy 2.0 Mapped[]）

4. **app/models/attendance.py** - AttendanceRecord, DailySummary モデル

5. **app/schemas/attendance.py** - Pydantic v2 スキーマ
   - `ClockInRequest`: employee_id (UUID), clock_in_time (datetime), location (str | None)
   - `ClockOutRequest`: employee_id (UUID), clock_out_time (datetime)
   - `DailySummaryRequest`: employee_id (UUID), work_date (date)
   - `DailySummaryResponse`: work_date, total_working_hours, overtime_hours, midnight_hours, break_hours
   - `AttendanceRecordResponse`: id, employee_id, type, recorded_at
   - `ErrorResponse`: error_code, detail
   - 全スキーマに `model_config = ConfigDict(from_attributes=True)` を設定

6. **app/services/attendance_service.py** - AttendanceService（勤怠計算ロジック）
   - clock_in / clock_out / calculate_daily_summary / calculate_flex_monthly_overtime
   - 勤務時間計算の実装ルール:
     - 実労働時間 = 退勤 - 出勤 - 休憩時間
     - 休憩時間の自動控除: 6時間以下→0分、6時間超〜8時間以下→45分、8時間超→60分
     - 法定外残業 = max(0, 実労働時間 - 8時間)
     - 深夜時間 = 22:00〜翌5:00 の勤務時間
     - フレックス残業 = max(0, 月の総実労働 - 所定労働日数 × 8)

7. **app/api/v1/attendance.py** - FastAPI ルーター（API エンドポイント層）
   - `POST /api/v1/attendance/clock-in` → 出勤打刻（201 Created）
   - `POST /api/v1/attendance/clock-out` → 退勤打刻（200 OK）
   - `POST /api/v1/attendance/daily-summary` → 日次集計取得（200 OK）
   - 各エンドポイントは:
     - Pydantic スキーマでリクエスト/レスポンスを型定義
     - AttendanceService を呼び出し（ビジネスロジックは API 層に書かない）
     - 例外を適切な HTTP レスポンスに変換

8. **app/main.py** - FastAPI アプリケーションエントリポイント
   - FastAPI インスタンスの作成（title, version 付き）
   - ルーターの登録
   - AttendanceError ハンドラの登録（例外の status_code, error_code をレスポンスに含める）
   - CORS ミドルウェアの設定

9. **tests/test_api_integration.py** - API 結合テスト
   - FastAPI の TestClient を使用
   - pytest fixtures でテスト用 DB（SQLite インメモリ）と dependency_overrides を設定
   - テストシナリオ:
     - 出勤打刻 → 退勤打刻 → 日次集計の一連フロー
     - 同日二重打刻 → 409 Conflict
     - 存在しない従業員 → 404 Not Found
     - 出勤せずに退勤 → 400 Bad Request

#### コード生成ルール

- Python 3.12+ の型ヒント構文（list[str], str | None 等）
- SQLAlchemy 2.0 の Mapped[] アノテーション
- Pydantic v2 の model_config = ConfigDict(from_attributes=True)
- pytest + SQLite インメモリ DB（sqlite:///:memory:）
- @pytest.fixture でテストデータ（従業員）を共通化
- 各テストに日本語 Docstring で「何をテストしているか」を記述
- 全関数に型ヒント

---

### Phase 2: テスト実行と自律修正

全ファイルを保存したら、以下のコマンドでテストを実行してください:

```bash
python -m pytest tests/ -v
```

テストが失敗した場合は:
1. エラーメッセージを分析する
2. **テストの期待値は正しい前提**で、実装コードを修正する
3. 修正したファイルを保存する
4. 再度テストを実行する

**全テストが PASSED になるまでこのサイクルを繰り返してください。**

---

### Phase 3: 完了報告

全テストが PASSED したら、以下の形式で完了報告を出力してください:

```
## 完了報告

### テスト結果
- 単体テスト: XX passed
- 結合テスト: XX passed
- 合計: XX passed, 0 failed

### 生成ファイル一覧
- tests/test_attendance_service.py（単体テスト XX件）
- tests/test_api_integration.py（結合テスト XX件）
- app/core/exceptions.py（カスタム例外 X クラス）
- app/db/session.py（DB セッション管理）
- app/models/employee.py（Employee モデル）
- app/models/attendance.py（AttendanceRecord, DailySummary モデル）
- app/schemas/attendance.py（Pydantic スキーマ X クラス）
- app/services/attendance_service.py（勤怠計算ロジック）
- app/api/v1/attendance.py（API エンドポイント X 本）
- app/main.py（FastAPI エントリポイント）

### 修正サマリー
（Phase 2 で修正した箇所があれば記載。なければ「修正なし」）

### API エンドポイント一覧
| メソッド | パス | 説明 |
|---------|------|------|
| POST | /api/v1/attendance/clock-in | 出勤打刻 |
| POST | /api/v1/attendance/clock-out | 退勤打刻 |
| POST | /api/v1/attendance/daily-summary | 日次集計 |
```

## やってはいけないこと

- テストコードなしに実装コードだけを生成しないこと
- except: pass（例外の握りつぶし）を書かないこと
- 例外クラスを pass だけで定義しないこと（error_code, status_code を必ず持たせる）
- 型ヒントのない関数を書かないこと
- API エンドポイント層にビジネスロジックを書かないこと（サービス層に委譲）
- スキーマファイルを空にしないこと（全 API の Request/Response を定義する）

@../04_detailed_design/detailed_design.md
````

---

## この工程で学ぶこと

| 学習ポイント | 説明 |
|------------|------|
| AI 駆動の TDD | テストを先に書き、テストが通る実装を書く。AI はこの順序を守れる |
| 全層の一括生成 | サービス層だけでなく API 層・スキーマ・エントリポイントまで一度に生成する |
| 自律的なデバッグ | テスト失敗時に AI 自身がエラーを分析・修正・再テストするサイクルを体験する |
| 境界値テストの重要性 | 8時間ちょうど、22:00ちょうどなど、境界値での動作を検証する |

---

## 次のステップ

AI の完了報告で全テストが PASSED していることを確認したら、[Step 06: コードレビュー](../06_code_review/README.md) に進んでください。
