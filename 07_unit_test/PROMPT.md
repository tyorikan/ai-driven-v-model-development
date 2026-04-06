# 07 単体テスト: AI プロンプト

## この工程の目的

詳細設計書に基づき、**サービスクラスの各メソッドが仕様通りに動作するか**を検証する工程です。
AI は詳細設計書の処理フロー・エラーケースからテストケースを自動生成します。

## V字モデルにおける位置づけ

```
詳細設計 ←──── 対応 ────→ 単体テスト
  │                           │
  クラス・メソッド設計         各メソッドの正常系・異常系テスト
  処理フロー                  境界値テスト
  エラーハンドリング設計       エラーケーステスト
```

**単体テストは詳細設計書の処理フローを検証基準とします。**

## AI への指示（プロンプト）

````
あなたは Python テストエンジニアです。pytest を使った単体テストの設計と
実装に精通しています。境界値分析、同値分割、デシジョンテーブルの
テスト技法を理解しています。

@detailed_design.md の詳細設計と @app/services/inspection_service.py の
実装コードを基に、pytest の単体テストコードを生成してください。

## 作業手順（この順番でテストを設計すること）

1. 詳細設計書のサービスクラス処理フローを読み、テスト対象メソッドを特定する
2. 各メソッドについて、正常系 → 異常系 → 境界値 の順でテストケースを設計する
3. テストデータ（フィクスチャ）を設計する
4. pytest コードを生成する

## テスト対象メソッド

1. InspectionService.create_inspection()
2. InspectionService._judge()（static method）
3. AlertService.check_and_trigger_alert()

## テストケース一覧（以下を全て実装すること）

### InspectionService.create_inspection() のテスト

#### 正常系（TestCreateInspectionSuccess クラス）
| # | テスト名 | 入力 | 期待結果 |
|---|---------|------|---------|
| 1 | test_all_pass | 全測定値が範囲内（外径=12.25, 硬度=88.0） | result="PASS", 全detail.judgment="PASS" |
| 2 | test_one_fail_makes_overall_fail | 外径=12.25（範囲内）, 硬度=96.0（上限95.0超過） | result="FAIL", 外径=PASS, 硬度=FAIL |

#### 異常系（TestCreateInspectionErrors クラス）
| # | テスト名 | 入力 | 期待結果 |
|---|---------|------|---------|
| 3 | test_lot_not_found | lot_number="99999999-XX-999" | NotFoundException, detail に lot_number 含む |
| 4 | test_duplicate_inspection | 同一ロット・同一工程を2回登録 | 2回目で DuplicateException |
| 5 | test_standard_not_found | inspection_standard_id="nonexistent-id" | NotFoundException |

### InspectionService._judge() のテスト

#### 境界値（TestJudgeBoundaryValues クラス）
検査基準: lower_limit=12.00, upper_limit=12.50 の場合

| # | テスト名 | 入力 measured_value | 期待結果 | テスト技法 |
|---|---------|-------------------|---------|-----------|
| 6 | test_exact_lower_limit_is_pass | 12.00 | "PASS" | 境界値（下限ON） |
| 7 | test_exact_upper_limit_is_pass | 12.50 | "PASS" | 境界値（上限ON） |
| 8 | test_just_below_lower_limit_is_fail | 11.99 | "FAIL" | 境界値（下限OFF） |
| 9 | test_just_above_upper_limit_is_fail | 12.51 | "FAIL" | 境界値（上限OFF） |
| 10 | test_middle_value_is_pass | 12.25 | "PASS" | 同値分割（中央値） |
| 11 | test_none_limits_is_pass | 1（上下限None） | "PASS" | 外観検査パターン |

## テストコードのルール

### フィクスチャ設計
```python
@pytest.fixture()
def db_session() -> Session:
    """テスト用のインメモリ SQLite セッションを生成する。"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()

@pytest.fixture()
def sample_data(db_session: Session) -> dict:
    """以下のテストデータを投入:
    - 品目: BP-001（ブレーキパッド Type-A）
    - 検査基準: 外径寸法（12.00〜12.50mm）, 硬度（80〜95 HRC）
    - ロット: 20260401-BP-001（LINE-BP, 数量100）
    """
```

### コーディングルール
- 各テストメソッドに Docstring で「何をテストしているか」を日本語で記述
- assert 文には意味のあるメッセージを含めること（可能な場合）
- 1 テスト 1 assert を原則とする（関連する複数の assert は許容）
- テストクラスで論理的にグループ化すること

## やってはいけないこと

- テストデータをテストメソッド内でハードコードせず、フィクスチャを使うこと
- モック（unittest.mock）は使わないこと（実際の SQLite DB でテストする）
- テスト名を test_1, test_2 のような無意味な名前にしないこと
- Docstring なしのテストメソッドを書かないこと
- テストケース一覧の 11 件を漏らさないこと

## 品質チェックリスト（出力前に自己確認すること）

- [ ] 上記テストケース一覧の 11 件が全て実装されているか
- [ ] 各テストに日本語の Docstring があるか
- [ ] フィクスチャが共通化されているか（テスト間でデータ投入コードが重複していないか）
- [ ] 境界値テストで「ON」と「OFF」の両方をテストしているか
- [ ] 異常系テストで期待する例外クラスと例外メッセージを検証しているか

@detailed_design.md
@app/services/inspection_service.py
````

## AI 活用のポイント

| 観点 | 従来の方法 | AI 活用後 | 改善効果 |
|------|-----------|----------|---------|
| 所要時間 | テスト設計書を作成してからテストコードを書く | AIが設計書からテストコードを直接生成 | **80%以上の時間削減** |
| 境界値分析 | 人間が手作業で境界値を洗い出す | AIが上限値・下限値の境界値テストを自動生成 | 漏れ防止 |
| 工数比率 | テストコード作成は実装の1.5倍の工数 | 実装と同等の時間でテストコードを生成 | テスト工数半減 |

## 人間の役割

1. **テストケースの網羅性確認**: AI が見落とすケース（業務特有のエッジケース）を追加
2. **テスト実行**: `pytest -v` でテストを実行し、全件 PASS を確認
3. **カバレッジ確認**: `pytest --cov=app --cov-report=term-missing` で 80% 以上を確認
