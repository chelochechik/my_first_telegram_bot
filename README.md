
This bot provides three key commands:
1) /routes_between: a search for actual routes between two stations. The scenario includes the following steps:
- input of departure station
- input of arrival station
- input of date 
- choice of transport type with inline keyboard
Result of a search contains list of routes with info (number of route, departure/arrival time, carrier) and is shown with pagination.

2) /route_stations: a search for route stations. The scenario includes the following steps:
- input of departure station
- input of arrival station
- choice of transport type with inline keyboard
- choice of a route from appropriate routes (they are shown with pagination).
Result of a search is shown as a sequence of stops within the selected route with info (time from start to a stop, stop time) and without pagination.

3) /history: search history of a user (10 latest queries)
