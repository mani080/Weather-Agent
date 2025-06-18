from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from typing import List, TypedDict
import requests
import os
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from typing import Annotated, Literal, TypedDict
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage ,AIMessage ,SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from langchain_core.tools import Tool
import requests
import datetime
from langchain_core.runnables import RunnableLambda

# class GraphState(TypedDict):
#     messages: List[BaseMessage]
from dotenv import load_dotenv
load_dotenv()


WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


import requests

#Replace with your actual API key
#WEATHER_API_KEY = "fa032005413e40c981d81949251706"

def get_weather_from_weatherapi(city: str) -> str:
    """Weather data provider"""
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days=3&aqi=no&alerts=no"
        response = requests.get(url)
        
        # Ensure valid JSON
        if response.status_code != 200:
            return f"❗ API request failed with status code {response.status_code}"
        
        data = response.json()

        if "error" in data:
            return f"❗ API Error: {data['error'].get('message', 'Unknown error')}"

        location = data["location"]
        current = data["current"]
        forecast = data["forecast"]["forecastday"]

        report = (
            f"📍 {location['name']}, {location['country']}\n"
            f"🌡️ Temp: {current['temp_c']}°C (Feels like {current['feelslike_c']}°C)\n"
            f"💧 Humidity: {current['humidity']}% | ☁️ Cloud: {current['cloud']}%\n"
            f"🌬️ Wind: {current['wind_kph']} kph\n"
            f"🌤️ Condition: {current['condition']['text']}\n\n"
            f"🗓️ Forecast:\n"
        )

        for day in forecast:
            date = day["date"]
            day_data = day["day"]
            report += (
                f"{date}: 🌡️ {day_data['avgtemp_c']}°C, 🌧️ {day_data['condition']['text']}, "
                f"💧 Humidity: {day_data['avghumidity']}%, 🌬️ Wind: {day_data['maxwind_kph']} kph\n"
            )

        return report

    except Exception as e:
        return f"❗ Error: {str(e)}"
    

# @tool
# def weather_search(city: str) -> AIMessage:
#     """
#     Tool to get weather forecast using WeatherAPI.
#     Expects a city name as input.
#     """
#     report = get_weather_from_weatherapi(city)
#     return AIMessage(content=report)

##
tools=[get_weather_from_weatherapi]

from testagents.chat_llm import llm


llm_with_tools = llm.bind_tools([get_weather_from_weatherapi])


def call_model(state:MessagesState):
    question=state["messages"][0]
    response=llm_with_tools.invoke(question)
    return {"messages":[response]}



def router_function(state: MessagesState):
    message=state["messages"]
    last_message=message[-1]
    if last_message.tool_calls:
        return "tools"
    return END

tool_node=ToolNode(tools)

def build_weather_graph():
    workflow = StateGraph(MessagesState)

    workflow.add_node("assistant",call_model)
    workflow.add_node("myweathertool",tool_node)

    #workflow.set_entry_point("chat_node")
    workflow.add_edge(START, "assistant")

    workflow.add_conditional_edges("assistant",
                               router_function,
                               {"tools": "myweathertool", END: END})
    workflow.add_edge("myweathertool","assistant")
    return workflow.compile()

app = build_weather_graph()

