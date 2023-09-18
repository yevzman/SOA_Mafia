from graphene import ObjectType, List, String, Schema, Field, Int, Boolean
from starlette_graphene3 import GraphQLApp, make_graphiql_handler
from fastapi import FastAPI
import uvicorn
import redis
import pickle

redis_server = redis.Redis()
LIVE_GAME_LIST = 'live_games'
LAST_GAME_LIST = 'last_games'
SCOREBOARD = 'scoreboard'


class LiveScoreboard(ObjectType):
    class GameStatus(ObjectType):
        class PlayerObj(ObjectType):
            user_id = Int()
            user_name = String()
            is_mafia = Boolean()
        
        session_id = String()
        players = List(PlayerObj)
        result = String()
    
    standings = List(GameStatus)


class Query(ObjectType):
    get_live_games = List(String)
    get_last_games = List(String)
    get_live_scoreboard = Field(LiveScoreboard, session_id=String())

    def resolve_get_live_games(self, info):
        res = []
        n = redis_server.llen(LIVE_GAME_LIST)
        for i in range(n):
            res.append(redis_server.lindex(LIVE_GAME_LIST, i).decode())
        print('live games:', res)
        return res

    def resolve_get_last_games(self, info):
        res = []
        n = redis_server.llen(LAST_GAME_LIST)
        for i in range(n):
            res.append(redis_server.lindex(LAST_GAME_LIST, i).decode())
        print('last games:', res)
        return res

    def resolve_get_live_scoreboard(self, info, session_id):
        if session_id == '':
            session_id = '*'
        res = []
        for key in redis_server.scan_iter(f"scoreboard:{session_id}"):
            game_status = redis_server.get(key.decode())
            res.append(pickle.loads(game_status))
        return {
            'standings': res
        }



app = FastAPI()
schema = Schema(query=Query)
gql_app = GraphQLApp(schema=schema, on_get=make_graphiql_handler())
app.add_route("/", gql_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6345)