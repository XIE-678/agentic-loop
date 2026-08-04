from datetime import datetime
from langchain_core.tools import tool
from app.tools.schemas import WeatherInput


@tool(args_schema=WeatherInput)
def get_current_weather(city: str):
    """获取指定城市的当前天气，返回该地区的天气情况以及温度"""
    weather_data = {
        "北京": "晴天，25°C", "上海": "小雨，22°C",
        "东京": "多云，18°C", "深圳": "雷阵雨，28°C",
    }
    return weather_data.get(city, f"没有找到{city}的天气信息")


@tool
def get_my_birthday():
    """获取我的生日"""
    return "2004年十二月十五日"


@tool
def get_history():
    """获取历史事件的信息"""
    return "2004年12月15日发生了小行星爆炸"


@tool
def get_current_time():
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
