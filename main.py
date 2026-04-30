from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import starlette.status as status
from datetime import datetime, timedelta
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
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

#azurite container for profile picture
azure_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
azure_container_name = "profile-pictures-container"

azure_container_client = azure_service_client.get_container_client(azure_container_name)
try:
    azure_container_client.create_container()
except Exception:
    print('profile picture container exists')

container_service_client=azure_service_client.get_container_client(azure_container_name)
existing_policies = container_service_client.get_container_access_policy()
access_policy = AccessPolicy(permission=ContainerSasPermissions(read=True),expiry=datetime.now() + timedelta(hours=24),start=datetime.now() - timedelta(minutes=5))
identifiers = {'read': access_policy}

azure_container_client.set_container_access_policy(signed_identifiers=identifiers,public_access=PublicAccess.CONTAINER)

#container for tweet images
tweet_images_container_name = "tweet-images-container"
tweet_images_container_client = azure_service_client.get_container_client(
    tweet_images_container_name
)
try:
    tweet_images_container_client.create_container()
except Exception:
    print('tweet images container exists')

container_service_client2 = azure_service_client.get_container_client(tweet_images_container_name)
existing_policies = container_service_client.get_container_access_policy()
access_policy = AccessPolicy(permission=ContainerSasPermissions(read=True),expiry=datetime.now() + timedelta(hours=24),start=datetime.now() - timedelta(minutes=5))
identifiers2 = {'read': access_policy}

container_service_client2.set_container_access_policy(signed_identifiers=identifiers2,public_access=PublicAccess.CONTAINER)




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
async def root(request: Request, edit_id: str = None):
    #query firebase for the requesr token we will also decide a bunch if other variables here as we will need them 
    # for rendering the template at the end We have an error_messafe there is case you want to output an error to 
    # the user in the template
    id_token = request.cookies.get('token')
    user_token = None

    
    

    #check if we have a valid firebase login if not return the template with empty dara as we will show the login boc
    if id_token:
        user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return templates.TemplateResponse('main.html', {
            'request': request,
            'user': None,
            "need_username": False,
            'tweets': []
            })
    
    user = getUser(user_token)

    #setting username if new
    if not user:
       return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "need_username": True,
        "tweets": [],
        "error_message": "" 
    })
    
    #timeline implementation
    following_ids = user.get("following", []).copy()
    following_ids.append(user_token["user_id"])#include user tweets

    tweets = list(
        tweets_collection.find({
            "user_id": {"$in": following_ids}
        })
        .sort("created_at", -1)
        .limit(20)
    )

    
    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "user_info": user,
        'need_username': False,
        "tweets": tweets,
        "edit_id": edit_id,
        "error_message": ""    
        })
 

#method for unew username
@app.post("/new-username", response_class=HTMLResponse)
async def newUsername(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse("/", status_code=302)
    
    form = await request.form()
    username = form["username"].strip()

    #check for username already there
    existing_user = users_collection.find_one({"username": username})

    if not username:
        return templates.TemplateResponse("main.html", {
            "request": request,
            "user_token": user_token,
            "user_info": None,
            'need_username': True,
            "error_message": "Username cannot be empty.",
            "tweets": []
        })

    if existing_user:
        return templates.TemplateResponse("main.html",{
            "request": request,
            "user_token": user_token,
            "user_info": None,
            'need_username': True,
            "error_message": "Username already exists",
            "tweets": [] 

        })
    
    users_collection.insert_one({
        "user_id": user_token["user_id"],
        "username": username,
        "bio": "",
        "profile_picture": "",
        "following": [],
        "followers": []
    })

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    

#method to add a new room to the database
@app.post('/add-tweet', response_class=HTMLResponse)
async def addTweet(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    form = await request.form()
    tweet_text = form['tweet_text']
    user_info = getUser(user_token)
    
    if not tweet_text:
        following_ids = user_info.get("following", []).copy()
        following_ids.append(user_token["user_id"])
        tweets = list(tweets_collection.find(
            {"user_id": {"$in": following_ids}}
        ).sort("created_at", -1).limit(20))

        return templates.TemplateResponse("main.html", {
            "request": request,
            "user_token": user_token,
            "user_info": user_info,
            "need_username": False,
            "tweets": tweets,
            "edit_id": None,
            "error_message": "Tweet cannot be empty."
            })

    if len(tweet_text) >280:
        following_ids = user_info.get("following", []).copy()
        following_ids.append(user_token["user_id"])

        tweets = list(tweets_collection.find(
            {"user_id": {"$in": following_ids}}
        ).sort("created_at", -1).limit(20))

        return templates.TemplateResponse("main.html", {
            "request": request,
            "user_token": user_token,
            "user_info": user_info,
            "need_username": False,
            "tweets": tweets,
            "edit_id": None,
            "error_message": "Tweet must be 280 characters or less."
        })
    
    file = form.get("file")
    image_url = ""

    if file and file.filename:
        if file.content_type not in ["image/jpeg", "image/png"]:
            return RedirectResponse("/", status_code=302)

        filename = user_token["user_id"] + "_" + file.filename
        blob_client = tweet_images_container_client.get_blob_client(filename)

        blob_client.upload_blob(await file.read(), overwrite=True)
        image_url = blob_client.url
    

    tweets_collection.insert_one({
        "user_id" : user_token["user_id"],
        "username": user_info["username"],
        "content": tweet_text,
        "image_url": image_url,
        "created_at": datetime.now(),
        "retweet": False
    })
        
    

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


#method to add a new room to the database
@app.get('/search-users', response_class=HTMLResponse)
async def searchUsers(request: Request, query: str =""):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    users = []

    if query:
        users = list(users_collection.find({
            "username": {"$regex": "^" + query}
        }))
     
    

    return templates.TemplateResponse("search.html", {
        "request": request,
        "user_token": user_token, 
        "users": users,
        "tweets": [],
        "query": query,
        "type": "users"
    })

@app.get('/search-tweets', response_class=HTMLResponse)
async def searchTweets(request: Request, query: str =""):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    tweets = []

    if query:
        tweets = list(tweets_collection.find({
            "content": {"$regex": "^" + query}
        }))
     
    

    return templates.TemplateResponse("search.html", {
        "request": request,
        "user_token": user_token, 
        "users": [],
        "tweets": tweets,
        "query": query,
        "type": "tweets"
    })


#profile route
@app.get('/profile/{username}', response_class=HTMLResponse)
async def profile(request: Request, username: str, edit_id: str = None):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    current_userId = user_token["user_id"]

    current_user = users_collection.find_one({"user_id": current_userId})
    user = users_collection.find_one({"username": username})

    if not user:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)     
    
    tweets = list(
        tweets_collection.find({"user_id": user["user_id"]})
        .sort("created_at", -1)
        .limit(10)
    )

    is_Following = user["user_id"] in current_user.get("following", [])

    

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user_token": user_token,
        "profile_user": user,
        "is_owner": current_userId == user["user_id"],
        "tweets": tweets,
        "is_following": is_Following,
        "edit_id": edit_id
    })

@app.post('/follow-user/{username}')
async def followUser(request: Request, username: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    current_userId = user_token["user_id"] 

    followed_user = users_collection.find_one({"username": username})

    if followed_user and followed_user["user_id"] == current_userId:
        return RedirectResponse(f"/profile/{username}", status_code=status.HTTP_302_FOUND)


    if followed_user:
        users_collection.update_one(
            {"user_id": current_userId},
            {"$addToSet": {"following": followed_user["user_id"]}}
        )
        users_collection.update_one(
            {"username": username},
            {"$addToSet": {"followers": current_userId}}
        )
    
    return RedirectResponse(f"/profile/{username}", status_code=status.HTTP_302_FOUND)

@app.post('/unfollow-user/{username}')
async def unfollowUser(request: Request, username: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    current_userId = user_token["user_id"] 

    followed_user = users_collection.find_one({"username": username})

    if followed_user:
        users_collection.update_one(
            {"user_id": current_userId},
            {"$pull": {"following": followed_user["user_id"]}}
        )
        users_collection.update_one(
            {"username": username},
            {"$pull": {"followers": current_userId}}
        )
    
    return RedirectResponse(f"/profile/{username}", status_code=status.HTTP_302_FOUND)


@app.post('/upload-profile-picture')
async def uploadProfilePicture(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)
    
    form = await request.form()
    file = form["file"]

    current_userId = user_token["user_id"]
    user = users_collection.find_one({"user_id": current_userId})
    
    if not file or not file.filename:
        return RedirectResponse("/", status_code=302)
    
    #format validation
    if file.content_type not in ["image/jpeg", "image/png"]:
        return RedirectResponse(f"/profile/{user['username']}", status_code=status.HTTP_302_FOUND)

   

    filename = current_userId + "_" + file.filename

    blob_client = azure_container_client.get_blob_client(filename)
    blob_client.upload_blob(await file.read(), overwrite=True)

    file_url = blob_client.url

    users_collection.update_one(
            {"user_id": current_userId},
            {"$set": {"profile_picture": file_url}}
    )

    
       
    return RedirectResponse(f"/profile/{user['username']}", status_code=status.HTTP_302_FOUND)



@app.post('/edit-tweet/{tweet_id}')
async def editTweet(request: Request, tweet_id: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=302)

    form = await request.form()
    new_text = form['tweet_text']
    source   = form.get('source', 'home')
    username = form.get('username', '')

    if len(new_text) > 280:
        if source == 'profile' and username:
            return RedirectResponse(
                f"/profile/{username}?edit_id={tweet_id}", status_code=302)
        return RedirectResponse(f"/?edit_id={tweet_id}", status_code=302)

    update_data = {"content": new_text}

    if form.get("remove_image"):
        update_data["image_url"] = ""

    
    file = form.get("file")


    if file and file.filename:
        if file.content_type not in ["image/jpeg", "image/png"]:
            return RedirectResponse("/", status_code=302)

        filename = user_token["user_id"] + "_" + file.filename
        blob_client = tweet_images_container_client.get_blob_client(filename)

        blob_client.upload_blob(await file.read(), overwrite=True)
        update_data["image_url"] = blob_client.url


    tweets_collection.update_one(
        {
            "_id": ObjectId(tweet_id),
            "user_id": user_token["user_id"]
        },
        {
            "$set": update_data
        }
    )


    if source == 'profile' and username:
        return RedirectResponse(f"/profile/{username}", status_code=302)
    return RedirectResponse("/", status_code=302)


@app.post('/update-bio')
async def updateBio(request: Request):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=302)


    form = await request.form()
    bio = form["bio"].strip()

    user = users_collection.find_one({"user_id": user_token["user_id"]})

    if len(bio) > 280:
        return RedirectResponse(f"/profile/{user['username']}", status_code=302)

    users_collection.update_one(
        {"user_id": user_token["user_id"]},
        {"$set" : {"bio": bio}}
        )

    return RedirectResponse(f"/profile/{user['username']}", status_code=302)

@app.post('/delete-tweet/{tweet_id}')
async def deleteTweet(request: Request, tweet_id: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=302)

    form = await request.form()
    source   = form.get('source', 'home')
    username = form.get('username', '')

    
    tweets_collection.delete_one({
        "_id": ObjectId(tweet_id),
        "user_id": user_token["user_id"]  
    })

    if source == 'profile' and username:
        return RedirectResponse(f"/profile/{username}", status_code=302)
    return RedirectResponse("/", status_code=302)


@app.post('/retweet/{tweet_id}')
async def retweet(request: Request, tweet_id: str):
    id_token = request.cookies.get('token')
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse('/', status_code=302)

    original = tweets_collection.find_one({"_id": ObjectId(tweet_id)})

    if not original:
        return RedirectResponse("/", status_code=302)

    if original.get("retweet"):
        return RedirectResponse("/", status_code=302)
    
    existing = tweets_collection.find_one({
    "user_id": user_token["user_id"],
    "original_tweet_id": ObjectId(tweet_id)
    })

    if existing:
        return RedirectResponse("/", status_code=302)

    user = getUser(user_token)

    tweets_collection.insert_one({
        "user_id": user_token["user_id"],
        "username": user["username"],
        "content": original["content"],
        "image_url": original.get("image_url", ""),
        "created_at": datetime.now(),
        "retweet": True,
        "original_tweet_id": original["_id"],
        "original_username": original["username"]
    })

    return RedirectResponse("/", status_code=302)