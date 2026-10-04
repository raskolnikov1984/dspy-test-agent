#!/usr/bin/env python3
import random
import string

from database import (
    flight_database,
    itinerary_database,
    ticket_database,
    user_database,
)
from schemes import Date, Flight, Itinerary, Ticket, UserProfile
from tool_registry import registry

"""
Define Tools
We need to prepare a list of tools so that the agent can behave like a human airline service agent:

1. fetch_flight_info: get flight information for certain dates.
2. pick_flight: pick the best flight based on some criteria.
3. book_flight: book a flight on behalf of the user.
4. fetch_itinerary: get the information of a booked itinerary.
5. cancel_itinerary: cancel a booked itinerary.
6. get_user_info: get users’ information.
7. file_ticket: file a backlog ticket to have human assist.
"""


@registry.register
def fetch_flight_info(date: Date, origin: str, destination: str):
    """Fetch flight information from origin to destination on the given date"""
    flights = []

    for flight_id, flight in flight_database.items():
        if (
            flight.date_time.year == date.year
            and flight.date_time.month == date.month
            and flight.date_time.day == date.day
            and flight.origin == origin
            and flight.destination == destination
        ):
            flights.append(flight)
    if len(flights) == 0:
        raise ValueError("No matching flight found!")
    return flights


@registry.register
def fetch_itinerary(confirmation_number: str):
    """Fetch a booked itinerary information from database"""
    return itinerary_database.get(confirmation_number)


@registry.register
def pick_flight(flights: list[Flight]):
    """Pick up the best flight that matches users' request. we pick the shortest, and cheaper one on ties."""
    sorted_flights = sorted(
        flights,
        key=lambda x: (
            x.get("duration") if isinstance(x, dict) else x.duration,
            x.get("price") if isinstance(x, dict) else x.price,
        ),
    )
    return sorted_flights[0]


def _generate_id(length=8):
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


@registry.register
def book_flight(flight: Flight, user_profile: UserProfile):
    """Book a flight on behalf of the user."""
    confirmation_number = _generate_id()
    while confirmation_number in itinerary_database:
        confirmation_number = _generate_id()
    itinerary_database[confirmation_number] = Itinerary(
        confirmation_number=confirmation_number,
        user_profile=user_profile,
        flight=flight,
    )
    return confirmation_number, itinerary_database[confirmation_number]


@registry.register
def cancel_itinerary(confirmation_number: str, user_profile: UserProfile):
    """Cancel an itinerary on behalf of the user."""
    if confirmation_number in itinerary_database:
        del itinerary_database[confirmation_number]
        return
    raise ValueError(
        "Cannot find the itinerary, please check your confirmation number."
    )


@registry.register
def get_user_info(name: str):
    """Fetch the user profile from database with given name."""
    return user_database.get(name)


@registry.register
def file_ticket(user_request: str, user_profile: UserProfile):
    """File a customer support ticket if this is something the agent cannot handle."""
    ticket_id = _generate_id(length=6)
    ticket_database[ticket_id] = Ticket(
        user_request=user_request,
        user_profile=user_profile,
    )
    return ticket_id
