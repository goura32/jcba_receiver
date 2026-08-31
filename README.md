# JCBA Receiver

JCBA インターネットサイマルラジオを、地域・局名検索、お気に入り、現在番組表示とともに受信する、ローカル実行の Web アプリです。

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)

## できること

- 公式 station ID を主キーにした局ブラウザ（検索・地域絞り込み）
- 再生／停止、音量、ミュート、お気に入り（ブラウザ localStorage）
- 任意の現在番組情報
- 配信停止・接続中・バッファリング・再生中を分けたステータス表示
- JCBA の Ogg/Opus WSS をローカル relay で受信し、ブラウザ互換の MP3 にリアルタイム変換
- WSS 切断時に新規 token/location を取得して 1, 2, 5 秒で再接続

## 動作要件

- Python 3.11 以上
- `ffmpeg`（`libmp3lame` を含むビルド）
- ネットワーク接続（JCBA / Radimo API と WSS に到達できること）

## 起動

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn jcba_receiver.main:app --host 127.0.0.1 --port 8017
```

ブラウザで http://127.0.0.1:8017 を開きます。`8017` が使用中の場合は空いているローカルポートに変更してください。

## 構成

```text
Browser UI ── /api/stream/{station_id} ── FastAPI relay ── JCBA WSS
                                                  │
                                         Ogg/Opus → ffmpeg → MP3
```

1. relay は `select_stream` を GET し、新しい `token` と `location` を取得する。
2. `listener.fmplapla.com` subprotocol と `https://www.jcbasimul.com` Origin で WSS 接続する。
3. token を TEXT message として一度送信し、受信した Ogg pages を ffmpeg に渡す。
4. ffmpeg の MP3 output を `audio/mpeg` HTTP response として `<audio>` へ流す。

token と location はキャッシュ・ログ・ブラウザへの公開を行いません。`select_stream` の 404 は「現在配信利用不可」として API 503 に変換します。局が恒久的に存在しないとは判断しません。

## 局データと制約

起動直後はローカルの station cache（初回のみ代表局 catalog）を表示し、バックグラウンドで JCBA トップページの埋め込み station data を更新します。station ID は局名から生成せず、常に公式 ID を使用します。番組表は提供局のみで、取得に失敗しても音声再生を止めません。詳細な既知事項と未確定事項は [jcba_receiver_technical_notes.md](jcba_receiver_technical_notes.md) を参照してください。

## テスト

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
node --check src/jcba_receiver/static/app.js
.venv/bin/python -m compileall -q src
```

テストは station catalog、session API の成功／404、API route、MP3 transcoder command を対象にしています。実サービス確認では `fmnanami` から WSS Ogg pages を受け、relay が `audio/mpeg` を返すことを確認してください。

## ドキュメント

- [要件定義](docs/requirements.md)
- [アーキテクチャ](docs/architecture.md)
- [UI 設計](docs/ui-design.md)
- [技術調査資料](jcba_receiver_technical_notes.md)

## 開発上の注意

このプロジェクトは受信技術の実装です。利用規約・配布条件・権利関係は [技術調査資料](jcba_receiver_technical_notes.md) の対象外であり、運用者が別途確認してください。
