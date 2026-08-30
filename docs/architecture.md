# アーキテクチャ

```text
Browser (HTML/CSS/ES modules)
  ├─ GET /api/stations            → Station directory
  ├─ GET /api/programs/{id}       → 任意の番組情報
  └─ GET /api/stream/{id}         → <audio> に Ogg/Opus bytes を供給
                                      │
FastAPI application                 │
  ├─ Station catalog (bundled)      │
  ├─ Program client ────────────────┤ HTTPS timetable API
  └─ Stream relay                    │
       ├─ GET select_stream          │ HTTPS session API
       └─ WSS listener               │ token TEXT + binary Ogg pages
                                      ▼
                             JCBA/Radimo service
```

## なぜ relay を置くか

JCBA WSS は `https://www.jcbasimul.com` Origin と専用 subprotocol を要求する。Web ブラウザでは `Origin` ヘッダーを任意に設定できず、WebSocket の binary stream をそのまま `<audio>` に渡す標準 API もない。バックエンドが session API と WSS を扱い、連結した Ogg pages を `audio/ogg; codecs=opus` の chunked HTTP response として渡すことで、ブラウザ標準の継続再生を使う。

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

`JcbaClient` は外部 HTTP/WSS をカプセル化する。API routes はこの client だけを呼ぶ。UI はアプリ API だけに依存する。これによりプロトコルと UI を別々にテストできる。
