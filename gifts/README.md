# ギフトコード登録

GitHub Pagesでは入力体験のみ。実際の登録には公開HTTPSのリバースプロキシから同一オリジンの /api/gifts/ を登録サーバーに転送するか、登録サーバーの /gifts/ をHTTPSで公開してHPからリンクする。

Python 3で python3 scripts/gifts.py を実行すると localhost:8130 で登録画面とAPIが起動する。標準モードの保存先は実行ユーザーのホームにある .ncb-gifts.sqlite3。標準モードの登録をBotへ自動移行することはない。

## 自動交換の接続

Kingshot Project の Kingshot-Discord-Bot を別途運用し、同じホストで登録サーバーを起動する。互換性を確認したソースは ce2dcdc8503f6a6e1dcfb7799147c69e6cd6857c。Botで外部王国を含むギフト登録専用グループを作成し、自動交換・新着コードの監視・結果ログを設定する。外部登録者にNCB同盟員としての権限を付与しないようグループを分ける。

NCB_BOT_DB にBotの既存dbディレクトリ、NCB_GIFT_GROUP にそのグループの数値IDを設定して登録サーバーを起動する。登録先はBotのusers.sqlite。既存の所属と王国は上書きしない。新コードの取得・交換・結果通知は稼働中のBotが担当する。登録解除は管理者がBotのメンバー管理から行う。運営公認の外部APIではない。実際の交換、Discord接続、ホスティングは試作の確認対象外。
