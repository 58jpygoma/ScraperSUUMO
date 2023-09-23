#読み込み
import time
import requests
from lxml import etree
import pandas as pd
import json
from geopy.distance import geodesic
import pyproj
import numpy as np
from numpy.linalg import norm
import folium

outputname = "output.csv"

# スカイツリーの緯度経度を入力
specific_latitude = 35.710053960864165
specific_longitude = 139.81070039716005

# pyprojによる座標変換オブジェクトの作成
input_crs = pyproj.CRS.from_epsg(4326)  # WGS 84 (緯度経度座標系)
output_crs = pyproj.CRS.from_epsg(6677)  # 東京都心の平面直角座標系
transformer = pyproj.Transformer.from_crs(input_crs, output_crs, always_xy=True)

# スカイツリーの頂点の座標を指定
polygon_coords = [(35.710219481322696, 139.8084902568853), 
                  (35.70950512741073, 139.8086404605933), 
                  (35.70992328657517, 139.81318948717825), 
                  (35.710829290572335, 139.8130821988154),]
m = folium.Map(location=[specific_latitude, specific_longitude], zoom_start=15, control_scale=True)
for i, coord in enumerate(polygon_coords, start=1):
    folium.Marker(location=[coord[0], coord[1]], popup=f'Marker {i}').add_to(m)
m.save('park_points.html')
polygon_coords_xy = [transformer.transform(lon, lat) for lat, lon in polygon_coords]
#距離計算する関数を定義
def calc_distance_and_neighbor_point(a, b, p):
    ap = p - a
    ab = b - a
    ba = a - b
    bp = p - b
    if np.dot(ap, ab) < 0:
        distance = norm(ap)
        neighbor_point = a
    elif np.dot(bp, ba) < 0:
        distance = norm(p - b)
        neighbor_point = b
    else:
        ai_norm = np.dot(ap, ab)/norm(ab)
        neighbor_point = a + (ab)/norm(ab)*ai_norm
        distance = norm(p - neighbor_point)
    return (neighbor_point, distance)

##各物件のurl集め
start_time = time.time()
url_list = [] 
#コードミスによりサイトに負担をかけないためfor文で記述
for n in range(1000):
    #ここに検索した時のurl(pageに注意)
    response = requests.get(f"https://suumo.jp/jj/chintai/ichiran/FR301FC005/?ar=030&bs=040&ta=13&sc=13107&cb=0.0&ct=9999999&mb=0&mt=9999999&md=01&et=9999999&cn=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&sngz=&po2=99&po1=00&page={n+1}")

    content = response.content
    tree = etree.HTML(content)
    if tree.xpath(".//div[@class='error_pop-txt']"):
        break
    for i in tree.xpath('//h2//a'): 
        name = i.xpath('text()')[0]
        #print(name)
        url = i.get('href')
        url_list.append([name, url])
    print(n)
    time.sleep(1)


end_time = time.time()
elapsed_time = end_time - start_time
print(f"最初のURLの所要時間{elapsed_time}")

columns = ["building_name", "url", 
            "rent", "management_fee", "security_deposit", "key_money", 
            "layout", "floor_area", "direction", "building_type", "age", 
            "access", "location", 
            "amenities", 
            "detailed_layout", "structure", "floor_level", "year_built", "insurance", "parking", "occupancy", "transaction_type", "conditions", "handling_store", "suumo", 
            "total_units", "information_updated_date", "next_update_date", "guarantor_company", "other_fees", "notes", "surroundings_information", "latitude","longitude",
            "distance", "distance_to_area"
            ]

##物件それぞれのページに飛び、データを収集する
start_time = time.time()
rent_data = []

for number, url in enumerate(url_list):
    rent = []
    rent.extend([url[0],"https://suumo.jp"+url[1]]) 
    #契約成立の404やアーカイブにリダイレクトされるのを防ぐ
    response = requests.get("https://suumo.jp"+url[1], allow_redirects=False)
    if not 200 <= response.status_code < 300:
        continue
    content = response.content
    tree = etree.HTML(content)
    print(str(number) + ":  https://suumo.jp"+url[1])
    
    #最初の上のほうにある情報
    rent_fee = tree.xpath("//*[@class='property_view_main-emphasis']/text()")[0].strip()
    management_fee = tree.xpath("//div[text()='管理費・共益費']/following-sibling::div[1]/text()")[0].strip()
    deposit = tree.xpath("//div[text()='敷金/礼金']/following-sibling::div[1]/span[1]/text()")[0].strip()
    gratuity_fee = tree.xpath("//div[text()='敷金/礼金']/following-sibling::div[1]/span[3]/text()")[0].strip()
    rent.extend([rent_fee,management_fee,deposit,gratuity_fee])

    room_information = []
    signatures = ["間取り", "専有面積", "向き", "建物種別", "築年数"]
    for signature in signatures:
        info = tree.xpath(f"//div[text()='{signature}']/following-sibling::div[1]/text()")[0].strip()
        room_information.append(info)
    rent.extend(room_information)
    
    access_list =[]
    access_elements = tree.xpath("//span[text()='アクセス']/parent::*/following-sibling::div/div")
    access_list = [access_element.text.strip() for access_element in access_elements]

    place = tree.xpath("//span[text()='所在地']/parent::*/following-sibling::div/div/text()")[0].strip()
    rent.extend([access_list,place])

    #以上が最初の上のほうにある情報

    #物件概要
    body02 = tree.xpath("//*[@id='contents']")[0]


    try:
        facilities = body02.xpath("//*[@id='bkdt-option']//li/text()")[0].strip()
    except:
        facilities = ""
    rent.append(facilities)

    #下の表
    building_information = []
    signatures = ["間取り詳細", "構造", "階建", "築年月", "損保", "駐車場", "入居", "取引態様", "条件", "取り扱い店舗", "SUUMO", "総戸数", "情報更新日", "次回更新日"]
    for signature in signatures:
        try:
            element = body02.xpath(f"//th[text()='{signature}']/following-sibling::td[1]/text()")
            if element:
                element_text = element[0].strip()
                building_information.append(element_text)
            else:
                building_information.append("")
        except:
            building_information.append("")
    signatures = [ "保証会社", "ほか諸費用", "備考", "周辺情報"]
    for signature in signatures:
        try:
            elements = body02.xpath(f"//th[text()='{signature}']/following-sibling::td[1]/ul/li/text()")
            if elements:
                elements_text = [ element.strip() for element in elements]
                if len(elements_text) == 1:
                    building_information.extend(elements_text)
                else:
                    building_information.append(elements_text)
            else:
                building_information.append("")
        except:
            building_information.append("")
    rent.extend(building_information)

    #緯度経度を求める
    map_response = requests.get("https://suumo.jp"+url[1]+"kankyo/", allow_redirects=False)
    if not 200 <= map_response.status_code < 300:
        continue

    map_content = map_response.content
    map_tree = etree.HTML(map_content)

    #マップから座標を取得
    try:
        script_element = map_tree.xpath('//script[@id="js-gmapData"]')[0]

        script_element = script_element.text.strip()

        data = json.loads(script_element)
        

        lat = data["center"]["lat"]
        lng = data["center"]["lng"]
    except:
        lat = ""
        lng = ""

    rent.extend([lat,lng])
    

    lat = rent[32]
    lon = rent[33]
    #直線距離計算
    if lat != "":
        distance = geodesic((specific_latitude, specific_longitude), (lat, lon)).meters
        rent.append(distance)
    else:
        distance = ""
        rent.append(distance)

    #点と領域の距離計算
    if lat != "":
        point_coords = (lat,lon)
        point_coords_xy = transformer.transform(point_coords[1], point_coords[0])

        #print(type(point_coords_xy))
        p = np.array([point_coords_xy[0],point_coords_xy[1]])
        #print(p)

        min_distance = float('inf')  # 初期値を無限大に設定
        for i in range(len(polygon_coords_xy)):
            a = np.array(polygon_coords_xy[i])
            b = np.array(polygon_coords_xy[(i + 1) % len(polygon_coords_xy)])  # 最後の辺から最初の辺へループ
            
            # 点から辺への最短距離を計算 (直線からの垂線距離)
            _, distance = calc_distance_and_neighbor_point(a, b, p)
            
            # 最短距離を更新
            if distance < min_distance:
                min_distance = distance
        if min_distance == float("inf"):
            min_distance = ""
        rent.append(min_distance)
    else:
        rent.append("")

    rent_df = pd.DataFrame([rent], columns=columns)

    #エラーで止まる可能性から、毎回書き加える。
    rent_row =rent_df
    if number == 0:
        rent_row.to_csv(outputname, mode='w', header=True, index=False)
    else:
        rent_row.to_csv(outputname, mode='a', header=False, index=False)
    
    time.sleep(1)


end_time = time.time()
elapsed_time = end_time - start_time
print(f"各ページからの情報の所要時間{elapsed_time}")
