# アーキテクチャ

```text
Browser (HTML/CSS/ES modules)
  ├─ GET /api/stations            → Station directory
  ├─ GET /api/programs/{id}       → 任意の番組情報
  └─ GET /api/stream/{id}         → <audio> に MP3 bytes を供給
                                      │
FastAPI application                 │
  ├─ Station directory cache         │ bundled fallback + JCBA HTML refresh
  ├─ Program client ────────────────┤ HTTPS timetable API
  └─ Stream relay                    │
       ├─ GET select_stream          │ HTTPS session API
       └─ WSS listener               │ token TEXT + binary Ogg pages
             └─ ffmpeg               │ Ogg/Opus → low-latency MP3
                                      ▼
                             JCBA/Radimo service
```

## なぜ relay を置くか

JCBA WSS は `https://www.jcbasimul.com` Origin と専用 subprotocol を要求する。Web ブラウザでは `Origin` ヘッダーを任意に設定できず、WebSocket の binary stream をそのまま `<audio>` に渡す標準 API もない。バックエンドが session API と WSS を扱い、受信 Ogg/Opus を ffmpeg で低遅延 MP3 に変換して chunked HTTP response として渡す。これによりブラウザ／OS の Ogg live-stream 実装差を避け、`<audio>` の広く対応した連続再生を使う。なお、JCBA 側から受信する元音声は Ogg/Opus のままである。

## 状態遷移

```text
STOPPED → CONNECTING → BUFFERING → PLAYING
                 │          │          │
                 ▼          ▼          ▼
            UNAVAILABLE    ERROR  RECONNECTING ──→ CONNECTING
```

- `UNAVAILABLE`: select_stream が 404。自動ループしない。
- `RECONNECTING`: WSS の終了・受信 timeout。古い session を破棄し、session API を再実行する。
- stop／局変更時はブラウザ request をキャンセルし、relay generator の finally で WebSocket を close する。

## 境界

`JcbaClient` は外部 HTTP/WSS をカプセル化する。`StationDirectory` は起動時にローカル cache（初回のみ bundled fallback）を読み、明示 refresh 時に JCBA ページの埋め込み `stations` data を更新する。API routes はこれらの境界だけを呼ぶ。UI はアプリ API だけに依存する。これによりプロトコルと UI を別々にテストできる。
