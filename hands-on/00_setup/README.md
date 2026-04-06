# Step 00: セットアップ

## 目的

Gemini CLI をインストールし、ハンズオンを進めるための環境を整えます。

---

## 1. Gemini CLI のインストール

```bash
npm install -g @google/gemini-cli
```

> **補足**: Gemini CLI は Google が提供するコマンドラインツールです。
> 最新のインストール手順は公式リポジトリを確認してください:
> https://github.com/google-gemini/gemini-cli

---

## 2. Python 環境の準備

Step 05（コーディング）でテストを実行するため、Python のパッケージもインストールしておきます。

```bash
pip install sqlalchemy pydantic pytest
```

---

## 3. 認証の設定

Gemini CLI を使用するには Google アカウントでの認証が必要です。

```bash
gemini
```

初回起動時に認証フローが開始されます。ブラウザが開くので、Google アカウントでログインしてください。

---

## 4. 動作確認

以下のコマンドで Gemini CLI が正しく動作するか確認します。

```bash
gemini -p "「Hello, World\!」と返してください。"
```

「Hello, World!」と返答があれば、セットアップ完了です。

---

## 5. Gemini CLI の基本操作

ハンズオンで使う Gemini CLI の基本操作を確認しておきましょう。

### 方法A: 対話モードで起動（推奨）

```bash
cd hands-on/01_requirements_analysis
gemini
```

対話モードでは、プロンプトを入力して Enter を押すと回答が返ります。
`@ファイル名` でファイルの内容を読み込ませることができます。
`/quit` で終了します。

```
# 対話モード中の例
> @rfp.md を分析してください
```

### 方法B: ワンショットで実行（非対話モード）

ファイルの内容を stdin で渡し、`-p` オプションでプロンプトを指定します。

```bash
cat rfp.md | gemini -p "このRFPを分析してください" -o text
```

> **本ハンズオンでは方法A（対話モード）を前提に手順を記載しています。**
> 方法B を使う場合は、プロンプト末尾の `@ファイル名` を省略し、
> 代わりに `cat ファイル名 | gemini -p "プロンプト"` の形式で実行してください。

### 成果物の保存方法

Gemini CLI の出力をファイルに保存する方法:

```bash
# 方法1: 対話モードで出力をコピー＆ペーストして保存
# → 出力を選択してコピーし、エディタに貼り付けて保存

# 方法2: ワンショット実行で直接ファイルに保存
cat rfp.md | gemini -p "プロンプト" -o text > ai_analysis.md
```

---

## 次のステップ

セットアップが完了したら、[Step 01: 要件分析](../01_requirements_analysis/README.md) に進んでください。
