from datetime import datetime
from langchain_core.tools import tool


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
