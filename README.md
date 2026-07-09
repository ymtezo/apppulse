# AppPulse

Windowsと接続したAndroid端末のアプリ利用状況を収集・保存・分析し、利用頻度の低いアプリと代替候補を提示するPythonツールです。

## 機能

- process foreground時間・起動回数・最終利用日時の集計
- SQLiteによる端末別履歴保存
- wingetとregistryからのinstalled app inventory
- 低利用・未利用アプリと代替候補の提示
- 週次report、通知、tray/dashboard
- Android Debug Bridgeを使う利用状況取得

## 安全設計

- uninstallは呼び出し側が`confirmed=True`を明示しない限り実行しない。
- Windowsの重要アプリはblocklistで保護する。
- 実行前に候補と根拠を表示し、削除結果を記録する。
- API keyは不要であり、無断で外部サービスへ利用履歴を送らない。

目的は[GOAL.md](GOAL.md)、現在地は[project state](system/project-state.json)を参照してください。

## 検証

```powershell
python -m unittest discover -s tests -v
python -m compileall -q .
```

## Project Tracking

- Current agent-ready issue: [[agent-task] Establish safe core tests and a reproducible Windows development baseline.](https://github.com/ymtezo/apppulse/issues/1)
- Local state: `system/project-state.json`
- Local handoff: `system/handoff.md`


