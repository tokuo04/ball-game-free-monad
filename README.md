# FDM Ball

SQLite 上の Free モナドで動かす「ブロック崩しのボールのみ」。サーバー(Python, Pyright strict)が
Firebase Realtime Database へ状態を配信し、GitHub Pages のブラウザが受信側コンフレーションで描画します。

## 構成
- `fdmball/free.py` 汎用 Free モナド(スタック安全) / `domain.py` 純粋ドメイン(decide/evolve)
- `fdmball/dsl.py` 命令 Load/Emit とプログラム / `store.py` SQLite インタープリタ(snapshot+イベント再生)
- `fdmball/__main__.py` 命令的シェル(時計・空きポートの制御口・配信)
- `docs/index.html` ブラウザ(GitHub Pages)

## 手順
1. Firebase で Realtime Database を作成し、`database.rules.json` を適用する。
2. リポジトリ変数 `FIREBASE_CONFIG_JSON` に Firebase のウェブアプリ設定(`{...}` の JSON)を登録する。
3. Settings → Pages → Source を「GitHub Actions」にして Actions から Run workflow。
4. サーバー起動(標準ライブラリのみ。Colab でも可):

       export FIREBASE_DB_URL=https://<project>-default-rtdb.firebaseio.com
       export FIREBASE_AUTH=<データベースシークレット>
       python -m fdmball --reset

   起動時に OS が割り当てた空きポートが表示されます(制御口: `GET /state`, `POST /launch`)。
5. ブラウザで Pages の URL を開く(`?room=名前` で部屋を切替)。複数ブラウザが同じ画面を共有します。

テスト: `python -m unittest discover -s tests -t .` / 型検査: `pip install pyright && pyright`
