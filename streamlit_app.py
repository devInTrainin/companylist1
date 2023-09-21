import math
import json
import warnings

import pandas as pd
import geopandas as gpd
import folium

from branca.element import Figure
from shapely.geometry import Point

import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

# Import the sidebar functions from sidebar.py
from sidebar import create_sidebar_container, update_sidebar_container
import plotly.express as px

# 3.16000, 101.71000: Kuala Lumpur

def read_file(filename, sheetname):
    excel_file = pd.ExcelFile(filename)
    data_d = excel_file.parse(sheet_name=sheetname)
    return data_d

if __name__ == '__main__':
    st.title('Available ITP companies in Malaysia')
    # Create a sidebar container
    sidebar_container = create_sidebar_container()

    file_input = 'MMU ITP List 13_9_9_11.xlsx'
    geojson_file = "msia_district.geojson"

    text_load_state = st.text('Reading files ...')
    with open(geojson_file) as gj_f:
        geojson_data = gpd.read_file(gj_f)

    itp_list_state = read_file(file_input, 0)
    text_load_state.text('Reading files ... Done!')

    map_size = Figure(width=800, height=600)
    map_my = folium.Map(location=[4.2105, 108.9758], zoom_start=6)
    map_size.add_child(map_my)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

    itp_list_state['geometry'] = itp_list_state.apply(lambda x: Point(x['map_longitude'], x['map_latitude']), axis=1)
    itp_list_state = gpd.GeoDataFrame(itp_list_state, geometry='geometry')

    joined_data = gpd.sjoin(geojson_data, itp_list_state, op="contains").groupby(["NAME_1", "NAME_2"]).size().reset_index(
        name="count")

    merged_gdf = geojson_data.merge(joined_data, on=["NAME_1", "NAME_2"], how="left")
    merged_gdf['count'].fillna(0, inplace=True)

    threshold_scale = [0, 1, 2, 4, 8, 16, 32, 64, 128, 200, 300, 400]

    choropleth = folium.Choropleth(
        geo_data=merged_gdf,
        name='choropleth',
        data=merged_gdf,
        columns=['NAME_2', 'count'],
        key_on='feature.properties.NAME_2',
        fill_color='RdYlGn',
        fill_opacity=0.7,
        line_opacity=0.2,
        threshold_scale=threshold_scale,
        line_color='black',
        legend_name='District Counts',
        highlight=False  # Disable the darkened coloration when hovering
    ).add_to(map_my)

    folium.GeoJsonTooltip(fields=['NAME_1', 'NAME_2', 'count'], aliases=['State', 'District', 'Count']).add_to(
        choropleth.geojson)

    text_load_state.text('Plotting ...')
    for itp_data in itp_list_state.to_dict(orient='records'):
        latitude = itp_data['map_latitude']
        longitude = itp_data['map_longitude']
        company_name = itp_data['Company name']
        company_address = itp_data['Company address']
        popup_name = '<strong>' + str(itp_data['Company name']) + '</strong>\n' + str(itp_data['Company address'])
        if not math.isnan(latitude) and not math.isnan(longitude):
            marker = folium.Marker(location=[latitude, longitude], popup=popup_name, tooltip=company_name)
            marker.add_to(map_my)

            # Create a function to update the sidebar with company information when marker is clicked
            def update_sidebar(marker=marker, sidebar_container=sidebar_container,
                               company_name=company_name, company_address=company_address):
                update_sidebar_container(sidebar_container, company_name, company_address)

            # Add a click event to the marker
            marker.add_child(folium.ClickForMarker(popup=update_sidebar))

    # Specify the file name
    file_name = "MMU ITP List 13_9_9_11.xlsx"

    try:
        df = pd.read_excel(file_name, engine='openpyxl')
    except FileNotFoundError:
        st.error(f"File '{file_name}' not found.")

    # Sidebar for state selection
    if df is not None:
        selected_state = st.sidebar.selectbox("Select a State", df['STATE'].unique())
    else:
        selected_state = None

    # Data processing
    if df is not None:
        grouped_data = df.groupby(['STATE', 'CITY']).size().reset_index(name='CompanyCount')
        grouped_data = grouped_data.sort_values(by=['STATE', 'CompanyCount'], ascending=[True, False])

        # Create bar chart
        if selected_state:
            filtered_data = grouped_data[grouped_data['STATE'] == selected_state]
            fig = px.bar(
                filtered_data,
                x='CompanyCount',
                y='CITY',
                orientation='h',
                labels={'CITY': 'City', 'CompanyCount': 'Number of Companies'},
                title=f'Company Distribution per City in {selected_state}'

            )
        else:
            fig = px.bar(
                grouped_data,
                x='CompanyCount',
                y='CITY',
                orientation='h',
                labels={'CITY': 'City', 'CompanyCount': 'Number of Companies'},
                title='Company Distribution per City in Malaysia (Sorted by State and City)'
            )

        # Display the plotly figure

        text_load_state.text('Plotting ... Done!')

        map_my.save('itp_area_map.html')
        # p = open('itp_area_map.html')
        p = open('itp_area_map.html', 'r', encoding='utf-8')
        components.html(p.read(), 1000, 600)
        st.title('Company Per District')
        st.plotly_chart(fig)
