## About
Published at https://haripriya-rajendran-weather-agent.streamlit.app/
This portfolio project showcases my ability to implement tool calling through a LangChain agent. I used the OpenWeather API and created a chat interface where the GPT-4o-mini LLM answers natural language queries about current weather and 5-day forecasts for any city name or zip code with country name. The functions to get weather using API are bound as tools to the GPT-4o-mini LLM through LangChain. 

## How to run locally:
1. pip install -r requirements.txt
2. streamlit run weather_api_tool_agent.py
Create an api_key.py file in the project directory and add:

* OPEN_WEATHER_API_KEY = '\<your-open-weather-api-key\>'
* OPENAI_API_KEY='\<your-open-api-key\>'

## References 
- https://blog.langchain.dev/tool-calling-with-langchain/
- https://python.langchain.com/docs/modules/model_io/chat/function_calling/?ref=blog.langchain.dev
- https://openweathermap.org/current
- https://openweathermap.org/forecast5

## Demo videos and screen captures 
Demo videos and screen captures are under demo/ folder
1. Demo_1.mov => Shows how the weather app gives the forecast for a particular location's relative time. It takes the location into account, calculates the exact timestamp of the future forecast requested, converts to unix timestamp and takes the closest weather for that day. Here in this example, we have requested Chennai's weather for the next day 6PM. Today's date in Chennai is 29th April, 2024. So, it takes 30th April, 2024 6PM in Chennai's local time, calculates the timestamp, takes the nearest unix timestamp which is 30th April, 2024 5:30 PM.
2. Demo_2.mov => Shows how the weather app gives the current weather even when asked in Natural Language format.
3. Capture_1.png => Sample weather call with Langchain's thinking chain displayed.
4. Capture_2.png => Shows how the weather app expects a country name when only zip code is queried.
