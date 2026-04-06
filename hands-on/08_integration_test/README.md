# Step 08: 結合テスト

## この工程の位置づけ

```
    要件定義 ────────────────────────── システムテスト
      │                                    │
      基本設計 ──────────────── >>> 結合テスト <<<
        │
        詳細設計 ──────── 単体テスト
```

基本設計で定義した **API エンドポイント間の連携**が正しく動作するかを検証します。
単体テストが「メソッド単位」の検証であるのに対し、結合テストは**「API を通じたシナリオ」**で検証します。

---

## やること

1. まず、Step 05 で作成したサービス層の上に **API エンドポイント層** を生成する
2. 次に、**API 結合テスト**を生成する
3. テストを実行して検証する

> **前提**: Step 05 で `app/services/attendance_service.py` が完成していること

---

## 手順

### 1. Step 05 のコーディングディレクトリに移動し、Gemini CLI を起動

```bash
cd hands-on/05_coding
gemini
```

### 2. まず、API エンドポイントと FastAPI アプリケーションを生成

> まだ API 層を作成していない場合、以下のプロンプトで生成してください。

````
以下の既存サービス層のコードを基に、FastAPI の API エンドポイントと
アプリケーションのエントリポイントを生成してください。

## 生成するファイル

### 1. app/main.py
FastAPI アプリケーションのエントリポイント:
- FastAPI インスタンスの作成
- ルーターの登録

### 2. app/api/v1/attendance.py
打刻・勤怠関連のエンドポイント:
- POST /api/v1/attendance/clock-in （出勤打刻）
- POST /api/v1/attendance/clock-out （退勤打刻）
- GET /api/v1/attendance/daily-summary （日次集計取得）

各エンドポイントは:
- Pydantic スキーマでリクエスト/レスポンスを定義
- AttendanceService を呼び出し
- 例外を適切な HTTP ステータスコードに変換
  - EmployeeNotFoundError → 404
  - DuplicateClockInError → 409
  - ValidationError → 400

### 3. app/db/session.py の更新
DB セッションの依存性注入（Depends）を追加:
- get_db() ジェネレータ
- Base は既存のものを維持

## 実装ルール
- SQLAlchemy 2.0 / Pydantic v2
- 全関数に型ヒント
- ビジネスロジックは既存の AttendanceService に委譲（API 層に書かない）

@app/services/attendance_service.py
@app/models/attendance.py
@app/models/employee.py
@app/schemas/attendance.py
@app/core/exceptions.py
@app/db/session.py
````

### 3. API ファイルを保存

生成されたファイルを以下に保存:
- `app/main.py`
- `app/api/v1/attendance.py`
- `app/db/session.py`（更新版）

### 4. 次に、結合テストを生成

````
以下の FastAPI アプリケーションに対して、
TestClient を使った API 結合テストを生成してください。

## 生成するファイル

tests/test_api_integration.py

## テストシナリオ

### シナリオ1: 出勤〜退勤〜日次集計（一連の打刻フロー）

1. POST /api/v1/attendance/clock-in で出勤打刻
   - リクエスト: employee_id, clock_in_time="2026-08-01T09:00:00"
   - 検証: status_code=201

2. POST /api/v1/attendance/clock-out で退勤打刻
   - リクエスト: employee_id, clock_out_time="2026-08-01T20:00:00"
   - 検証: status_code=200

3. GET /api/v1/attendance/daily-summary で日次集計を取得
   - 検証: working_hours=10.0, overtime_hours=2.0

4. 同日に再度出勤打刻 → 409 Conflict
   - 検証: status_code=409

### シナリオ2: エラーケース

5. 存在しない従業員で出勤打刻 → 404 Not Found
6. 出勤せずに退勤打刻 → 400 Bad Request

## テストコードのルール

- FastAPI の TestClient を使用
- pytest fixtures で以下を共通化:
  - テスト用 DB（SQLite インメモリ）
  - テスト用 FastAPI app（dependency_overrides で DB を差し替え）
  - テスト用従業員データ
- レスポンスの status_code と body の両方を検証

@app/main.py
@app/api/v1/attendance.py
@app/services/attendance_service.py
````

### 5. テストファイルを保存して実行

```bash
# httpx をインストール（TestClient の依存パッケージ）
pip install httpx

# 結合テスト実行
python -m pytest tests/test_api_integration.py -v
```

### 6. テストが失敗した場合

API 層の実装とテストの不整合は頻繁に起きます。
エラーメッセージを Gemini CLI に貼り付けて修正を依頼してください:

```
以下の結合テストが FAIL しています。
API のエンドポイント実装とテストの両方を確認し、修正してください:

（エラーメッセージを貼り付け）
```

---

## 期待される出力の例

```
tests/test_api_integration.py::TestAttendanceFlow::test_clock_in PASSED
tests/test_api_integration.py::TestAttendanceFlow::test_clock_out PASSED
tests/test_api_integration.py::TestAttendanceFlow::test_daily_summary PASSED
tests/test_api_integration.py::TestAttendanceFlow::test_duplicate_clock_in PASSED
tests/test_api_integration.py::TestAttendanceErrors::test_not_found PASSED
tests/test_api_integration.py::TestAttendanceErrors::test_clock_out_without_in PASSED

6 passed
```

---

## この工程で学ぶこと

| 学習ポイント | 説明 |
|------------|------|
| V字の対応関係 | 基本設計の API → 結合テストで検証、という対応が明確 |
| シナリオベースのテスト | 単一 API ではなく、API の連携（打刻→集計）を検証する |
| エラーレスポンスの検証 | 正常系だけでなく、404/409/400 のエラーケースも検証する |
| API 層の生成 | サービス層を先に作り、その上に API 層を被せるアーキテクチャ |

---

## 次のステップ

結合テストが完了したら、[Step 09: システムテスト](../09_system_test/README.md) に進んでください。
