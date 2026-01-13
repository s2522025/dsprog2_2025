import flet as ft
import requests
import sqlite3
import datetime

DB_NAME = "weather_app.db"
AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_code TEXT NOT NULL,
            report_date TEXT NOT NULL,
            weather_text TEXT,
            created_at TEXT,
            UNIQUE(area_code, report_date)
        )
    """)
    conn.commit()
    conn.close()

def save_forecasts_to_db(area_code, forecast_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for date_str, weather in forecast_list:
        cursor.execute("""
            INSERT OR REPLACE INTO forecasts (id, area_code, report_date, weather_text, created_at)
            VALUES (
                (SELECT id FROM forecasts WHERE area_code = ? AND report_date = ?),
                ?, ?, ?, ?
            )
        """, (area_code, date_str, area_code, date_str, weather, now))
        
    conn.commit()
    conn.close()
    print(f"DEBUG: Saved {len(forecast_list)} records to DB for area {area_code}")

def get_forecasts_from_db(area_code):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT report_date, weather_text, created_at 
        FROM forecasts 
        WHERE area_code = ? 
        ORDER BY report_date ASC
    """, (area_code,))
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_weather_icon(text):
    if "晴" in text:
        return ft.Icons.WB_SUNNY, ft.Colors.ORANGE
    elif "雨" in text:
        return ft.Icons.WATER_DROP, ft.Colors.BLUE
    elif "雪" in text:
        return ft.Icons.AC_UNIT, ft.Colors.CYAN
    elif "曇" in text:
        return ft.Icons.CLOUD, ft.Colors.GREY
    else:
        return ft.Icons.WB_CLOUDY_OUTLINED, ft.Colors.BLUE_GREY

def main(page: ft.Page):
    init_db()

    page.title = "天気予報アプリ"
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    
    page.appbar = ft.AppBar(
        title=ft.Text("日本全国 天気予報", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        center_title=True,
        bgcolor=ft.Colors.INDIGO_800,
    )

    try:
        area_data = requests.get(AREA_URL).json()
        centers = area_data['centers']
        offices = area_data['offices']
    except Exception as e:
        page.add(ft.Text(f"エリアデータ取得エラー: {e}", color="red"))
        return

    weather_column = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True)
    main_content = ft.Container(content=weather_column, padding=20, expand=True)

    def render_forecasts(container, data_source_text, forecasts):
        container.controls.clear()
        
        container.controls.append(
            ft.Text(f"データソース: {data_source_text}", size=12, color=ft.Colors.GREY)
        )

        if not forecasts:
            container.controls.append(ft.Text("データがありません"))
            container.update()
            return

        for date_str, weather, *rest in forecasts:
            date_display = date_str.split("T")[0]
            
            icon_data, icon_color = get_weather_icon(weather)

            tile = ft.ListTile(
                leading=ft.Icon(icon_data, color=icon_color, size=30),
                title=ft.Text(date_display, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(weather, size=12, color=ft.Colors.GREY_700),
                bgcolor=ft.Colors.BLUE_50,
            )
            container.controls.append(
                ft.Container(content=tile, border_radius=10, margin=ft.margin.only(bottom=5))
            )
        container.update()

    def update_weather_view(center_code):
        weather_column.controls.clear()
        center_name = centers[center_code]['name']
        
        weather_column.controls.append(
            ft.Text(f"{center_name}の天気", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900)
        )
        weather_column.controls.append(ft.Divider())

        target_offices = {k: v for k, v in offices.items() if v['parent'] == center_code}

        for code, info in target_offices.items():
            office_name = info['name']
            forecast_content = ft.Column()

            def fetch_and_save(e, area_code=code, container=forecast_content):
                container.controls.clear()
                container.controls.append(ft.ProgressRing())
                container.update()

                try:
                    url = FORECAST_URL_TEMPLATE.format(area_code=area_code)
                    res = requests.get(url).json()
                    
                    time_series = res[0]['timeSeries'][0]
                    areas = time_series['areas']
                    target_area = areas[0]
                    weathers = target_area['weathers']
                    time_defines = time_series['timeDefines']

                    forecast_list = []
                    for d, w in zip(time_defines, weathers):
                        d_clean = d.split("T")[0]
                        forecast_list.append((d_clean, w))
                    
                    save_forecasts_to_db(area_code, forecast_list)

                    db_rows = get_forecasts_from_db(area_code)
                    render_forecasts(container, "JMA API -> DB保存 -> 表示", db_rows)

                except Exception as err:
                    container.controls.clear()
                    container.controls.append(ft.Text(f"エラー: {err}", color="red"))
                    container.update()

            def load_from_db_only(e, area_code=code, container=forecast_content):
                db_rows = get_forecasts_from_db(area_code)
                if db_rows:
                    render_forecasts(container, "ローカルDB参照", db_rows)
                else:
                    container.controls.clear()
                    container.controls.append(ft.Text("DBにデータがありません。APIから取得してください。", color="red"))
                    container.update()

            card = ft.Card(
                elevation=2,
                content=ft.ExpansionTile(
                    title=ft.Text(office_name, weight=ft.FontWeight.W_500),
                    subtitle=ft.Text(f"地域コード: {code}"),
                    leading=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.INDIGO_400),
                    text_color=ft.Colors.INDIGO,
                    controls=[
                        ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.ElevatedButton(
                                        "APIから取得＆保存", 
                                        icon=ft.Icons.CLOUD_DOWNLOAD, 
                                        on_click=fetch_and_save,
                                        style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO, color=ft.Colors.WHITE)
                                    ),
                                    ft.OutlinedButton(
                                        "DBデータを見る", 
                                        icon=ft.Icons.STORAGE, 
                                        on_click=load_from_db_only
                                    ),
                                ]),
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                forecast_content
                            ])
                        )
                    ]
                )
            )
            weather_column.controls.append(card)
        
        page.update()

    def rail_changed(e):
        selected_index = e.control.selected_index
        keys = list(centers.keys())
        if 0 <= selected_index < len(keys):
            update_weather_view(keys[selected_index])

    rail_destinations = []
    for c_code, c_info in centers.items():
        rail_destinations.append(
            ft.NavigationRailDestination(
                icon=ft.Icons.MAP_OUTLINED,
                selected_icon=ft.Icons.MAP_SHARP,
                label=c_info['name'],
                padding=10,
            )
        )

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=rail_destinations,
        on_change=rail_changed,
        bgcolor=ft.Colors.BLUE_GREY_50,
    )

    if centers:
        update_weather_view(list(centers.keys())[0])

    page.add(
        ft.Row(
            [rail, ft.VerticalDivider(width=1, color=ft.Colors.GREY_300), main_content],
            expand=True,
            spacing=0,
        )
    )

ft.app(target=main)