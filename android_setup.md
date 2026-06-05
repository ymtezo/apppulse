# AppPulse Android セットアップガイド (Pixer / Gala)

## 方法A: Termux + Python（簡易版・すぐ使える）

### 1. Termuxをインストール
- F-Droid から Termux をインストール
  - Google Play版は古いのでF-Droid推奨

### 2. Termuxで環境構築
```bash
pkg update && pkg upgrade
pkg install python
pip install psutil

# OneDrive同期フォルダをTermuxからアクセスできるようにする
termux-setup-storage
```

### 3. AppPulseをコピー
```bash
# OneDriveからコピー、またはPC経由でコピー
cp -r /storage/emulated/0/OneDrive/AppPulse ~/apppulse
cd ~/apppulse
pip install -r requirements.txt
```

### 4. Android用トラッカーを使用
```bash
# Androidではプロセス監視の代わりにアプリ使用統計を使う
python android_tracker.py
```

### 5. Termux:Taskで週次実行
```bash
pkg install termux-api
# crontab で毎週土曜10:00に実行
crontab -e
# 以下を追加:
# 0 10 * * 6 cd ~/apppulse && python weekly_report.py
```

---

## 方法B: ネイティブAndroidアプリ（フル機能版・開発が必要）

### 技術スタック
- Kotlin + Jetpack Compose
- UsageStatsManager API（アプリ使用時間取得）
- Room (SQLite)
- WorkManager（週次バックグラウンドジョブ）
- Android通知チャンネル

### 必要な権限
- `PACKAGE_USAGE_STATS` — 設定 > セキュリティ > 使用状況へのアクセス で許可

### 制約
- Androidではアプリの直接アンインストールは不可
  → `Intent.ACTION_UNINSTALL_PACKAGE` でユーザーに確認画面を表示
- Play Store代替アプリは Intent でストアページを開く

---

## 方法C: Webダッシュボード（全デバイス統合・推奨）

全デバイス（REON, PETER, Pixer, Gala）のデータを
1つのWebダッシュボードで確認・管理できる。

### 構成
- バックエンド: Python (FastAPI) — PCで動作
- フロントエンド: HTML/JS — ブラウザからアクセス
- 各デバイスのデータをOneDrive or REST APIで集約
- Androidからはブラウザでアクセスするだけ

### メリット
- Android側にアプリ不要（ブラウザだけ）
- REON/PETERのデータも一覧表示
- レコメンド・削除操作はPC側で実行
