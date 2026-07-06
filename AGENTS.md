# AppPulse Agent Instructions

- `D:\ControlTower\reference\global-agent-handoff-policy.md`を適用する。
- uninstallやファイル削除をテストで実行しない。mockまたは`confirmed=False`のguardだけを検証する。
- 実利用履歴、端末識別情報、DB、logをGitやhandoffへ含めない。
- API keyや外部accountを無断発行しない。
- mergeは原則`--no-ff`、subtree使用時は`--no-squash`とする。
- 最終応答前に中央とローカルのhandoffを更新する。
