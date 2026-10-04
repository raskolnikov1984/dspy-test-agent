import os
import dspy

from agent import DSPyAirlineCustomerService
from tools import *

agent = dspy.ReAct(
    DSPyAirlineCustomerService,
    tools=[
        fetch_flight_info,
        pick_flight,
        book_flight,
        fetch_itinerary,
        cancel_itinerary,
        get_user_info,
        file_ticket,
    ],
)

lm = dspy.LM(
    "deepseek/deepseek-chat",
    api_key="",
    temperature=0.0,
    max_tokens=4000,
)

dspy.configure(lm=lm)
