#!/usr/bin/env python

# WS server example that synchronizes state across clients

import asyncio
from asyncio.streams import IncompleteReadError
from dataclasses import dataclass, field
from datetime import datetime
import json
import websockets
from websockets.server import WebSocketServerProtocol as Socket
from typing import List, Union, Dict, Any, Set


import logging

logger = logging.getLogger("websockets.server")
logger.setLevel(logging.ERROR)
logger.addHandler(logging.StreamHandler())


@dataclass
class RoomInfo:
    admin: Socket
    song_uris: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    current_prog: int = 0
    users: Set[Socket] = field(default_factory=set)


class RoomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


# Listener
rooms: Dict[str, RoomInfo] = {}
websocket_room: Dict[Socket, str] = {}


async def notify(websocket: Union[Set[Socket], Socket], event: Dict[str, Any]) -> None:
    try:
        logging.error(event)
        message = json.dumps(event, cls=RoomEncoder)
        if isinstance(websocket, set):
            await asyncio.wait([socket.send(message) for socket in websocket])
        elif isinstance(websocket, Socket):
            await asyncio.wait([websocket.send(message)])
    except Exception as exc:
        logging.error(str(exc))


async def join_room(websocket: Socket, room: str) -> None:
    if room not in rooms:
        await notify(websocket, {"error": "Room doesn't exist"})
        return
    else:
        if websocket_room.get(websocket) == room:
            await notify(websocket, {"error": "Already in the room!"})
            return
        try:
            rooms[room].users.add(websocket)
            websocket_room[websocket] = room
            await receive_queue(websocket)
        except Exception as exc:
            await notify(websocket, {"error": str(exc)})


async def leave_room(websocket: Socket) -> None:
    logging.info("Leaving room")
    room = websocket_room.get(websocket)
    if room:
        del websocket_room[websocket]
        rooms[room].users.remove(websocket)
        if rooms[room].admin == websocket:
            if len(rooms[room].users) > 0:
                logging.info("Kicking all other users")
                await asyncio.wait([leave_room(u) for u in rooms[room].users])


async def receive_queue(websocket: Socket) -> None:
    room = websocket_room.get(websocket)
    if room:
        room_info = rooms[room]
        await notify(
            websocket,
            dict(uris=room_info.song_uris, last_updated=room_info.last_updated),
        )


async def create_room(websocket: Socket, room: str) -> None:
    if room in rooms:
        await notify(websocket, {"error": "room already exists"})
    rooms[room] = RoomInfo(users={websocket}, admin=websocket)
    websocket_room[websocket] = room


async def add_song(websocket: Socket, song_uri: str) -> None:
    try:
        room = websocket_room.get(websocket)
        if not room:
            await notify(
                websocket, {"error": f"Room doesn't exist! {json.dumps(rooms.keys())}"}
            )
        if room:
            room_info = rooms[room]
            if room_info.admin != websocket:
                await notify(websocket, {"error": "Not an admin"})
                return
            else:
                room_info.song_uris.append(song_uri)
                room_info.last_updated = datetime.now()
                await notify(
                    room_info.users,
                    dict(uris=room_info.song_uris, last_updated=room_info.last_updated),
                )
    except Exception as exc:
        await notify(websocket, dict(error=str(exc)))


async def syncer(websocket: Socket, path: str) -> None:
    # websocket joined
    while True:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=30)
            data = json.loads(message)
            if "action" not in data:
                await notify(websocket, {"error": "improperly formed data"})
            if data["action"] == "add_song":
                if data.get("song_uri"):
                    await add_song(websocket, data["song_uri"])
                else:
                    await notify(websocket, {"error": "Song not specified"})
            elif data["action"] == "create_room":
                await create_room(websocket, data["room_name"])
            elif data["action"] == "leave_room":
                await leave_room(websocket)
            elif data["action"] == "join_room":
                if data.get("room_name"):
                    await join_room(websocket, data["room_name"])
                else:
                    await notify(websocket, {"error": "Room name not specified"})
            else:
                logging.error(f"unsupported event: {data}")
        except IncompleteReadError:
            pass
        except asyncio.TimeoutError:
            try:
                logging.error("We timed out! Pinging")
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
            except asyncio.TimeoutError:
                logging.error("We out")
                await leave_room(websocket)
                return
        except json.decoder.JSONDecodeError:
            logging.error(f"Message data improperly encoded: {message}")
        except Exception as exc:
            logging.error(
                f"Leaving room since we don't handle exception '{str(exc)}' correctly."
            )
            await leave_room(websocket)
            return


asyncio.get_event_loop().run_until_complete(websockets.serve(syncer, "0.0.0.0", 6789))
asyncio.get_event_loop().run_forever()
