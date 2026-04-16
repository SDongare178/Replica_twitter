from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import starlette.status as status
import datetime
from bson import ObjectId
from azure.storage.blob import BlobServiceClient, AccessPolicy, ContainerSasPermissions, PublicAccess


#connection string to out MongoDB Nosql database
uri = "mongodb+srv://sudhanshdongare178_db_user:pjZRFup5KsigUq6@cluster0.7ubbhoc.mongodb.net/?appName=Cluster0"

#create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

#send a ping to confirm a successful conncetion to the database
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

#define the app that will contain all of our routing for the FastAPI
app = FastAPI()

#open up a database in MongoDB and open the collections we will need
db = client["A2-3165686"]

#crate the followind tables in db
users_collection = db["users"]
tweets_collection = db["tweets"]


#we need a request object to be able to talk to firebase for verifying user logins
firebase_request_adapter = requests.Request()
azure_connection_string = (

)
azure_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
azure_container_name = "twitter-container"
azure_service_client = azure_service_client.get_container_client(azure_container_name)

azure_container_client = azure_service_client.get_container_client(azure_container_name)
try:
    azure_service_client.create_container()
except Exception:
    print('container exists')

container_service_client = azure_service_client.get_container_client(azure_container_name)
existing_policies = container_service_client.get_container_access_policy()
access_policy = AccessPolicy(permission=ContainerSasPermissions(read=True), expiry=datetime.now() + timedelta(hours=24), start=datetime.now()- timedelta(minutes=1))
identidiers = {'read': access_policy}
existing_policies['public_access']= 'blob'

azure_container_client.set_container_access_policy(signed_identifiers=identidiers, public_access=PublicAccess.CONTAINER)

#define the static and directories
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

#function that we will use to validate an id_token, will return the user_token if valid, None if not 
def validateFirebaseToken(id_token):
    #if we dont have a token then return None
    if not id_token:
        return None 

    #try to validate the token if this fails with an exception then this will remain None so just return at the end 
    # if we get an exception then log the exception before returning
    user_token = None  
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as err:
        #dump this message to the console as it will be displayed on the template use for debugging Use for debugging but if you are 
        # building for production you should handle this more graefully
        print(str(err))

    #retutn the token to the caller
    return user_token


'''def checkClash(day_id, start_time, end_time, repeat_booking_id=None):

    #convert time into datetime
    start = datetime.datetime.strptime(start_time, "%H:%M")
    end = datetime.datetime.strptime(end_time, "%H:%M")

    #check for invalid 
    if start >= end:
        return True

    bookings = bookings_collection.find({"day_id": day_id})

    for booking in bookings:
        #skip same booking
        if repeat_booking_id and str(booking["_id"]) == repeat_booking_id:
            continue

        start_present = datetime.datetime.strptime(booking["start_time"], "%H:%M")
        end_present = datetime.datetime.strptime(booking["end_time"], "%H:%M")

        if not (end <= start_present or start >= end_present):
            return True

    return False'''
def addFile(file, path):
    if path =='':
        azure_container_client.upload_blob(name=file.filename, data=file.read(), overwrite=True)
    else:
        if path[-1] == '/':
            azure_container_client.upload_blob(name=path+file.filename, data=file.file.read(), overwrite=True)

def listBlobs():
    blob_names = []
    for blob in azure_container_client.list_blobs():
        blob_names.append(blob.name)

    return blob_names    

#user get function
def getUser(user_token):
    user = users_collection.find_one({"user_id": user_token["user_id"]})

    if not user:
        # first time login
        return None

    return user

#root of the application that will be responsible for login and logout and display the details of the user 
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    #query firebase for the requesr token we will also decide a bunch if other variables here as we will need them 
    # for rendering the template at the end We have an error_messafe there is case you want to output an error to 
    # the user in the template
    id_token = request.cookies.get('token')
    user_token = None

    ##azurite
    blob_names=listBlobs()
    #azurite urls
    urls = []
    for blob in blob_names:
        blob_client = azure_container_client.get_blob_client(blob=blob)
        urls.append(blob_client.url)
    

    #check if we have a valid firebase login if not return the template with empty dara as we will show the login boc
    if id_token:
        user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('main.html', {
            'request': request,
            'user': None,
            'tweets': []
            })

    user = getUser(user_token)

    #setting username if new
    if not user:
        return RedirectResponse("/new-username", status_code=302)
    
    tweets = list(tweets_collection.find({"user_id": user_token["user_id"]}).sort("created_at", -1))

 

    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_id": user_token["user_id"],
        "error_message": None  
    })


#method to add a new room to the database
@app.post('/add-tweet', response_class=HTMLResponse)
async def addTweet(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    form = await request.form()
    user_name = form['user_name']
    users = list(users_collection.find())

    #tweet_name = room_name.strip()
    
    

    tweets_collection.insert_one({
        "owner_id": user_token["user_id"]
         })

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

#another version of the user route but this will accept a post request and will only redirect when finished

#method to book a booking for available rooms
"""@app.post('/book-room', response_class=RedirectResponse)
async def bookRoom(request: Request):
    #there should be a token Validate it and if invalid then return to /
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    

    form = await request.form()
    room_id = form['room_id']
    date = form['date']
    start_time = form['start_time']
    end_time = form['end_time']

    rooms = list(rooms_collection.find())
    all_days = list(days_collection.find())
    room_map = {str(room["_id"]): room["name"] for room in rooms}
    day_map  = {str(day["_id"]): day for day in all_days}

    bookings = list(bookings_collection.find({"user_id": user_token["user_id"]}))

    def error(msg):
        return templates.TemplateResponse("main.html", {
            "request": request,
            "user_token": user_token,
            "rooms": rooms,
            "days": all_days,
            "bookings": bookings,
            "room_map": room_map,   
            "day_map": day_map, 
            "error_message": msg
        })

    #time validations
    try:
        start = datetime.datetime.strptime(start_time, "%H:%M")
        end   = datetime.datetime.strptime(end_time,   "%H:%M")
    except ValueError:
        return error("Invalid time format.")

    if start >= end:
        return error("Start time must be before end time.")

    if start.hour < 9 or end.hour > 18 or (end.hour == 18 and end.minute > 0):
        return error("Bookings must be between 09:00 and 18:00.")

    #get or create day if doesnt exist
    day = days_collection.find_one({"room_id": ObjectId(room_id), "date": date})
    if not day:
        day_id = days_collection.insert_one({
            "room_id": ObjectId(room_id), "date": date
        }).inserted_id
    else:
        day_id = day["_id"]

    #calling method to check id clashes with other boooking
    if checkClash(day_id, start_time, end_time):
        return error("That time slot clashes with an existing booking. Please choose another time.")

    bookings_collection.insert_one({
        "day_id": day_id,
        "user_id": user_token["user_id"],
        "start_time": start_time,
        "end_time": end_time
    })

    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
#method to delete a room     
@app.post("/delete-room")
async def deleteRoom(request: Request):
    # Get user token
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)


    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    form = await request.form()
    room_id = form['room_id']

    room = rooms_collection.find_one({"_id": ObjectId(room_id)})

    if not room:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    #if this is owner of the room thencontinue else root back
    if room["owner_id"] != user_token["user_id"]:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    #get all days for room
    this_room_days = list(days_collection.find({"room_id": ObjectId(room_id)}))

    #if any booking exist
    for day in this_room_days:
        if bookings_collection.find_one({"day_id": day["_id"]}):
            return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    #deletee room
    rooms_collection.delete_one({"_id": ObjectId(room_id)})
    days_collection.delete_many({"room_id": ObjectId(room_id)})

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


##delete booking
@app.post("/delete-booking")
async def deleteBooking(request: Request):

    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


    form = await request.form()
    booking_id = form['booking_id']

    bookings_collection.delete_one({
        "_id": ObjectId(booking_id),
        "user_id": user_token["user_id"]
    })
    

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

##edit bookings
@app.get('/edit-booking/{booking_id}', response_class=HTMLResponse)
async def editBooking(request: Request, booking_id: str):

    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    
    booking = bookings_collection.find_one({
        "_id": ObjectId(booking_id),
        "user_id": user_token["user_id"]
        })
    if not booking:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    day = days_collection.find_one({"_id": booking["day_id"]})

    return templates.TemplateResponse("editBooking.html", {
        "request": request,
        "booking": booking,
        "day": day
    })

##booking udate
@app.post("/edit-booking")
async def postEditBooking(request: Request):
    #there should be a token Validate it and if invalid then return to /
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    form = await request.form()
    booking_id = form['booking_id']
    date = form['date']
    start_time = form['start_time']
    end_time = form['end_time']


    booking = bookings_collection.find_one({
        "_id": ObjectId(booking_id),
        "user_id": user_token["user_id"]
        })
    if not booking:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    day = days_collection.find_one({
        "_id": booking["day_id"]
        })
    if not day:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    
    try:
        start = datetime.datetime.strptime(start_time, "%H:%M")
        end   = datetime.datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    if start >= end:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    if start.hour < 9 or end.hour > 18 or (end.hour == 18 and end.minute > 0):
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    new_day = days_collection.find_one({
        "room_id": day["room_id"],
        "date": date
    })

    if not new_day:
        new_day_id = days_collection.insert_one({
            "room_id": day["room_id"],
            "date": date
        }).inserted_id
    else:
        new_day_id = new_day["_id"]

    if checkClash(new_day_id, start_time, end_time, booking_id):
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    # update booking
    bookings_collection.update_one(
        {"_id": ObjectId(booking_id),
        "user_id": user_token["user_id"]},
        {
            "$set": {
                "day_id": new_day_id,
                "start_time": start_time,
                "end_time": end_time
            }
        }
    )

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


##filter for days
@app.post("/filter-by-day")
async def filterByDay(request: Request):
    #there should be a token Validate it and if invalid then return to /
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    form = await request.form()
    date = form['date']

    rooms = list(rooms_collection.find())
    days = list(days_collection.find({"date": date}))

    day_id = [day["_id"] for day in days]
    
    bookings = list(bookings_collection.find({
        "day_id": {"$in":day_id},
        "user_id": user_token["user_id"]
    }).sort("start_time", 1))
    
    all_days = list(days_collection.find())
    room_map = {str(room["_id"]): room["name"] for room in rooms}
    day_map  = {str(day["_id"]): day for day in all_days}

    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "rooms": rooms,
        "days": all_days,
        "bookings": bookings,
        "room_map": room_map,
        "day_map": day_map,
        "filtered_date": date,
        "error_message": None
    })

#function to calculate 5 day occupancy
def occupancyPercent(room_id):

    result = []
    today = datetime.date.today()

    for i in range(5):
        current_day = str(today + datetime.timedelta(days=i)) 

        day = days_collection.find_one({
            "room_id": ObjectId(room_id),
            "date": current_day
        })

        total_minutes = 0

        if day:
            bookings = bookings_collection.find({"day_id": day["_id"]})

            for booking in bookings:
                start_time = datetime.datetime.strptime(booking["start_time"], "%H:%M")
                end_time = datetime.datetime.strptime(booking["end_time"], "%H:%M")

                total_minutes += (end_time - start_time).seconds / 60

        working_minutes = 9*60
        occupancy = (total_minutes / working_minutes) * 100

        result.append({
            "date": current_day,
            "occupancy": round(occupancy, 2)
        })

    return result

#method of room details
@app.get("/room/{room_id}", response_class=HTMLResponse)
async def roomDetails(request: Request, room_id: str):

    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    rooms = list(rooms_collection.find())
    room = (rooms_collection.find_one({"_id":ObjectId(room_id)}))
    if not room:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    days = list(days_collection.find({"room_id": ObjectId(room_id)}))
    day_id = [day["_id"] for day in days]

    bookings = list(bookings_collection.find({
        "day_id": {"$in" : day_id}
        }))

    
    all_rooms = list(rooms_collection.find())
    room_map = {str(r["_id"]): r["name"] for r in all_rooms}
    
    all_days = list(days_collection.find())
    day_map = {str(day["_id"]): day for day in all_days}

    bookings.sort(key=lambda booking: (day_map.get(str(booking["day_id"]), {}).get("date", ""),booking["start_time"]))    
    

    occupancy = occupancyPercent(room_id)
    free_slot = freeSlot(room_id)
    calendar = calendarView(room_id)



    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "rooms": rooms,
        "room": room,
        "days": days,
        "bookings": bookings,
        "room_map": room_map,
        "day_map": day_map,
        "this_room_id": room_id,
        "occupancy": occupancy,
        "free_slot": free_slot,
        "calendar": calendar,
        "error_message": None
    })

#freesolts available for next 5 days function
def freeSlot(room_id):
    result = []
    today = datetime.date.today()

    for i in range(5):
        current_day = str(today + datetime.timedelta(days=i))

        day = days_collection.find_one({
            "room_id": ObjectId(room_id),
            "date": current_day
        })

        bookings = []
        if day:
            bookings = list(bookings_collection.find({
                "day_id": day["_id"]
            }).sort("start_time", 1))

        current_time = datetime.datetime.strptime("09:00", "%H:%M")
        end_of_day = datetime.datetime.strptime("18:00", "%H:%M")

        found_slot = None

        for booking in bookings:
            start = datetime.datetime.strptime(booking["start_time"], "%H:%M")
            end = datetime.datetime.strptime(booking["end_time"], "%H:%M")

            if current_time < start:
                found_slot = current_time.strftime("%H:%M")
                break

            current_time = max(current_time, end)

        if not found_slot:
            if current_time < end_of_day:
                found_slot = current_time.strftime("%H:%M")
            else:
                found_slot = "No availability"

        result.append({
            "date": current_day,
            "earliest": found_slot
        })

    return result


def calendarView(room_id):

    result = []
    today = datetime.date.today()

    for i in range(5):
        current_day = str(today + datetime.timedelta(days=i))

        day = days_collection.find_one({
            "room_id": ObjectId(room_id),
            "date": current_day
        })

        bookings_list = []

        if day:
            bookings = list(bookings_collection.find({
                "day_id": day["_id"]
            }).sort("start_time", 1))

            for b in bookings:
                bookings_list.append({
                    "start": b['start_time'],
                    "end": b['end_time']
                })

        result.append({
            "date": current_day,
            "bookings": bookings_list
        })

    return result
"""

    