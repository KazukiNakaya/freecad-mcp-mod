# 開発者向けメモ

利用方法は [README](../README.md) を参照。ここにはアドオンの開発に必要な情報を書く。

## 開発環境

```bash
uv run --group dev pytest
```

クローンしたソースを Claude Desktop から使う場合の設定:

```json
{
  "mcpServers": {
    "freecad": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/freecad-mcp/",
        "run",
        "freecad-mcp"
      ]
    }
  }
}
```

## 公式版からの変更点

- `addon/FreeCADMCP/rpc_server/mcp_status.py`: ステータスバーの表示を追加
- `addon/FreeCADMCP/InitGui.py`: 起動時に表示を組み込む
- `src/freecad_mcp/`（MCPサーバー本体）は変更していない。そのため `uvx freecad-mcp` で公式のパッケージをそのまま使える

範囲はステータス表示のみで、既定のワークベンチの変更や共通のON/OFFツールバーは含まない。

## InitGui.py の制約

FreeCAD は `InitGui.py` を、`RunInitGuiPy` 関数の中から globals を指定せずに `exec()` で実行する。そのためトップレベルの名前は `exec` のローカルにしか入らず、同じファイルの関数の本体からは見えない。

```python
def a(): ...
def b(): a()                     # 実行時に NameError
QtCore.QTimer.singleShot(0, b)

QtCore.QTimer.singleShot(0, a)   # OK: exec の実行中に参照を渡している
```

この問題で Auto-Start が動かなくなったことがあるため、`tests/test_initgui_startup.py` で同じ実行方法を再現して確認している。

## ステータス表示の仕組み

- 500ミリ秒ごとに、アドオン内部の状態（`rpc_server_instance` と `_stop_thread`）を確認する。ネットワーク通信はしない
- `stop_rpc_server` はソケットを閉じる前にインスタンスを消すので、`_stop_thread` が動いている間を Stopping... とする
- ラベルとタイマーはステータスバーが所有する。表示の組み込みに失敗しても自動起動は実行される

## 手動確認の手順

1. 自動起動OFFで FreeCAD を起動し、MCP Addon を選ぶ前から赤の Stopped が出ることを確認する
2. Start RPC Server で緑の Running に変わることを確認する
3. 別のワークベンチへ切り替えても表示が残ることを確認する
4. Stop RPC Server で Stopped に戻り、再度起動できることを確認する
5. 自動起動ONで FreeCAD を再起動し、Running になることを確認する

`QT_QPA_PLATFORM=offscreen` と `FREECAD_USER_HOME`、`FREECAD_USER_DATA`、`FREECAD_USER_TEMP` を指定すると、実環境の設定に触れずに FreeCAD を画面なしで起動して確認できる。

## GUIスレッドとタイムアウト

- GUIスレッドの処理が開始後にタイムアウトすると、ブリッジは `GUI_DISPATCH_STUCK` を返し、以降のGUI処理をすぐに拒否する
- `get_rpc_status` はGUIスレッドを使わない。別のRPCクライアントから、実行中の処理を特定できる
- RPCサーバーは接続を並行処理するので、診断は他のリクエストの完了を待たない
- `get_object`、`get_objects`、`list_documents` もGUIスレッドで動き、タイムアウトや停滞時はRPC faultを返す
- GUI処理は安全に強制キャンセルできない。処理の完了後も `healthy` に戻らなければ FreeCAD を再起動する

## execute_code

- `execute_code` と `execute_code_async` は、`FreeCAD`/`App` と `FreeCADGui`/`Gui` を持つ共通の名前空間で動く。変数は呼び出しをまたいで残るが、RPCサーバー自身の関数は上書きしない
- これは名前の衝突を防ぐためのもので、権限を制限するものではない
- FreeCAD の開発版で `execute_code` が例外を出した場合は、新しい `FeaturePython` オブジェクトを変更や削除の前に確認する。`Proxy` が設定されていない壊れたオブジェクトに触れると、GUIスレッドが停止することがある

## 既知の問題

- Windows では `SimpleXMLRPCServer` の `allow_reuse_address=True` により、同じポートを二重にバインドしてもエラーにならない。FreeCAD を2つ起動すると両方とも Running と表示され、どちらに接続されるかは保証されない。同じ設定の標準の `SimpleXMLRPCServer` で、Windows 11 上の二重バインドを確認した
