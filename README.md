# SUUMOからスクレイピングする
## 住宅情報を取得
- requestsとstreeを使っています。seleniumなどに変更する場合に、xpathのほうがより簡単だと判断したためです。
- サイトに負荷をかけないように待機時間を設けています。
- 利用規約を必ず読みましょう

## 距離を計算する
- 2点間距離はそのまま計算しています。
- 点と領域の距離は、平面座標系に変換したうえで、ベクトルの考え方で計算しています。