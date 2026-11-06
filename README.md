# ai-dev-lab-public
AI multi-agent development experiment

## 概要・必要環境

CSVから同一日の作業時間を行ごとに計算するCLIです。Python 3.9以上で動作し、
標準ライブラリのみを使用します。追加インストールは不要です。

## CSV形式

UTF-8（BOM付きも可）で、1行目は列順固定の `task,start,end` です。
各値の前後空白とデータ部分の空行（空白だけの行を含む）は無視します。
作業名は必須で、時刻はゼロ埋めした `00:00`〜`23:59` を指定します。
終了時刻は開始時刻より後である必要があります。ヘッダのみのCSVはエラーです。
同名作業も行ごとに表示し、重なった時間も各行の所要時間をそのまま加算します。
日跨ぎ・複数日・タイムゾーン・同名作業の集約・CSV出力には対応しません。

## 実行例

```console
$ python worktime.py examples/sample.csv
Task  Start  End    Duration
設計    09:00  10:30  1h 30m
実装    10:45  12:00  1h 15m
レビュー  13:00  13:45  0h 45m
----------------------------
Total                3h 30m
```

正常時の終了コードは0です。入力エラーは標準エラーに表示し、終了コード1で終了します。
例えば2行目の開始時刻が `9:00` の場合:

```text
Error: line 2: invalid start time '9:00' (expected HH:MM)
```

ファイルが読めない場合も `Error: cannot read file ...` を表示します。
引数なしではusageを表示して終了コード2、`-h` ではヘルプを表示して終了コード0です。
CSV内のエラーには該当する物理行番号を付け、最初のエラーで停止します。

## テスト

```sh
python -m unittest discover -s tests -v
```
