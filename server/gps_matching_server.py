import os
import socket
import threading
import geopandas
import h5py
import psycopg2
import geopandas as gpd
import pandas as pd
import webbrowser
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np
import datetime
import time
import json


host = "localhost"
port = 5432
database = "harbin"
user = "osmuser"
password = "pass"

con = psycopg2.connect(
    host=host, port=port, database=database, user=user, password=password)
con.set_client_encoding("UTF8")

bfmap_ways = gpd.read_postgis("select gid, osm_id, source, target, reverse, priority, geom from bfmap_ways;", con)
ways = pd.read_sql_query("select id as osm_id, tags, nodes from ways;", con)
roads = bfmap_ways.merge(ways, on='osm_id')
con.close()


lat = []
lon = []
tms = []


def gps2json(gps_id):
    lat_tmp = lat[gps_id]
    lon_tmp = lon[gps_id]
    tms_tmp = tms[gps_id]
    pt_count = len(lat_tmp)
    js = []
    for i in range(pt_count):
        point = {"point": "POINT({} {})".format(lon_tmp[i], lat_tmp[i]),
                 "time": tms_tmp[i],
                 "id": "\\x0001"}
        js.append(point)
    return js


def match_trip(gps_id):
    dict_req = {"format": "slimjson", "request": gps2json(gps_id)}
    request = json.dumps(dict_req)
    conn_match = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn_match.connect(('127.0.0.1', 1234))
    message = request + '\n'
    conn_match.send(message.encode('utf-8'))
    res = conn_match.recv(1024)
    response = ''
    while res:
        response += res.decode('utf-8')
        res = conn_match.recv(1024)
    conn_match.close()
    # response = res.decode('utf-8')
    res_lines = response.splitlines()  # remain unsolved
    roads_js = res_lines[1]
    trips = json.loads(roads_js)
    road = []
    for trip in trips:
        road.append(trip['road'])
    routes = roads[roads.gid.isin(road)]
    return routes


def handle_request(port, client):
    while True:
        recv_data = client.recv(1024)
        if recv_data:
            recv_content = recv_data.decode('ascii')
            gps_id = int(recv_content)
            lat_tmp = lat[gps_id]
            lon_tmp = lon[gps_id]
            road = match_trip(gps_id)

            match_map = bfmap_ways.explore(color='navajowhite', style_kwds={'opacity': 0})
            gps_point = {'lon': lon_tmp, 'lat': lat_tmp}
            df_gps = pd.DataFrame(gps_point)
            gdf_gps = gpd.GeoDataFrame(df_gps, geometry=gpd.points_from_xy(df_gps.lon, df_gps.lat))
            match_map = gdf_gps.explore(m=match_map)
            match_map = road.explore(m=match_map, color="red")
            file_name = '../VisualServer/gps_map.html'
            match_map.save(file_name)
            print('save complete')
            # file_path = 'file:///Users/arcueid/DeepGTT/VisualServer/gps_map.html'
            # webbrowser.open_new_tab(file_path)
            send_content = 'got it'
            send_data = send_content.encode('ascii')
            client.send(send_data)
        else:
            break


if __name__ == '__main__':
    with h5py.File('./data/h5path/trips_150104.h5', 'r') as file_trips:
        # i = 0
        lat_tmp = []
        lon_tmp = []
        tms_tmp = []
        trips_count = len(file_trips['trip'].keys())
        for i in range(1, trips_count+1):
            if i > 1000:
                break
            key = str(i)
            last_time = float(file_trips['trip'][key]['tms'][0]) - 11
            for x in range(file_trips['trip'][key]['lon'].shape[0]):
                unix_time = file_trips['trip'][key]['tms'][x]
                if unix_time - last_time >= 10:  # remove redundant points
                    lon_tmp.append(file_trips['trip'][key]['lon'][x])
                    lat_tmp.append(file_trips['trip'][key]['lat'][x])
                    f_time = time.localtime(unix_time)
                    str_time = time.strftime('%Y-%m-%d %H:%M:%S', f_time) + '+0800'
                    tms_tmp.append(str_time)
                    last_time = unix_time
            lon.append(lon_tmp.copy())
            lat.append(lat_tmp.copy())
            tms.append(tms_tmp.copy())
            lon_tmp.clear()
            lat_tmp.clear()
            tms_tmp.clear()
            # i += 1

        with open('../gps_count.txt', 'w') as fp:
            fp.write(str(len(lon)))
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        server_socket.bind(('127.0.0.1', 10002))

        server_socket.listen(128)

        print('gps matching server start')
        while True:
            client, port = server_socket.accept()
            sub_thread = threading.Thread(target=handle_request, args=(port, client), daemon=True)

            sub_thread.start()

    server_socket.close()