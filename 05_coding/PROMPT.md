# 05 コーディング: AI プロンプト

## この工程の目的

詳細設計書を基に、**TDD（テスト駆動開発）で実際に動作するコード**を生成する工程です。
AI は詳細設計書の Pydantic スキーマ、サービスクラス設計、処理シーケンスから
**テストコードを先に生成し、次に実装コード**を生成します。

## AI への指示（プロンプト）

```
あなたは Python (FastAPI) のシニアエンジニアで、TDD（テスト駆動開発）の
実践経験が豊富です。

@detailed_design.md（詳細設計書）を基に、TDD の手順に従って
テストコードと実装コードを生成してください。

## 重要: TDD の実施手順

必ず以下の順番でコードを生成してください:

### Step 1: テストコードを先に書く（Red フェーズ）

tests/unit/test_inspection_service.py を最初に生成すること。
以下のテストケースを含めること:

#### 正常系テスト（2件）
1. 全検査項目が合格（PASS）するケース
   - 入力: lot_number="20260401-BP-001", 測定値=12.25（範囲: 12.00〜12.50）
   - 期待: result="PASS", 各 detail の judgment="PASS"

2. 1項目が不合格で全体も FAIL になるケース
   - 入力: 外径寸法=12.25（PASS）, 硬度=96.0（上限 95.0 を超過 → FAIL）
   - 期待: result="FAIL", 外径寸法は PASS, 硬度は FAIL

#### 異常系テスト（3件）
3. 存在しないロット番号 → NotFoundException が発生
   - 入力: lot_number="99999999-XX-999"
   - 期待: NotFoundException, detail に "99999999-XX-999" を含む

4. 同一ロット・同一工程の重複検査 → DuplicateException が発生
   - 入力: 1回目は成功、2回目は DuplicateException
   - 期待: DuplicateException

5. 存在しない検査基準ID → NotFoundException が発生
   - 入力: inspection_standard_id="nonexistent-id"
   - 期待: NotFoundException

#### 境界値テスト（6件）
6. 測定値 = 下限値（12.00）→ PASS
7. 測定値 = 上限値（12.50）→ PASS
8. 測定値 = 下限値 - 0.01（11.99）→ FAIL
9. 測定値 = 上限値 + 0.01（12.51）→ FAIL
10. 測定値 = 範囲の中央値（12.25）→ PASS
11. 上限値・下限値が None（外観検査等）→ PASS

#### テストコードのルール
- pytest を使用
- DB は SQLite のインメモリ DB（`sqlite:///:memory:`）
- @pytest.fixture でテストデータ（品目、検査基準、ロット）を共通化
- 各テストメソッドに Docstring で「何をテストしているか」を日本語で記述
- テストクラスを以下の 3 つに分類:
  - TestCreateInspectionSuccess（正常系）
  - TestCreateInspectionErrors（異常系）
  - TestJudgeBoundaryValues（境界値）

### Step 2: 実装コードを書く（Green フェーズ）

テストが通る最小限の実装コードを以下のファイルに生成:

1. app/core/config.py - 環境変数管理（pydantic-settings 使用）
2. app/core/exceptions.py - AppException, NotFoundException, DuplicateException
3. app/models/item.py - Item, InspectionStandard（SQLAlchemy 2.0）
4. app/models/lot.py - Lot
5. app/models/inspection.py - InspectionResult, InspectionDetail
6. app/models/defect.py - DefectRecord, QualityAlert, ShipmentDecision
7. app/schemas/inspection.py - InspectionCreate, InspectionResponse 等
8. app/schemas/lot.py - LotCreate, LotResponse
9. app/schemas/dashboard.py - DefectRateResponse, QualityAlertResponse
10. app/services/inspection_service.py - InspectionService
11. app/services/alert_service.py - AlertService
12. app/api/v1/inspections.py - 検査関連エンドポイント
13. app/api/v1/lots.py - ロット関連エンドポイント
14. app/db/session.py - DB セッション管理
15. app/main.py - FastAPI アプリケーション

### Step 3: リファクタリング（Refactor フェーズ）

実装後に以下を確認・修正:
- 重複コードの排除
- 命名の一貫性
- 不要なコメントの削除

## 実装ルール

- Python 3.14+ の型ヒント構文を使用（list[str], str | None 等）
- 全関数に型ヒント（引数と戻り値）を付与
- Google Style Docstring を public メソッドに記述
- SQLAlchemy 2.0 の新スタイル: select() + scalars() を使用
- Pydantic v2: BaseModel, Field, model_config を使用
- エラーハンドリング: 詳細設計書のエラーコードに準拠
- joinedload を使用して N+1 問題を防止
- UUID は uuid4() で生成し、文字列型で DB に保存

## やってはいけないこと

- テストコードなしに実装コードだけを生成しないこと（TDD 必須）
- except: pass（例外の握りつぶし）を書かないこと
- SQL 文字列を直接組み立てないこと（SQLAlchemy の ORM を使用）
- Controller 層（api/v1/）にビジネスロジックを書かないこと
- 型ヒントのない関数を書かないこと

## 品質チェックリスト（出力前に自己確認すること）

- [ ] テストコードが実装コードより先に生成されているか
- [ ] 正常系・異常系・境界値の全テストケースが含まれているか
- [ ] 全関数に型ヒントと Docstring があるか
- [ ] N+1 問題を防止する joinedload が使われているか
- [ ] エラーコードが詳細設計書と一致しているか
```

## 生成されるファイル一覧

```
app/
├── main.py
├── core/
│   ├── config.py
│   └── exceptions.py
├── models/
│   ├── item.py
│   ├── lot.py
│   ├── inspection.py
│   └── defect.py
├── schemas/
│   ├── inspection.py
│   ├── lot.py
│   └── dashboard.py
├── services/
│   ├── inspection_service.py
│   └── alert_service.py
├── db/
│   └── session.py
├── api/
│   └── v1/
│       ├── inspections.py
│       └── lots.py
└── tests/
    └── unit/
        └── test_inspection_service.py   ← TDD: このファイルを最初に生成
```

## AI 活用のポイント

| 観点 | 従来の方法 | AI 活用後 | 改善効果 |
|------|-----------|----------|---------|
| 所要時間 | エンジニアが数週間かけてコーディング | AIが設計書からコードを数分で生成 | **80%以上の時間削減** |
| テスト | テストコードは後回しになりがち | AIがテストコードを先に生成（TDD） | 品質向上 |
| 定型コード | ボイラープレートコードの手書き | 定型コード（CRUD等）をAIが自動生成 | 工数削減 |

## 人間の役割

1. **コードのレビュー**: AI 生成コードの品質・セキュリティをレビュー
2. **ビジネスロジックの検証**: 合否判定ロジック等が業務要件と合致するか確認
3. **エッジケースの追加実装**: AI が見落とすエッジケースを補完
4. **テストの実行**: `pytest --cov` で実際にテストを実行し、カバレッジ 80% 以上を確認
