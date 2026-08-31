# 要件定義

## 目的

JCBA インターネットサイマルラジオを、局検索・お気に入り・番組情報・安定したライブ再生で利用できるローカル Web アプリとして提供する。

## 利用者機能

- 地域・キーワードで局を探す
- 局を選び、再生／停止、音量変更、ミュートを操作する
- お気に入りをブラウザに保存する
- 現在の番組情報（提供局のみ）を表示する
- 接続中、バッファリング、再生中、配信停止、再接続中、エラーを明示する
- 配信停止の局を「局が存在しない」と断定せず、再試行できるようにする

## 技術要件

- stream session は `GET /api/v1/select_stream` の都度新しい `token` と `location` を使用する。
- WSS は `listener.fmplapla.com` を subprotocol とし、接続直後に token を TEXT 送信する。
- バックエンドは WSS の Ogg/Opus binary frame を受信し、ffmpeg で MP3 HTTP ストリームに変換してブラウザへ中継する。これにより Origin 制約とブラウザごとの Ogg live-stream 互換性を避ける。
- `select_stream` の 404 は `UNAVAILABLE` として HTTP 503 で表し、UI は再生不能な一時状態として提示する。
- WSS 切断時は 1, 2, 5 秒のバックオフで、常に session API から再取得して再接続する。
- station directory と番組情報は音声再生から独立し、番組表の失敗は再生を妨げない。

## 非機能要件

- モバイル幅でも操作できるレスポンシブ UI。
- token をレスポンス、ログ、ブラウザへ出力しない。
- 公開ネットワーク依存箇所を抽象化し、単体テストではモック transport を使用できる。
- WCAG を意識し、明確なコントラスト、キーボード操作、ARIA ラベルを備える。

## 受入条件

1. `fmnanami` など選択可能な局を UI から再生でき、audio 要素の source がアプリの stream endpoint になる。
2. `rinsaikanto` など API 404 の局で、配信停止メッセージと再試行導線が表示される。
3. 検索・地域絞り込み・お気に入り・音量操作がブラウザで機能する。
4. unit test と browser E2E test が成功する。
5. README に起動、アーキテクチャ、制約、テスト手順が記載される。
