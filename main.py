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
"""azure_connection_string = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://azurite:10000/devstoreaccount1;"
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
"""
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



"""
def listBlobs():
    blob_names = []
    for blob in azure_container_client.list_blobs():
        blob_names.append(blob.name)

    return blob_names  """ 

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
    """blob_names=listBlobs()
    #azurite urls
    urls = []
    for blob in blob_names:
        blob_client = azure_container_client.get_blob_client(blob=blob)
        urls.append(blob_client.url)
    """    
    

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
        "error": "" 
    })
    
    tweets = list(tweets_collection.find({"user_id": user_token["user_id"]}).sort("created_at", -1))

    
    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "user_info": user,
        'need_username': False,
        "tweets": tweets,
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
    username = form["username"]

    #check for username already there
    existing_user = users_collection.find_one({"username": username})

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
        "username": username
        
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

    if len(tweet_text) >280:
        return RedirectResponse("/", status_code=302)
    
    user_info = getUser(user_token)

    tweets_collection.insert_one({
        "user_id" : user_token["user_id"],
        "username": user_info["username"],
        "content": tweet_text,
        "created_at": datetime.datetime.now()
    })
        
    

    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

