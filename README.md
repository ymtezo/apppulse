# AppPulse

使用頻度の低いアプリを検出し、代替アプリを提案する使用状況トラッカー。
Android アプリと、Windows から ADB 経由で扱う Python ツールの2本立て。

| ディレクトリ | 内容 |
|---|---|
| `app/` ほか | **Android アプリ**(Kotlin / Compose / Room / WorkManager)。以下の説明はこちら |
| [`python-tool/`](python-tool/) | **Windows 側の Python ツール**。ADB で接続した端末の利用状況を SQLite に蓄積し、低利用アプリと代替候補を提示する |

以前は `ymtezo/apppulse`(private / Python)と `ymtezo/apppulse-android`(public / Kotlin)に
分かれていた。同じ製品の両輪なのに公開範囲も履歴も別々だったため、
2026-08-20 にここへ**履歴ごと**統合し、全体を public にした。
統合前に Python 側の全履歴50ブロブを走査し、鍵・トークン・`.env` の混入が
無いことを確認している(`.github` の `secrets.*` は参照式であり値ではない)。

---

## Android アプリ

Android アプリ使用状況トラッカー。使用頻度の低いアプリを検出し、代替アプリを提案する。

## 機能

- **使用統計取得** — UsageStatsManager で過去7日間のアプリ使用時間を集計
- **インストール済みアプリスキャン** — システムアプリとユーザーアプリを区別
- **週次レポート** — WorkManager で毎週土曜10:00に自動実行、Android通知で結果表示
- **代替アプリ提案** — 19アプリに対するプライバシー重視・オープンソースの代替案を提示
- **削除支援** — 使用頻度が低いアプリの削除を提案、見送り回数に応じた段階的な警告

## アーキテクチャ

```
com.apppulse/
├── AppPulseApplication.kt      # Application — WorkManager初期化
├── MainActivity.kt             # Compose エントリポイント
├── PermissionActivity.kt       # 使用統計アクセス権限設定
├── data/
│   ├── db/
│   │   ├── Entities.kt         # Room エンティティ (4テーブル)
│   │   ├── AppDatabase.kt      # Room Database (singleton)
│   │   └── AppDao.kt           # DAO (CRUD + Flow)
│   └── repository/
│       └── AppRepository.kt    # Repository パターン
├── tracker/
│   └── UsageTracker.kt         # UsageStatsManager + PackageManager
├── recommender/
│   └── Alternatives.kt         # 代替アプリDB (19アプリ)
├── worker/
│   └── WeeklyReportWorker.kt   # WorkManager CoroutineWorker
└── ui/
    ├── screens/
    │   ├── DashboardScreen.kt  # Compose UI (3タブ)
    │   └── DashboardViewModel.kt
    └── theme/
        └── Theme.kt            # Material You + Catppuccin Mocha
```

## 技術スタック

| 分類 | ライブラリ |
|---|---|
| UI | Jetpack Compose + Material 3 |
| DB | Room + KSP |
| 非同期 | Kotlin Coroutines + Flow |
| バックグラウンド | WorkManager |
| ライフサイクル | ViewModel + Lifecycle |

## データベーステーブル

| テーブル | 用途 |
|---|---|
| `usage_stats` | アプリ使用統計（package, 使用秒数, 起動回数） |
| `installed_apps` | インストール済みアプリ一覧 |
| `deletion_log` | アンインストール実行ログ（成功/失敗） |
| `uninstall_rejections` | 削除見送りログ（段階的警告の根拠） |

## 必要な権限

| 権限 | 用途 |
|---|---|
| `PACKAGE_USAGE_STATS` | アプリ使用統計の取得（設定画面で手動許可が必要） |
| `POST_NOTIFICATIONS` | 週次レポート通知（Android 13+） |
| `QUERY_ALL_PACKAGES` | インストール済みアプリ一覧の取得 |
| `RECEIVE_BOOT_COMPLETED` | 端末再起動後のWorker再登録 |

## ビルド

```bash
# デバッグビルド
./gradlew assembleDebug

# APK は app/build/outputs/apk/debug/ に出力
```

**要件:**
- Android SDK (compileSdk 35)
- JDK 17
- minSdk 26 (Android 8.0+)

## Windows版

`D:\apppulse\` に Python (winotify) ベースの Windows 版あり。同じコンセプトでデスクトップ向けに実装。
