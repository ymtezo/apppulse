# AppPulse Goal

アプリ利用実績を本人が理解できる指標へ変換し、不要アプリの整理を、誤削除なく本人確認付きで支援する。

## 成功条件

- foreground時間・起動回数・recencyを端末別に集計できる。
- 低利用判定の期間と根拠を説明できる。
- uninstall候補を提示しても、明示確認なしには削除しない。
- system-critical appを削除対象から除外する。
- 実データなしのunit testでranking、期間filter、winget解析、安全guardを検証できる。

## 非目標

- ユーザー確認なしの自動uninstall。
- 利用履歴の無断外部送信。
- API keyや外部アカウントの発行。
