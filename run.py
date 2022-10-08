from fastapi import FastAPI, HTTPException, status, Body
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import config.constants as C
import jmespath
from typing import List
import os

app = FastAPI()

client = MongoClient(
    host="localhost",
    port=27017,
    username=os.environ["MONGODB_USER"],
    password=os.environ["MONGODB_PASS"]
)
db = client.workouts


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# TODO: Simplify DB management


class WorkoutModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    muscle_group: str = Field(...)
    workout_type: str = Field(...)
    reps: int = Field(...)
    weight: int = Field(...)
    date: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "muscle_group": "chest",
                "workout_type": "push-ups",
                "reps": 12,
                "weight": 0,
                "date": "2022-10-03T17:06:16.848605"
            }
        }


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/workout/{muscle_group}",  response_description="List all workouts", response_model=List[WorkoutModel])
async def read_item(muscle_group: str):
    if muscle_group not in C.workouts.keys():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{muscle_group} not valid muscle group")

    query = {"muscle_group": muscle_group}

    workouts = db["workouts"].find(query)

    return [item for item in workouts]

    # raise HTTPException(status_code=404, detail=f"No {id} workouts found")


@app.post("/workout", response_description="Add new workout", response_model=WorkoutModel)
async def create_workout(workout: WorkoutModel = Body(...)):
    workout = jsonable_encoder(workout)
    if workout['muscle_group'] not in C.workouts.keys():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{workout['muscle_group']} not valid muscle group")

    valid_exercises = jmespath.search(f"{workout['muscle_group']}[*].name",
                                      C.workouts)

    if workout['workout_type'] not in valid_exercises:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{workout['workout_type']} not valid workout type for {workout['muscle_group']}")

    # TO-DO: Fix date recording system
    workout["date"] = str(datetime.utcnow())
    new_workout = db["workouts"].insert_one(workout)
    created_workout = db["workouts"].find_one({"_id": new_workout.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_workout)
