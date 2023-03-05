import glob
import re
import requests
from bs4 import BeautifulSoup
import tqdm
import spotify_id as si
import spotipy
import pandas as pd
import pykakasi
import os


def main():
    genre = int(input('ジャンルを選択 1:邦ロック 2:女性アイドル 3:ボカロ 4:J-POP >>'))
    if genre == 1:
        art_names = get_Japanese_band_names()
    if genre == 2:
        art_names = get_girls_idol_names()
    if genre == 3:
        art_names = get_vcp_names()
    if genre == 4:
        art_names = get_jpop_names()
    artnames_to_csv(art_names,genre)
    consolidate_data(genre)


def get_Japanese_band_names():
    Japanese_band_names = []
    url = 'https://ja.wikipedia.org/wiki/%E6%97%A5%E6%9C%AC%E3%81%AE%E3%83%90%E3%83%B3%E3%83%89%E4%B8%80%E8%A6%A7'
    r = requests.get(url)
    soup = BeautifulSoup(r.text,'html.parser')
    elems = soup.find_all('li')

    for elem in elems:
        Japanese_band_names.append(elem.a.string)
    Japanese_band_names = Japanese_band_names[326:2791]
    return Japanese_band_names


def get_girls_idol_names():
    girls_idol_names = []
    #スクレイピング先サイト
    url = 'https://ja.wikipedia.org/wiki/%E6%97%A5%E6%9C%AC%E3%81%AE%E5%A5%B3%E6%80%A7%E3%82%A2%E3%82%A4%E3%83%89%E3%83%AB%E3%82%B0%E3%83%AB%E3%83%BC%E3%83%97%E3%81%AE%E4%B8%80%E8%A6%A7'
    r = requests.get(url)
    soup = BeautifulSoup(r.text,'html.parser')
    ##mw-content-text > div.mw-parser-output > divの要素を全て取得
    elems = soup.select('#mw-content-text > div.mw-parser-output > div')

    for elem in elems:
        #取得したもののうちaタグに該当するものを
        names = elem.select('a')
        for name in names:
            #抜き出したものの中から要素だけを
            girls_idol_names.append(name.string)

    return girls_idol_names


def get_vcp_names():
    vcp_names = []
    print('ボカロpの名前を取得中...')
    #ページ数が1~50まで
    for i in tqdm.tqdm(range(1,51)):
        #urlの末尾がページ数になってる
        url = 'http://nicodb.jp/v/bgm/alllist/' + str(i)
        #urlの情報を取る
        r = requests.get(url)
        soup = BeautifulSoup(r.text,'html.parser')
        [tag.extract() for tag in soup(string='n')]

        for j in range(1,101):
            #{}の中にjを入れる
            elems = soup.select('#SortTable > tbody > tr:nth-of-type({}) > td:nth-of-type(3) > a > span'.format(str(j)))
            name = elems[0].text
            name = name.replace('\n','')
            vcp_names.append(name.strip())
    return vcp_names


def get_jpop_names():
    jpop_artists=[]
    #Rakutenブックス CD J-POP アーティスト一覧
    URL = 'https://books.rakuten.co.jp/cd/artist/japanese-pop-music/#sa'
    res = requests.get(URL)
    soup = BeautifulSoup(res.text, 'html.parser')

    #find_allでタグ:td,class = etc_rankを全て取得
    etc_ranks = soup.find_all('td',class_='etc_rank')

    print('アーティスト名を取得中...')
    for i in tqdm.tqdm([6, 7, 8, 9, 10, 17, 18, 19, 20, 21, 28, 29, 30, 31, 32, 39, 40, 41,
    42, 43, 50, 51, 53, 54, 61, 62, 63, 64, 65, 72, 73, 74, 75, 76, 81, 82, 83, 90, 91, 93, 94, 98, 99]):
        for j in etc_ranks[i].find_all('a'):
            jpop_artists.append(j.text)

    return jpop_artists


def artnames_to_csv(art_names,genre):
    #認証
    client_credentials_manager = spotipy.oauth2.SpotifyClientCredentials(si.id(), si.secret())
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager,language='ja')

    #データフレーム宣言
    df = pd.DataFrame()

    print('楽曲情報取得中...')
    for art_name in tqdm.tqdm(art_names):
        #全曲
        #offsetずらす用のcnt
        cnt = 0
        #連続で見つからない回数
        continuous_times = 0
        df = pd.DataFrame()
        ids = []
        names = []
        art_names = []

        #offsetの上限1000を超えないように
        while(cnt < 20):
            tracks = sp.search(q=art_name, limit=50, offset=cnt*50, type='track')['tracks']['items']
            cnt +=1
            #検索結果がなくなったらbreak
            if len(tracks) == 0 or continuous_times > 100:
                break

            for track in tracks:
                if track is None:
                    continue
                if track['artists'][0]['name'] == art_name:
                    continuous_times = 0
                    ids.append(track['id'])
                    names.append(track['name'])
                    art_names.append(track['artists'][0]['name'])
                else:
                    continuous_times +=1
            
        for i in range(0, len(ids), 100):
            results = sp.audio_features(ids[i:i+100])
            for j,result in enumerate(results):
                if result is None:
                    continue
                result['name'] = names[i+j]
                s = pd.DataFrame(result.values(),index=result.keys()).T
                s = s.set_index('name')
                df = pd.concat([df,s])

        name = ''
        if len(df) != 0:
            kks = pykakasi.kakasi() # インスタンスの作成

            result = kks.convert(str(art_name))
            for kanji in result:
                name = name + kanji['passport']
                #ファイル名に使えないものを'-'に変換
                name = re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '-', name)
                
            name = str(name) + '.csv'
            #df内の重複を削除
            df = df.drop_duplicates()

            if genre == 1:
                folder = 'Japanese_band'
            if genre == 2:
                folder = 'girls_idol'
            if genre == 3:
                folder = 'internet_singer'
            if genre == 4:
                folder = 'vocaloid'
            if genre == 5:
                folder = 'Jpop'            
            dir = os.path.dirname(__file__)
            file_name = os.path.join(dir,'csvfiles',folder,name)
            df.to_csv(file_name,encoding='utf-8',index=True)

def consolidate_data(genre):
    # パスで指定したファイルの一覧をリスト形式で取得. （ここでは一階層下のtestファイル以下）
    if genre == 1:
        path = './csvfiles/Japanese_band'
    if genre == 2:
        path = './csvfiles/girls_idol'
    if genre == 3:
        path = './csvfiles/vocaloid'
    if genre == 4:
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

if __name__ == '__main__':
    main()
