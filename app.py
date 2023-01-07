import glob
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import streamlit as st
import os
import pandas as pd
import spotipy
import spotify_id as si
from spotipy.oauth2 import SpotifyClientCredentials



def main():
    with st.form('送信フォーム'):
        URL,genre,tempo,energy = initial_display()
        submitted = st.form_submit_button("送信")

    if submitted:
        with st.spinner('プレイリスト取得中...'):
            url_to_items(URL)
        with st.spinner('楽曲情報取得中...'):
            all_song_data,target_song_data = load_items(genre)
        with st.spinner('推薦中...(10分かかる場合があります)'):
            recommendation_ids = recommender(all_song_data,target_song_data,tempo,energy)
        with st.spinner('プレイリスト作成中...'):
            playlist_id = create_playlist(playlist_name='おすすめ',items=recommendation_ids)
        st.write('作成したプレイリスト')
        st.write('https://open.spotify.com/playlist/'+playlist_id)
    

#初期表示
def initial_display():
    #タイトル表示
    st.title('音楽推薦システム')
    #Spotify Playlist の共有URLを入力
    URL = st.text_input('URLを入力',value='https://open.spotify.com/playlist/4ovXpa5zN9xoannaeP7OZF?si=rb5xpbtoQQeHZPeyiX97mw')

    #ユーザが選択した要素
    tempo = st.slider(label='テンポ',min_value=0,max_value=100,value=50)
    energy = st.slider(label = 'エネルギー',min_value=0,max_value=100,value=50)
    
    #ユーザが選択したジャンル
    genre = st.selectbox('ジャンルを選択',('全て選択','ボカロ','J-POP'))

    return URL,genre,tempo,energy


#プレイリスト共有URLからtarget_playlist_items.csvを作成する
def url_to_items(URL):
    #共有URLからプレイリストidを抜き出す
    target1 = 'playlist/'
    target2 = '?'
    idx1 = URL.find(target1)
    idx2 = URL.find(target2)
    playlist_id = URL[idx1+9:idx2]

    #楽曲情報を格納するdataframe
    items_df = pd.DataFrame()

    #playlist_idからプレイリスト内の楽曲情報を取り出せる
    playlist_items = sp.playlist_items(playlist_id)['items']

    #playlist_itemsの各楽曲から解析情報を取り出す
    for track in playlist_items:
        result = sp.audio_features(track['track']['id'])
        result[0]['name'] = track['track']['name']
        item = pd.DataFrame(result[0].values(),index=result[0].keys()).T
        item = item.set_index('name')
        items_df = pd.concat([items_df,item])

    #target_playlist_items.csvを作成
    dir = os.path.dirname(__file__)
    file_name = os.path.join(dir,'csvfiles','target_playlist_items.csv')
    items_df.to_csv(file_name,encoding='utf-8',index=True)


def load_items(genre):
    #選択されたジャンルによって取得する曲を選択
    if genre == '全て選択':
        song_path = glob.glob('sutaminajing40/rms/main//app/csvfiles/*/*.csv')
    if genre == 'ボカロ':
        song_path = glob.glob('sutaminajing40/rms/main//app/csvfiles/vocaloid/*.csv')
    if genre == 'J-POP':
        song_path = glob.glob('sutaminajing40/rms/main//app/csvfiles/Jpop/*.csv')

    #all_song_data:ジャンルに対応した全ての楽曲のデータ
    all_song_data = pd.DataFrame()
    #ジャンルに対応した.csvのパスを取得
    for path in song_path:
        song_data = pd.read_csv(path)
        all_song_data = pd.concat([all_song_data,song_data])

    target_song_data = pd.read_csv('/Users/iguchihiroto/Documents/programming/app/csvfiles/target_playlist_items.csv')
    #推薦の対象となる曲にnotice = 1をそれ以外にnotice = 0を
    all_song_data['notice'] = 0
    target_song_data['notice'] = 1
    #列名の整頓
    all_song_data = all_song_data.reindex(columns=['name','id','notice','danceability','energy',
    'loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo'])
    target_song_data = target_song_data.reindex(columns=['name','id','notice','danceability','energy',
    'loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo'])

    return all_song_data,target_song_data


def recommender(all_song_data,target_song_data,tempo,energy):
    recommendation_ids = []
    #全曲データにtargetデータの値を一曲ずつ入れて最近傍探索で一番近い曲を探す
    for index,song_data in target_song_data.iterrows():
        #合体したデータの格納先
        ori_song_data = pd.DataFrame()
        ori_song_data = all_song_data.append(song_data)
        #正規化
        minmax_sc = MinMaxScaler()
        X = ori_song_data.loc[:,'danceability':'tempo']
        X = minmax_sc.fit_transform(X)
        ori_song_data.loc[:,'danceability':'tempo'] = X

        #バイアス
        tempo_bias = tempo*-0.015+2
        energy_bias = energy*-0.015+2
        ori_song_data['tempo']*=tempo_bias
        ori_song_data['energy']*=energy_bias
        #最近傍探索で一番近いものを探す
        comparison_songs = ori_song_data[ori_song_data.notice == 0]
        target_song = ori_song_data[ori_song_data.notice == 1]
        np_target_song = target_song[['danceability','energy','loudness','speechiness','acousticness',
        'instrumentalness','liveness','valence','tempo']].values
        #距離
        dis = 9999
        for index1,comparison_song in comparison_songs.iterrows():
            np_comparison_song = comparison_song[['danceability','energy','loudness','speechiness','acousticness',
            'instrumentalness','liveness','valence','tempo']].values
            new_dis = np.linalg.norm(np_target_song-np_comparison_song)
            if new_dis < dis:
                dis = new_dis
                #一番近い曲のid
                id = comparison_song['id']
        #最近傍探索の結果のidをlistで
        recommendation_ids.append(id)

    return recommendation_ids


def create_playlist(playlist_name,items):
    id = sp.user_playlist_create(user='nohoarito_yuzu_334129',name=playlist_name)['id']
    sp.playlist_add_items(playlist_id=id,items = items)
    return id

if __name__ == '__main__':
    auth_manager = SpotifyClientCredentials(client_id=si.id(),client_secret=si.secret())
    sp = spotipy.Spotify(auth_manager=auth_manager)
    main()