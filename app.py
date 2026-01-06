import flet as ft
import requests

AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_TEMPLATE = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

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
    page.title = "天気予報アプリ"
    
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    
    page.appbar = ft.AppBar(
        title=ft.Text("日本全国 天気予報", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        center_title=True,
        bgcolor=ft.Colors.INDIGO,
    )

    try:
        area_data = requests.get(AREA_URL).json()
        centers = area_data['centers']
        offices = area_data['offices']
    except Exception as e:
        page.add(ft.Text(f"データ取得エラー: {e}", color="red"))
        return

    weather_column = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True)
    
    main_content = ft.Container(
        content=weather_column,
        padding=20,
        expand=True
    )

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

            def fetch_forecast(e, area_code=code, container=forecast_content):
                container.controls.clear()
                container.controls.append(ft.Row([ft.ProgressRing()], alignment=ft.MainAxisAlignment.CENTER))
                container.update()

                try:
                    url = FORECAST_URL_TEMPLATE.format(area_code=area_code)
                    res = requests.get(url).json()
                    
                    time_series = res[0]['timeSeries'][0]
                    areas = time_series['areas']
                    target_area = areas[0]
                    weathers = target_area['weathers']
                    time_defines = time_series['timeDefines']

                    container.controls.clear()

                    for date_str, weather in zip(time_defines, weathers):
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
                    
                except Exception as err:
                    container.controls.clear()
                    container.controls.append(ft.Text(f"エラーが発生しました: {err}", color="red"))
                
                container.update()

            card = ft.Card(
                elevation=2,
                content=ft.ExpansionTile(
                    title=ft.Text(office_name, weight=ft.FontWeight.W_500),
                    subtitle=ft.Text(f"地域コード: {code}", size=12, italic=True),
                    leading=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.INDIGO_400),
                    text_color=ft.Colors.INDIGO, 
                    controls=[
                        ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.ElevatedButton(
                                    "予報を見る", 
                                    icon=ft.Icons.REFRESH, 
                                    on_click=fetch_forecast,
                                    style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.INDIGO),
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
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
        first_center_code = list(centers.keys())[0]
        update_weather_view(first_center_code)

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                main_content,
            ],
            expand=True,
            spacing=0,
        )
    )

ft.app(target=main)