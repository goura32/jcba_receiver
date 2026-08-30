# JCBAインターネットサイマルラジオ受信アプリ 技術調査資料

- 改訂日: 2026-08-31
- 状態: 実ストリーム検証反映版
- 対象: JCBAインターネットサイマルラジオ受信アプリの実装
- 範囲: 通信、局情報、音声形式、再接続、番組情報、実測結果等の技術事項のみ

---

## 1. 目的

JCBAインターネットサイマルラジオの公開Webプレイヤーと同等の受信機能を、独自アプリケーションとして実装するために必要な技術情報を整理する。

本資料では以下を対象とする。

- station IDと局一覧
- ストリーム取得API
- WebSocket接続
- セッショントークン
- Ogg / Opus音声
- 実ストリームのフレーミング
- `burst` の挙動
- バッファリング
- 切断・再接続
- 配信停止状態
- 番組表API
- 局一覧キャッシュ
- 推奨データ構造
- 推奨実装構成
- 実測済み事項と残る未確定事項

利用規約、配布条件、法務、権利関係等は扱わない。

---

# 2. 結論

JCBA受信アプリは以下の3層に分離して実装する。

```text
Station Directory
  station_id / 局名 / 地域
        │
        ├─────────────────┐
        ↓                 ↓
Program Metadata      Audio Streaming
番組表・現在番組       select_stream
任意機能               ↓
                    token + location
                         ↓
                        WSS
                         ↓
                     Ogg Opus
                         ↓
                        PCM
```

2026-08-31時点の調査・実測から、次を実装仕様として採用できる。

1. 通常局の音声受信方式は共通化できる。
2. `station_id` を局の主キーとして扱う。
3. ストリーム開始時は `select_stream` APIへGETする。
4. APIから毎回 `token` と `location` を取得する。
5. `location` は動的に割り当てられるためキャッシュしない。
6. WebSocket subprotocolは `listener.fmplapla.com`。
7. WebSocket接続後、`token` をTEXT messageとして1回送信する。
8. 音声はWebSocket BINARY messageで受信する。
9. 実測3局では、1 BINARY messageが1個の完全なOgg pageに対応した。
10. 音声形式はOgg Opus、48 kHz、2ch stereo。
11. `burst=5` は接続開始時に約5秒分の過去音声を先行送出する設定と強く推定できる。
12. 現在配信していないstationでは、`select_stream` 自体がHTTP 404になる場合がある。
13. 番組表は任意機能であり、音声受信可否とは分離する。
14. 再接続時は古いtoken/locationを使わず、`select_stream` からやり直す。

---

# 3. 実測対象

今回、以下を実ストリームで確認した。

| station_id | 種別 | 結果 |
|---|---|---|
| `fmnanami` | 通常局 | 受信成功 |
| `fmichinomiya` | i-wave / 番組情報表示あり | 受信成功 |
| `fmmahoroba` | 放送時間限定案内のある局 | 受信成功 |
| `rinsaikanto` | 臨時災害放送局訓練 | `select_stream` がHTTP 404 |

このうちFMななみについては詳細JSONレポートを採取し、HTTP、WebSocket、Ogg、Opus、ffprobeまで確認した。

---

# 4. 全体通信シーケンス

通常の受信シーケンス:

```text
station_id
    ↓
HTTPS GET
/api/v1/select_stream
    ↓
JSON
  code
  token
  location
    ↓
WSS connection
    ↓
TEXT(token)
    ↓
BINARY(Ogg page)
BINARY(Ogg page)
BINARY(Ogg page)
    ↓
Ogg Opus decoder
    ↓
PCM
    ↓
audio output
```

重要:

```text
JCBA Webページを埋め込む必要はない。
```

ネイティブアプリから直接APIとWSSへ接続できる。

---

# 5. station ID

`station_id` はJCBA内部の局識別子。

例:

| 局 | station_id |
|---|---|
| FMななみ | `fmnanami` |
| i-wave | `fmichinomiya` |
| RADIO SANQ | `radiosanq` |
| S-Wave | `swave` |
| FM新宮 | `fmshingu` |
| FMまほろば | `fmmahoroba` |
| 関東臨時災害放送局訓練 | `rinsaikanto` |

station IDは局名から機械的に生成できない。

例:

```text
LCV FM       → lovefm
RADIO LUSH   → fmyaizu
FM845        → kyotoribingufm
FMふくやま   → bingo
```

したがって以下は禁止。

```python
station_id = normalize(station_name)
```

アプリ内の永続主キーは必ず公式station IDとする。

---

# 6. 局ごとのプロトコル差

実測した3通常局:

```text
fmnanami
fmichinomiya
fmmahoroba
```

では、以下が一致した。

```text
HTTP method       GET
channel           0
quality           high
burst             5
WebSocket         WSS
subprotocol       listener.fmplapla.com
container         Ogg
codec             Opus
sample rate       48000 Hz
channels          2
channel layout    stereo
mapping family    0
```

したがって現時点では、局別の受信処理分岐は不要。

```python
if station_id == "...":
    # 局専用処理
```

のようなコードは作らない。

---

# 7. ストリーム取得API

エンドポイント:

```text
https://api.radimo.smen.biz/api/v1/select_stream
```

推奨リクエスト:

```http
GET /api/v1/select_stream
    ?station=<station_id>
    &channel=0
    &quality=high
    &burst=5
```

FMななみ実測例:

```text
https://api.radimo.smen.biz/api/v1/select_stream
?station=fmnanami
&channel=0
&quality=high
&burst=5
```

実測では:

```text
HTTP 200
Content-Type: application/json
```

となった。

---

# 8. GET / POST

FMななみではGETで正常受信できた。

```text
GET → HTTP 200
```

したがって新規実装ではGETを標準とする。

一方、第三者実装ではPOSTの利用例も存在する。

`rinsaikanto` では:

```text
GET  → HTTP 404
POST → HTTP 404
```

となったため、このケースの404はHTTP methodの違いによるものではない。

推奨:

```python
GETを標準とする。
POST fallbackは通常クライアントには不要。
```

検証ツールでのみfallbackを残してよい。

---

# 9. `select_stream` レスポンス

FMななみ実測ではJSONに以下のキーが存在した。

```json
{
  "code": 200,
  "location": "wss://...",
  "token": "..."
}
```

実測response JSON keys:

```text
code
location
token
```

`token` はログ等へ平文保存しない。

---

# 10. HTTPレスポンスヘッダー

FMななみ実測では以下が確認された。

```text
Content-Type: application/json
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
Strict-Transport-Security: ...
```

APIはブラウザからの利用も考慮された構成になっている。

ネイティブアプリではCORS制約はない。

---

# 11. WebSocket location

FMななみ実測:

```text
wss://os1305.radimo.smen.biz:443/socket?burst=5
```

分解:

```text
scheme = wss
host   = os1305.radimo.smen.biz
port   = 443
path   = /socket
query  = burst=5
```

他局:

```text
fmichinomiya → os1302.radimo.smen.biz
fmmahoroba   → os1305.radimo.smen.biz
```

したがって:

```text
station_id → 固定サーバー
```

ではない。

毎回:

```text
select_stream
 ↓
location
 ↓
connect
```

とする。

locationはキャッシュしない。

---

# 12. token / locationの寿命

正確なTTLは未確認。

ただし実装はTTLを知る必要がない。

推奨:

```text
再生開始
 ↓
select_stream
 ↓
新token/location
 ↓
WSS

切断
 ↓
古いtoken/location破棄
 ↓
select_streamから再実行
```

token/locationを再利用しないことで、TTLへ依存しない。

---

# 13. WebSocket handshake

WebSocketはTLS上。

```text
wss://
```

要求subprotocol:

```text
listener.fmplapla.com
```

FMななみ実測ではサーバーから:

```http
Sec-WebSocket-Protocol: listener.fmplapla.com
```

が返り、実際にネゴシエーションされた。

したがってこのsubprotocolは実装上の正式要素として扱う。

推奨Origin:

```text
https://www.jcbasimul.com
```

---

# 14. WebSocketサーバー

FMななみ実測のhandshake response:

```text
Server: fmpp 1.7.1
```

Ogg metadataにも:

```text
ENCODER=fmpp 1.7.1
```

が確認された。

したがって配信系では `fmpp 1.7.1` が使用されている。

---

# 15. WebSocket認証

接続成功後:

```text
tokenをWebSocket TEXT messageとして送信
```

する。

```text
WSS CONNECT
    ↓
CONNECTED
    ↓
TEXT(token)
    ↓
BINARY audio
```

FMななみ実測では、token送信後:

```text
約16.2 ms
```

で最初のBINARY audioを受信した。

---

# 16. TEXT / PING / PONG

FMななみ8秒実測:

```text
TEXT受信     0
PING         0
PONG         0
CLOSE frame  0
```

i-wave、FMまほろばでも:

```text
PING 0
PONG 0
```

だった。

短時間接続ではJCBA固有heartbeatは確認されていない。

推奨:

```text
独自heartbeatは実装しない。
WebSocket library標準のkeepalive/ping-pongへ任せる。
```

長時間接続でのserver ping intervalは未確認。

---

# 17. WebSocket BINARY framing

FMななみ8秒実測:

```text
binary_frame_count                 46
frames_starting_with_OggS          46
frames_with_exactly_one_OggS       46
frames_with_multiple_OggS           0
frames_with_no_OggS                 0
complete Ogg pages                 46
remaining bytes                     0
resync skipped bytes                0
```

i-wave:

```text
binary frames 47
Ogg pages     47
OggS start    47
```

FMまほろば:

```text
binary frames 47
Ogg pages     47
OggS start    47
```

3局すべてで:

```text
1 WebSocket BINARY message
        =
1 complete Ogg page
```

となった。

これは現行実装の強い実測結果である。

ただしサーバー内部仕様として永続保証されているとは限らないため、受信側では最低限:

```python
if not frame.startswith(b"OggS"):
    fallback_buffer.extend(frame)
```

のようなフォールバック余地を残す。

---

# 18. Ogg

Ogg page header:

```text
Offset  Size  内容
0       4     "OggS"
4       1     version
5       1     header_type
6       8     granule_position
14      4     bitstream_serial_number
18      4     page_sequence_number
22      4     checksum
26      1     page_segments
27      N     segment_table
```

FMななみの最初の2 page:

```text
page 0
  sequence     0
  header_type  2
  length       47

page 1
  sequence     1
  length       79
```

それぞれ:

```text
OpusHead
OpusTags
```

に相当する。

---

# 19. Ogg page sequenceの注意

FMななみでは:

```text
OpusHead page sequence = 0
OpusTags page sequence = 1
```

の後、最初のlive audio pageは:

```text
sequence = 59768683
```

へジャンプした。

つまり概念的に:

```text
接続時
 ↓
クライアント向けOpusHead
 ↓
クライアント向けOpusTags
 ↓
既存ライブストリームの現在位置付近
```

となっている。

したがって:

```text
Ogg sequence番号が0から連続する
```

という検証を入れてはいけない。

---

# 20. 音声形式

3局の実測で以下が一致した。

```text
Container               Ogg
Codec                   Opus
Opus version            1
Sample rate             48000 Hz
Channel count           2
Channel layout          stereo
Pre-skip                0
Output gain             0
Channel mapping family  0
```

FMななみはffprobeでも:

```text
codec_name     opus
sample_rate    48000
channels       2
channel_layout stereo
format_name    ogg
probe_score    100
```

となった。

したがって通常局の現行JCBA配信は:

```text
Ogg Opus / 48 kHz / stereo
```

として実装可能。

---

# 21. Opus parameterの扱い

現在3局で一致していても、アプリ側で以下を固定値にしすぎない。

```text
sample rate
channels
mapping family
```

decoderはOpusHeadを読む。

推奨:

```text
通常時:
  48 kHz stereo

実装:
  OpusHeadから自動判定
```

FFmpeg/PyAV利用時は自動解析へ任せる。

---

# 22. `burst`

API parameter:

```text
burst=5
```

WebSocket locationにも:

```text
/socket?burst=5
```

として引き継がれる。

FMななみ実測では、壁時計約8.166秒の接続で46 Ogg pageを受信。

先頭2 pageはOpusHead/OpusTagsなので、音声pageは約44。

音声pageのgranule差から1 pageは概ね:

```text
約0.28〜0.32秒
```

程度。

したがって44 pageは概算:

```text
約13.2秒分の音声
```

一方、実接続時間:

```text
約8.2秒
```

差:

```text
約5秒
```

指定:

```text
burst=5
```

と一致する。

---

# 23. `burst=5` の現時点の解釈

実測から最も整合する解釈:

```text
burst=N
 ↓
接続開始時に約N秒分の過去音声を高速に先行送出
 ↓
ライブ位置へ追いつく
 ↓
以後通常速度
```

これはJCBAプレイヤーの:

```text
2秒
5秒
30秒
60秒
```

というバッファ選択とも整合する。

したがって現時点では:

```text
burstの単位は秒と強く推定
```

できる。

ただし `burst=2/30/60` の実測比較はまだ行っていないため、内部仕様として完全確定とはしない。

---

# 24. bitrate

FMななみ:

```text
8.166秒の壁時計時間
108,917 bytes
見かけのtransport bitrate ≈ 106.7 kbps
```

i-wave:

```text
約107.57 kbps
```

FMまほろば:

```text
約106.61 kbps
```

ただしこれは `burst=5` の先行送出を含むため、通常の音声bitrateではない。

FMななみでは約13秒分の音声を約8秒で取得したと推定できるため:

```text
実音声時間基準 ≈ 66 kbps
```

程度になる。

JCBAの通信量目安とも整合し:

```text
約64〜67 kbps級のOgg Opus
```

と推定できる。

---

# 25. ffprobe durationの注意

ライブOggを数秒切り出してffprobeへ渡すと、非常に大きなdurationが表示される。

FMななみでは:

```text
duration ≈ 18,031,764秒
```

となったが、実際の取得時間は約8秒。

原因:

```text
live streamのgranule_positionが
ストリーム開始時点からの大きな累積値
```

だからである。

したがって録音時間の計算に:

```text
ffprobe format.duration
```

をそのまま使ってはいけない。

推奨:

```text
実録音時間 = wall clock
```

または:

```text
last granule - first audio granule
```

から算出する。

---

# 26. 配信停止station

`rinsaikanto` 実測:

```text
GET select_stream
→ HTTP 404

POST select_stream
→ HTTP 404
```

response JSON keys:

```text
code
error
```

token/locationは発行されなかった。

したがって:

```text
局一覧に存在する
       ≠
現在ストリームセッションが存在する
```

ことが実測で確定した。

---

# 27. `rinsaikanto` 404の解釈

現時点では以下を区別できていない。

```text
station_id自体が現在無効
```

なのか:

```text
stationは存在するが現在配信ストリームがない
```

なのか。

probeはエラー時JSONのキーのみ保存し、`error` の実値を出力していなかったため、正確な意味は未確認。

アプリでは404を:

```text
現在配信利用不可
```

として扱う。

UI上で:

```text
局が存在しません
```

と断定しない。

---

# 28. Stream Availability

Station情報に:

```python
is_online: bool
```

を永続属性として持たせない。

正しいモデル:

```text
Station Directory
  stationが掲載されている
        │
        └──────────┐
                   ↓
             select_stream
                   ↓
              200 / 404
                   ↓
          現在のavailability
```

つまりavailabilityはその瞬間のAPI結果。

---

# 29. 放送時間限定局

FMまほろばは放送時間限定案内のある局だが、今回の試験時には:

```text
select_stream成功
WSS成功
Ogg Opus受信成功
```

した。

したがって:

```text
公式に案内された放送時間外
    ↓
必ずselect_stream 404
```

とは限らない。

ストリームが常時維持され、放送時間外には無音・告知等を流す可能性もある。

アプリでは自然文の放送時間を解析して受信可否を決めず:

```text
select_stream / WSSの実結果
```

を真実とする。

---

# 30. ストリーム状態

推奨:

```python
from enum import Enum


class StreamState(Enum):
    STOPPED = "停止"
    CONNECTING = "接続中"
    BUFFERING = "バッファリング中"
    PLAYING = "再生中"
    RECONNECTING = "再接続中"
    UNAVAILABLE = "配信停止"
    ERROR = "エラー"
```

意味:

```text
UNAVAILABLE
  select_stream 404等
  現在ストリームが取得できない正常系

ERROR
  JSON破損
  protocol violation
  decoder failure
  想定外例外等
```

---

# 31. 再接続

再生中のネットワーク切断:

```text
PLAYING
 ↓
connection lost
 ↓
session破棄
 ↓
backoff
 ↓
select_stream
 ↓
new token/location
 ↓
WSS
```

推奨backoff:

```text
1秒
2秒
5秒
10秒
30秒
60秒
```

最大60秒程度。

一方、開始時から:

```text
select_stream → 404
```

の場合は頻繁に再試行しない。

例:

```text
UNAVAILABLE
 ↓
60秒以上後に再確認
```

またはユーザー操作時のみ再確認する。

---

# 32. 切断処理

停止操作:

```text
1. audio output停止
2. WebSocket close
3. close完了待機
4. session破棄
5. 次の局へ接続
```

`close()` 直後に新しいWebSocketを開始しない。

推奨状態遷移:

```text
PLAYING
 ↓
CLOSING
 ↓
CLOSED
 ↓
FETCH_SESSION
 ↓
CONNECTING
```

---

# 33. スリープ・ネットワーク変更

以下では既存WSSを破棄する。

```text
OS sleep
wake/resume
Wi-Fi変更
Ethernet/Wi-Fi切替
VPN変更
IPアドレス変更
network unavailable → available
```

復帰後:

```text
select_stream
 ↓
new session
 ↓
new WSS
```

とする。

---

# 34. 局一覧

局一覧をアプリへ固定埋め込みするだけでは不十分。

理由:

```text
新局追加
局名変更
廃局
station_id追加
地域表示変更
臨時局
```

station ID一覧はJCBAトップページの埋め込みデータから取得できる。

概念:

```text
GET https://www.jcbasimul.com/
 ↓
HTML
 ↓
embedded serialized data
 ↓
station list
 ↓
station_id / name / region
```

内部JSONの具体的な固定パスへ過度に依存しない。

---

# 35. Stationモデル

推奨:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    prefecture: str | None = None
    region: str | None = None
```

主キー:

```text
Station.id
```

局名・都道府県は表示情報。

---

# 36. Station Repository

```python
class StationRepository:

    async def refresh(self) -> list[Station]:
        ...

    async def get_all(self) -> list[Station]:
        ...

    async def get(self, station_id: str) -> Station | None:
        ...
```

構成:

```text
StationRepository
 ├─ remote fetch
 ├─ parser
 └─ local cache
```

---

# 37. 局一覧キャッシュ

推奨起動処理:

```text
起動
 ↓
local stations.json
 ↓
即UI表示
 ↓
必要ならremote refresh
 ↓
差分保存
```

キャッシュ更新間隔目安:

```text
6〜24時間
```

station list更新失敗でも再生可能な既知局は利用できるようにする。

---

# 38. 番組表API

確認されているendpoint:

```text
https://api.radimo.smen.biz/api/v1/mobile/timetables?station=<station_id>
```

確認されているフィールド:

```text
id
start
end
title
url
performer
detail
sub_title
mail_address
```

ただし全局が番組情報を提供するわけではない。

---

# 39. Program Metadataはoptional

重要:

```text
番組表が取れない
        ≠
ストリームが再生できない
```

依存関係:

```text
            Station
           /       \
          /         \
 Program Metadata    Audio Streaming
     optional          independent
```

番組情報がない局でも音声再生を継続する。

---

# 40. Programモデル

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Program:
    id: str | None
    station_id: str
    start_at: datetime
    end_at: datetime
    title: str
    performer: str | None = None
    description: str | None = None
    url: str | None = None
```

```python
async def get_current_program(
    station_id: str,
) -> Program | None:
    ...
```

`None` は正常ケース。

---

# 41. Streamモデル

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamOptions:
    channel: int = 0
    quality: str = "high"
    burst: int = 5


@dataclass(frozen=True)
class StreamSession:
    token: str
    location: str
```

API:

```python
async def create_stream_session(
    station_id: str,
    options: StreamOptions = StreamOptions(),
) -> StreamSession:
    ...
```

---

# 42. 最小受信処理

概念コード:

```python
async def play_station(station_id: str):

    session = await select_stream(
        station=station_id,
        channel=0,
        quality="high",
        burst=5,
    )

    async with connect(
        session.location,
        origin="https://www.jcbasimul.com",
        subprotocols=["listener.fmplapla.com"],
    ) as ws:

        await ws.send(session.token)

        async for message in ws:
            if not isinstance(message, bytes):
                continue

            if message.startswith(b"OggS"):
                decoder.feed(message)
            else:
                fallback_stream_parser.feed(message)
```

---

# 43. デコード方式

推奨:

```text
WebSocket
 ↓
Ogg Opus
 ↓
FFmpeg / PyAV
 ↓
PCM
 ↓
audio output
```

最初からOgg parser + libopusを全面自作する必要はない。

FFmpeg/PyAVの利点:

```text
Ogg parsing
OpusHead処理
OpusTags処理
codec negotiation
sample format conversion
```

を既存実装へ任せられる。

---

# 44. バッファ構成

```text
WebSocket
 ↓
compressed buffer
 ↓
decoder
 ↓
PCM ring buffer
 ↓
audio callback
```

`burst` とローカルPCM bufferは別概念として扱う。

```text
burst:
  サーバー側の接続開始時先行送出

PCM buffer:
  クライアント側の再生安定化
```

PCM buffer初期値:

```text
2〜5秒程度
```

ただし低遅延を重視する場合は短縮する。

---

# 45. HTTP / WebSocket timeout

推奨初期値:

```text
HTTP connect timeout    5秒
HTTP read timeout      10秒
WSS connect timeout    10秒
audio receive timeout 10〜15秒
```

WebSocketが接続中でも一定時間audio BINARYが来なければ再接続対象とする。

---

# 46. エラー分類

```python
class JcbaError(Exception):
    pass


class StationNotFoundError(JcbaError):
    pass


class StreamUnavailableError(JcbaError):
    pass


class StreamSessionError(JcbaError):
    pass


class WebSocketConnectionError(JcbaError):
    pass


class ProtocolError(JcbaError):
    pass


class AudioDecodeError(JcbaError):
    pass
```

推奨マッピング:

```text
select_stream 404
  → StreamUnavailableError

select_stream 5xx
  → StreamSessionError

WSS接続失敗
  → WebSocketConnectionError

OggSでない想定外データ
  → ProtocolErrorまたはfallback parser

decode failure
  → AudioDecodeError
```

---

# 47. デバッグログ

最低限記録:

```text
station_id
select_stream method
HTTP status
response code
location host
WebSocket handshake status
negotiated subprotocol
token send status
first audio latency
binary frame count
binary bytes
Ogg page count
OpusHead
decoder state
PCM buffer duration
audio underrun
last audio receive
reconnect count
```

tokenはマスクする。

---

# 48. 実測検証ツール

検証用スクリプトでは以下を採取する。

```text
select_stream HTTP status
response JSON keys
location
WSS handshake headers
subprotocol
BINARY frame count
BINARY frame size
OggS判定
Ogg page parsing
OpusHead
OpusTags
PING/PONG
ffprobe
transport bitrate
```

検証ファイル:

```text
<station>.ogg
<station>_report.json
```

---

# 49. 開発環境上のLibreSSL警告

macOSの古いPython環境では:

```text
NotOpenSSLWarning:
urllib3 v2 only supports OpenSSL 1.1.1+
ssl module is compiled with LibreSSL 2.8.3
```

が表示される場合がある。

今回:

```text
HTTPS成功
WSS成功
音声受信成功
```

しているため、JCBAプロトコル上の問題ではない。

開発環境としてはHomebrew等の新しいPython/OpenSSLを推奨する。

確認:

```bash
python3 -c 'import ssl; print(ssl.OPENSSL_VERSION)'
```

---

# 50. 推奨ディレクトリ構成

```text
jcba_receiver/
├── pyproject.toml
├── README.md
├── src/
│   └── jcba_receiver/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── station/
│       │   ├── model.py
│       │   ├── repository.py
│       │   ├── parser.py
│       │   └── cache.py
│       │
│       ├── program/
│       │   ├── model.py
│       │   └── api.py
│       │
│       ├── stream/
│       │   ├── session_api.py
│       │   ├── websocket.py
│       │   ├── protocol.py
│       │   └── reconnect.py
│       │
│       └── audio/
│           ├── decoder.py
│           ├── buffer.py
│           └── output.py
│
└── tests/
    ├── test_station_repository.py
    ├── test_stream_session.py
    ├── test_protocol.py
    ├── test_reconnect.py
    └── test_program_api.py
```

---

# 51. 推奨実装順序

## Phase 1: Session API

```text
station_id
 ↓
select_stream
 ↓
token/location
```

404を `UNAVAILABLE` として扱う。

## Phase 2: WSS

```text
location
 ↓
subprotocol
 ↓
token TEXT
 ↓
BINARY
```

## Phase 3: Audio

```text
Ogg Opus
 ↓
PyAV / FFmpeg
 ↓
PCM
 ↓
speaker
```

## Phase 4: Stability

```text
buffer
timeout
close
reconnect
sleep/resume
```

## Phase 5: Station Directory

```text
JCBA site
 ↓
station list
 ↓
cache
```

## Phase 6: Program Metadata

```text
timetables API
 ↓
current/next program
```

## Phase 7: UI

```text
station list
search
favorites
play / stop
volume
buffer
program metadata
```

---

# 52. 現時点の最小プロトコル仕様

```text
Protocol:
    HTTPS + WSS

Station key:
    station_id

Stream API:
    https://api.radimo.smen.biz/api/v1/select_stream

Method:
    GET

Parameters:
    station=<station_id>
    channel=0
    quality=high
    burst=5

Success response:
    code
    token
    location

Unavailable:
    HTTP 404
    JSON contains code / error

WebSocket:
    URL = response.location

Observed location:
    wss://osXXXX.radimo.smen.biz:443/socket?burst=5

Subprotocol:
    listener.fmplapla.com

Origin:
    https://www.jcbasimul.com

Authentication:
    send token as WebSocket TEXT message

Audio transport:
    WebSocket BINARY

Observed framing:
    1 BINARY message = 1 complete Ogg page
    confirmed on 3 stations

Container:
    Ogg

Codec:
    Opus

Audio:
    48000 Hz
    stereo
    mapping family 0

Estimated audio bitrate:
    approximately 64–67 kbps class

Server/encoder observed:
    fmpp 1.7.1

Reconnect:
    discard old token/location
    call select_stream again

Station list:
    JCBA website embedded data
    local cache recommended

Program API:
    /api/v1/mobile/timetables?station=<station_id>
    optional
```

---

# 53. 実測により確定度が上がった項目

## 確定扱い可能

```text
GET select_streamが現行FMななみで成功
responseにcode/token/location
locationは動的WSS
port 443
path /socket
listener.fmplapla.com
token TEXT送信
BINARY audio
Ogg
Opus
48kHz
2ch stereo
Opus mapping family 0
3通常局で同一方式
3通常局で1 WS BINARY = 1 Ogg page
fmpp 1.7.1
臨時局でselect_stream 404があり得る
```

## 強い推定

```text
burst=N
  ≈ 接続開始時にN秒分の過去音声を先行送出

通常audio bitrate
  ≈ 64〜67 kbps級
```

## 未確定

```text
tokenの厳密なTTL
tokenの複数接続再利用可否
locationの厳密なTTL
burst=2/30/60でN秒と完全一致するか
長時間接続時のserver ping interval
全局で1 WS frame = 1 Ogg pageが保証されるか
全局が48kHz stereoか
rinsaikantoの404 response.errorの実値
404が「現在配信なし」か「station無効」かの厳密区別
```

---

# 54. 残る実測候補

優先度が高いものだけを挙げる。

## A. burst比較

同一局で:

```text
burst=2
burst=5
burst=30
burst=60
```

を比較する。

確認:

```text
接続時間
受信音声granule差
初期受信bytes
初期送信速度
```

これにより:

```text
burst=N → N秒
```

を確定できる。

## B. 404 error body

`rinsaikanto` で:

```json
{
  "code": ...,
  "error": "..."
}
```

の値を記録する。

## C. 長時間WSS

数分〜数十分接続し:

```text
server PING
idle timeout
disconnect interval
```

を確認する。

通常の受信アプリ実装開始には、これらの完了を待つ必要はない。

---

# 55. 実装判断

現時点で、JCBA受信エンジンの基本仕様は実装開始可能な水準まで確定している。

必要以上に局別ロジックや独自Ogg/Opus実装を増やさず:

```text
station_id
 ↓
select_stream
 ↓
WSS
 ↓
Ogg Opus
 ↓
既存decoder
```

という単純な共通パイプラインを中心にする。

例外処理として重要なのは:

```text
select_stream 404 → UNAVAILABLE
network loss      → session再取得
unexpected frame  → protocol fallback/error
```

の3点である。
