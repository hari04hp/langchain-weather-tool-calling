from uuid import UUID
from langchain_core.outputs import LLMResult
from langchain_core.tools import tool
import requests
import streamlit as st
import json
import api_key #my local file
import os
from langchain.agents import create_tool_calling_agent, AgentExecutor, create_structured_chat_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, ChatMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.base import BaseCallbackHandler
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.chat_message_histories import SQLChatMessageHistory
from openai import AuthenticationError
from langchain.memory import ConversationBufferMemory
import pandas as pd
from streamlit_lottie import st_lottie


df = pd.read_csv('country_code.csv', header = 0)
df['name'] = df['name'].str.upper()

def get_response(url):
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        print("Error:", response.status_code)
    return data

@tool
def get_geo_data_from_city_or_zip(zip_code=None, country_name=None, city_name=None,):
    '''Get Geographical data with latitude and longitude using zip code and country name or city name and country name combinations. When zip code is passed, country name must be present.'''
    try:
        country_code = None
        if country_name is not None:
            country_code = (df[(df['name'] == country_name.upper()) | (df['alpha-2'] == country_name.upper()) | (df['alpha-3'] == country_name.upper())]['alpha-2']).iloc[0]
        if city_name is None and zip_code is None:
            return "Need city name or zip code"
        if zip_code is not None:
            url = f'http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},{country_code}&appid={api_key.OPEN_WEATHER_API_KEY}'
            geo_data = get_response(url)
        elif city_name is not None:
            url = f'http://api.openweathermap.org/geo/1.0/direct?q={city_name},{country_code}&limit=1&appid={api_key.OPEN_WEATHER_API_KEY}'
            geo_data = get_response(url)[0]
        else:
            return "Wrong"
        return geo_data
    except:
        return "Something is wrong in get geo data tool. There is a chance that zipcode is given without country name. Get that from the user."

@tool
def get_weather(geo_data, is_forecast, local_requested_timestamp):
    '''Getting current weather or forecast for the upcoming 5 days (not more than that) at a specified geo location. Geo data must be received from get_geo_data_from_city_or_zip before calling this tool. If it's a forecast, we MUST need the local_requested_timestamp generated from get_local_datetime tool.'''

    try:
        if not is_forecast:
            url = f'https://api.openweathermap.org/data/2.5/weather?lat={geo_data['lat']}&lon={geo_data['lon']}&appid={api_key.OPEN_WEATHER_API_KEY}&units=imperial'
            data = get_response(url)
            return data
        else:
            url = f'https://api.openweathermap.org/data/2.5/forecast?lat={geo_data['lat']}&lon={geo_data['lon']}&appid={api_key.OPEN_WEATHER_API_KEY}&units=imperial'
            data = get_response(url)
            only_date_json = {}
            value = data["list"][0]["dt"]
            for i in data["list"]:
                if abs(i["dt"] - local_requested_timestamp) > value:
                    break
                else:
                    value = abs(i["dt"] - local_requested_timestamp)
                    only_date_json = i
                    print(value)
            
            return only_date_json
    except:
        return "Tool has been called in the wrong order. Call get_geo_data_from_city_or_zip with relevant parameters first."

@tool
def get_local_datetime(geo_data, days = 0, hour = 10):
    '''If a future weather forecast is queried, this tool must be called and the returned value MUST be used in get_weather function's local_requested_timestamp variable.'''
    from datetime import datetime, timedelta
    from timezonefinder import TimezoneFinder
    import pytz
    obj = TimezoneFinder()
    latitude =  geo_data["lat"]
    longitude = geo_data["lon"]
    local_timezone= obj.timezone_at(lng=longitude, lat=latitude)
    local_requested_datetime = (datetime.now(pytz.timezone(local_timezone)) + timedelta(days = days))
    if days != 0:
        local_requested_datetime = local_requested_datetime.replace(hour=hour, minute=0, second=0)
    return local_requested_datetime.timestamp()

# @tool
# def get_weather_flow():


class StreamHandler(BaseCallbackHandler):
    '''Class for displaying the streaming the response as soon as it's received.'''
    def __init__(self, container: st.delta_generator.DeltaGenerator, initial_text: str = ""):
        self.container = container
        self.text = initial_text
        self.run_id_ignore_token = None

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if self.run_id_ignore_token == kwargs.get("run_id", False):
            return
        self.text += token
        self.container.markdown(self.text)

st.set_page_config(page_title="Weather App with Langchain Tool Calling", page_icon="🌤️", layout="wide")
st.markdown("""
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css" rel="stylesheet">
            """, unsafe_allow_html=True)

st.header("Weather App with Langchain Tool Calling 🌤️")
with st.container():
    openai_api_key = st.sidebar.text_input(
        label="Enter your OpenAI API key", type="password"
    )
    username = st.sidebar.text_input(
        label="Enter your username"
    )
    if not openai_api_key.startswith('sk-') or not username:
        st.info("Please add your OpenAI API key in the sidebar on the left to use the agent. Username is also necessary to maintain and retrieve your chat history. Please give a unique id or name if possible. To open sidebar in the mobile, click on the arrow at the top left.", icon = "ℹ")
    
    button_status = st.sidebar.button("Clear message history")
    os.environ['OPENAI_API_KEY'] = openai_api_key

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

python_lottie = load_lottieurl("https://assets6.lottiefiles.com/packages/lf20_2znxgjyt.json")
my_sql_lottie = load_lottieurl("https://assets4.lottiefiles.com/private_files/lf30_w11f2rwn.json")
ml_lottie = load_lottieurl("https://lottie.host/30f7a673-5d1a-4a83-b694-0361c985b506/Ik5pQjtkjb.json")

with st.container():
    st.sidebar.image("images/my-image-2.jpg")
    st.sidebar.title("Haripriya Rajendran 🤓")
    st.sidebar.header("Data Scientist 👩‍💻")
    
    with st.sidebar:
        columns = st.columns(2)
        columns[i:=0].markdown("""
        <a href="https://github.com/hari04hp" class="text-decoration-none text-light"><i class="fab fa-github contact-icons1" style="font-size: 50px;"></i></a>""",unsafe_allow_html=True,)
        columns[i:=i+1].markdown("""
        <a href="https://www.linkedin.com/in/haripriyar" class="text-decoration-none text-light"><i class="fab fa-linkedin contact-icons1" style="font-size: 50px;"></i></a>""",unsafe_allow_html=True,)
    
    with st.sidebar:
        dict_of_lotties = {"python": python_lottie, "mysql": my_sql_lottie, "ml": ml_lottie}
        columns = st.columns(len(dict_of_lotties))
        for index,column in enumerate(columns):
            with column:
                st_lottie(dict_of_lotties[list(dict_of_lotties.keys())[index]], height=70,width=70, key=list(dict_of_lotties.keys())[index], speed=2.5)

if username and openai_api_key.startswith('sk-'):
    db_path = 'local_sqlite_db.db'
    msgs = SQLChatMessageHistory(
        session_id=username,
        connection_string="sqlite:///" + db_path  # This is the SQLite connection string
    )

    if len(msgs.messages) == 0 or button_status:
        msgs.clear()
        msgs.add_ai_message("How can I help you?")

    avatars = {"human": "user", "ai": "assistant"}
    for msg in msgs.messages:
        st.chat_message(avatars[msg.type]).write(msg.content)

    tools = [get_geo_data_from_city_or_zip, get_local_datetime,get_weather]
    # llm = ChatOpenAI(model="gpt-3.5-turbo-0125", streaming=True)
    llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
    llm_with_tools = llm.bind_tools(tools)

    #prompt should contain ("placeholder", "{agent_scratchpad}"), so I'm rewriting the prompt here
    examples = [
        HumanMessage(
            "Get weather at Rocklin for tomorrow at 6PM", name="example_user"
        ),
        AIMessage(
            "",
            name = "example_assistant",
            tool_calls = [
                {"name": "get_geo_data_from_city_or_zip", "args": {"city_name": "Rocklin"}, "id": "3"}
            ]
        ),
        ToolMessage('''{
            "name": "Rocklin",
            "lat": 38.7907339,
            "lon": -121.2357828,
            "country": "US",
            "state": "California"
        }''', tool_call_id="3"),
        AIMessage(
            "",
            name = "example_assistant",
            tool_calls = [
                {"name": "get_local_datetime", "args": {"geo_data": {'name': 'Rocklin','lat': 38.7907339,'lon': -121.2357828,'country': 'US','state': 'California'}, "days" : 1, "hour" : 18}, "id": "4"}
            ]
        ),
        ToolMessage(1714352798.281548, tool_call_id="4"),
        AIMessage(
            "",
            name="example_assistant",
            tool_calls=[
                {"name": "get_weather", "args": {"geo_data":{'name': 'Rocklin','lat': 38.7907339,'lon': -121.2357828,'country': 'US','state': 'California'}, "is_forecast" : 1, "local_requested_timestamp" :1714352798.281548}, "id": "5"}
            ],
        ),
        ToolMessage('''{'dt': 1714327200,
            'main': {'temp': 65.95,
            'feels_like': 64.63,
            'temp_min': 65.95,
            'temp_max': 65.95,
            'pressure': 1019,
            'sea_level': 1019,
            'grnd_level': 1009,
            'humidity': 51,
            'temp_kf': 0},
            'weather': [{'id': 801,
            'main': 'Clouds',
            'description': 'few clouds',
            'icon': '02d'}],
            'clouds': {'all': 11},
            'wind': {'speed': 5.73, 'deg': 294, 'gust': 6.26},
            'visibility': 10000,
            'pop': 0,
            'sys': {'pod': 'd'},
            'dt_txt': '2024-04-28 18:00:00'}''', tool_call_id = "5"),
        AIMessage(
            "The temperature at Rocklin tommorow around 6 PM is 65.95 F with few clouds .",
            name="example_assistant",
        ),
    ]

    system = """You are bad at predicting weather but an expert at using tools those give you a current weather or a forecast report. DO NOT ANSWER YOURSELF, ALWAYS USE TOOLS. If the user queries zipcode without a country name, ask for the country name or code. If the query is about a forecast, take is_forecast as 1 and always use the generated timestamp from get_local_datetime tool in get_weather function.
    Use past tool usage order as an example on how to correctly use the tools. If the query asks for weather information for a date which is beyond 5 days from today, only then tell them that you only have information for the next five days, otherwise don't tell."""

    few_shot_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            *examples,
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}")
        ]
    )

    agent = create_tool_calling_agent(llm_with_tools, tools, few_shot_prompt)
    memory = ConversationBufferMemory(memory_key="chat_history",chat_memory=msgs, return_messages=True)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, memory=memory)
    

    # print("Output:  ", agent_ai_msg)
    if user_query := st.chat_input(placeholder="Ask my weather assistant the weather at any location. You can query with a city name or a zip code with country name!"):
        st.chat_message("user").write(user_query)

        with st.chat_message("assistant"):
            container = st.empty()
            stream_handler = StreamHandler(container)
            st_callback = StreamlitCallbackHandler(st.container())
            response = agent_executor.invoke(
                {"query" : user_query},  {"callbacks": [st_callback, stream_handler]} #callbacks should be in dictionary
            )
            st.write(response["output"])