import numpy as np
from sklearn.preprocessing import MinMaxScaler
import streamlit as st
import pandas as pd
import spotipy
import spotify_id as si
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util as util




def main():
    with st.form('送信フォーム'):
        URL,username,genre,tempo,energy = initial_display()
        submitted = st.form_submit_button("送信")

    if submitted:
        #API認証
        token = util.prompt_for_user_token(username,
                                    scope="playlist-modify-public",
                                    client_id=si.id(),
                                    client_secret=si.secret(),
                                    redirect_uri='https://localhost:8888/callback/')
        sp = spotipy.Spotify(auth=token)
        with st.spinner('プレイリスト取得中...'):
            playlist_items = url_to_items(sp,URL)
        with st.spinner('楽曲情報取得中...'):
            all_song_data,target_song_data = load_items(genre,playlist_items)
        with st.spinner('推薦中...(10分ほどかかる場合があります)'):
            recommendation_ids = recommender(all_song_data,target_song_data,tempo,energy)
        display_result(sp,recommendation_ids)
        #create_playlist(sp,recommendation_ids,username,'おすすめ')



#初期表示
def initial_display():
    #タイトル表示
    st.title('音楽推薦システム')
    #Spotify Playlist の共有URLを入力
    URL = st.text_input('URLを入力(公開プレイリストのみ)',value='https://open.spotify.com/playlist/4xrsvkAXz2cEjBRguh65X3?si=Ol8lTMUITzS4glmaqfHdlw')
    username = st.text_input('ユーザーidを入力')
    #ユーザが選択した要素
    tempo = st.slider(label='テンポ',min_value=0,max_value=100,value=50)
    energy = st.slider(label = 'エネルギー',min_value=0,max_value=100,value=50)
    
    #ユーザが選択したジャンル
    genre = st.selectbox('ジャンルを選択',('全て選択','邦ロック','ボカロ','J-POP','女性アイドル','test'))

    return URL,username,genre,tempo,energy


#プレイリスト共有URLからtarget_playlist_itemsを作成する
def url_to_items(sp,URL):
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

    return items_df


def load_items(genre,playlist_items):
    #選択されたジャンルによって取得する曲を選択
    #all_song_data:ジャンルに対応した全ての楽曲のデータ
    if genre == '全て選択':
        all_song_data = pd.read_csv('csvfiles/Jpop/music_data.csv')
        all_song_data = pd.concat([all_song_data,pd.read_csv('csvfiles/vocaloid/music_data.csv'),
        pd.read_csv('csvfiles/Japanese_band/music_data.csv'),pd.read_csv('csvfiles/girls_idol/music_data.csv')])
    if genre == '邦ロック':
        all_song_data = pd.read_csv('csvfiles/Japanese_band/music_data.csv')
    if genre == 'ボカロ':
        all_song_data = pd.read_csv('csvfiles/vocaloid/music_data.csv')
    if genre == 'J-POP':
        all_song_data = pd.read_csv('csvfiles/Jpop/music_data.csv')
    if genre == '女性アイドル':
        all_song_data = pd.read_csv('csvfiles/girls_idol/music_data.csv')
    if genre == 'test':
        all_song_data = pd.read_csv('csvfiles/test/music_data.csv')


    target_song_data = playlist_items
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
        ori_song_data = ori_song_data.drop_duplicates(subset='name',keep='last')
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


def create_playlist(sp,items,username,playlist_name):
    id = sp.user_playlist_create(user=username,name=playlist_name)['id']
    sp.playlist_add_items(playlist_id=id,items = items)


def display_result(sp,ids):
    results = []
    song_datas = sp.tracks(ids)['tracks']
    for data in song_datas:
        results.append([data['name'],data['artists'][0]['name']])
    result = pd.DataFrame(
        results,
        columns=['曲名','アーティスト名']
    )
    st.dataframe(result)

if __name__ == '__main__':
    main()