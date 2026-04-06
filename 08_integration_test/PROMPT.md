# 08 結合テスト: AI プロンプト

## この工程の目的

基本設計で定義した **API エンドポイント間の連携が正しく動作するか**を検証する工程です。
AI は基本設計書の API 設計から、エンドポイント間の連携シナリオを自動生成します。

## V字モデルにおける位置づけ

```
基本設計 ←──── 対応 ────→ 結合テスト
  │                           │
  API設計                     API エンドポイントの連携テスト
  データフロー                 データの整合性テスト
  外部連携設計                 MES連携の結合テスト
```

**結合テストは基本設計書の API 設計・データフローを検証基準とします。**

## AI への指示（プロンプト）

````
あなたは FastAPI アプリケーションの結合テストに精通した
テストエンジニアです。FastAPI の TestClient を使ったテストの実装経験が
豊富です。

@basic_design.md の API 設計と @detailed_design.md のシーケンス図を基に、
結合テストのテストコードを生成してください。

## 作業手順（この順番でテストを設計すること）

1. 基本設計書の API エンドポイント一覧を読み、API 間の依存関係を把握する
2. 業務フロー（ロット登録 → 検査登録 → 結果取得 → アラート確認）を
   シナリオとして設計する
3. 各シナリオについて、API 呼び出しの順序とデータの受け渡しを明確にする
4. エラーケースのシナリオを設計する
5. FastAPI の TestClient を使ったテストコードを生成する

## テストシナリオ一覧（以下を全て実装すること）

### シナリオ1: 検査登録フロー（正常系） - TestInspectionRegistrationFlow

業務フロー: ロット登録 → 検査結果登録 → 検査結果取得

| Step | API | 入力データ | 検証内容 |
|------|-----|----------|---------|
| 1 | POST /api/v1/lots | lot_number="20260401-BP-001", item_id="BP-001", line_code="LINE-BP", quantity=100 | status_code=201, lot_number が返る |
| 2 | POST /api/v1/inspections | lot_number="20260401-BP-001", phase="IN_PROCESS", details=[{std_id, value=12.25}] | status_code=201, result="PASS" |
| 3 | GET /api/v1/inspections?lot_number=20260401-BP-001 | - | status_code=200, 1 件取得, lot_number 一致 |

### シナリオ2: エラーケース - TestErrorCases

| # | テスト名 | API | 入力 | 期待結果 |
|---|---------|-----|------|---------|
| 1 | test_inspection_for_nonexistent_lot | POST /inspections | lot_number="99999999-XX-999" | 404, error_code="LOT_NOT_FOUND" |
| 2 | test_invalid_lot_format | POST /inspections | lot_number="invalid-format" | 422（Pydantic バリデーション） |
| 3 | test_get_nonexistent_lot | GET /lots/99999999-XX-999 | - | 404 |

### シナリオ3: 不合格ケース - TestFailedInspection

| Step | API | 入力データ | 検証内容 |
|------|-----|----------|---------|
| 1 | POST /api/v1/lots | lot_number="20260401-BP-002" | 201 |
| 2 | POST /api/v1/inspections | measured_value=13.00（上限 12.50 超過） | 201, result="FAIL", detail.judgment="FAIL" |

## テストコードのルール

### テスト環境のセットアップ
```python
# SQLite インメモリ DB でアプリの DB を差し替え
engine = create_engine("sqlite:///:memory:")
TestSessionLocal = sessionmaker(bind=engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
```

### マスタデータのフィクスチャ
```python
@pytest.fixture(autouse=True)
def setup_db():
    """各テスト前に DB を初期化し、以下のマスタデータを投入:
    - 品目: BP-001（ブレーキパッド Type-A）
    - 検査基準: std-dim-001（外径寸法 12.00〜12.50mm）
    """
    Base.metadata.create_all(engine)
    # ... マスタ投入 ...
    yield
    Base.metadata.drop_all(engine)
```

### コーディングルール
- FastAPI の TestClient を使用（httpx ベース）
- 各テストメソッドに Docstring で「何をテストしているか」を日本語で記述
- API のレスポンスボディを JSON としてパースし、具体的な値を検証する
- status_code の検証を必ず最初に行う

## やってはいけないこと

- status_code だけ検証してレスポンスボディを検証しないこと
- テスト間でデータが依存する（順序依存する）テストを書かないこと
- autouse=True のフィクスチャで DB を初期化せず、テスト間でデータが残ること
- 実際の外部サービス（MES 等）に接続するテストを書かないこと

## 品質チェックリスト（出力前に自己確認すること）

- [ ] 3 つのシナリオ（正常系、エラー系、不合格系）が全て実装されているか
- [ ] 各テストで status_code とレスポンスボディの両方を検証しているか
- [ ] テスト間でデータが干渉しないよう、各テスト前に DB が初期化されているか
- [ ] 各テストに日本語の Docstring があるか

@basic_design.md
@detailed_design.md
@app/main.py
@app/api/v1/inspections.py
@app/api/v1/lots.py
````

## AI 活用のポイント

| 観点 | 従来の方法 | AI 活用後 | 改善効果 |
|------|-----------|----------|---------|
| 所要時間 | テスト設計者が業務フローからシナリオを手作業で作成 | AIがAPI設計からシナリオを自動生成 | **80%以上の時間削減** |
| テストデータ | テストデータの準備に時間がかかる | AIがテストデータも含めて生成 | 工数削減 |
| 網羅性 | API間の依存関係の見落としリスク | AIがシーケンス図からデータフローを解析 | 抜け漏れ防止 |

## 人間の役割

1. **業務シナリオの網羅性確認**: 実際の業務フローで発生しうるパターンの追加
2. **テスト環境の準備**: 本番に近い環境での結合テスト実行
3. **テスト実行**: `pytest tests/integration/ -v` で実行し、全件 PASS を確認
