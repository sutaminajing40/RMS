import pandas as pd
import glob
import os

# パスで指定したファイルの一覧をリスト形式で取得. （ここでは一階層下のtestファイル以下）
genre = int(input('ジャンルを選択 1:邦ロック 2:女性アイドル 3:歌い手 4:ボカロ 5:J-POP >>'))
if genre == 1:
    path = './csvfiles/Japanese_band'
if genre == 2:
    path = './csvfiles/girls_idol'
if genre == 3:
    path = './csvfiles/internet_singer'
if genre == 4:
    path = './csvfiles/vocaloid'
if genre == 5:
    path = './csvfiles/Jpop'

csv_files = glob.glob(os.path.join(path,'*.csv'))

#読み込むファイルのリストを表示
for a in csv_files:
    print(a)

#csvファイルの中身を追加していくリストを用意
data_list = []

#読み込むファイルのリストを走査
for file in csv_files:
    data_list.append(pd.read_csv(file))

#リストを全て行方向に結合
#axis=0:行方向に結合, sort
df = pd.concat(data_list, axis=0, sort=True)

df.to_csv(os.path.join(path,"music_data.csv"),index=False)