# UI 設計

## ビジュアル方針: Midnight Broadcast

深い藍の背景に、放送信号を思わせるライムとコーラルをアクセントとして使う。情報量の多い局一覧は暗いカードと明快な階層で整理し、現在再生中の局を大きなアートワークとメーターで主役にする。

- 表示書体: `DM Sans`（UI）と `Space Grotesk`（局名・数値）
- 配色: ink `#07111f`、panel `#10233a`、lime `#c6f44a`、coral `#ff7b54`
- モーション: 再生中に控えめな waveform と station signal をアニメーション。`prefers-reduced-motion` では停止する。

## レイアウト

- Desktop: 左 300px に局ブラウザ、右に Now Playing と番組・操作領域。
- Mobile: Now Playing を先頭、局一覧を下部に 1 カラム表示。
- Header: ロゴ、ライブ接続状態、局数。

## 主な操作フロー

1. 検索または地域 chip で局を絞る。
2. 局カードを選択するとプレーヤーに反映され、再生ボタンで接続する。
3. お気に入りボタンは `localStorage` に station ID を保存し、一覧のピンで即時反映する。
4. 音量 slider／mute で audio 要素を制御する。
5. 失敗時は障害が起きた場所に応じた短い説明と「再試行」を表示する。

## アクセシビリティ

- ボタン・入力に aria-label と可視 focus ring を付ける。
- 状態文言を `aria-live=polite` で通知する。
- 色のみで状態を区別せず、アイコンとテキストも併用する。
