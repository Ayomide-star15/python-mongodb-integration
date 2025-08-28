#import required libraries
from dotenv import load_dotenv, find_dotenv
import os
import pprint
from pymongo import MongoClient

# Load environment variable from .env file (if available)
load_dotenv(find_dotenv())

# Get MongoDB password from environment variable (optional if you want)
password = os.environ.get("MONGODB_PWD")

# Mongo connection string (replace with your own if needed)
connection_string = f"mongodb+srv://AyoTech:43l1OC1mqilP030g@dataforge.blxqv5n.mongodb.net/?retryWrites=true&w=majority&appName=DataForge"

# create a MongoClient instance (connects python to MongoDB)
client = MongoClient(connection_string)

# Select "Test" database and "test" collection
Test_dbs = client["Test"]
collection = Test_dbs["test"]

# Function to insert a single document into Test.test
def insert_test_doc():
    test_document = {
        "Name" : "Ayomide",
        "Type" : "Test"
    }
    inserted_id = collection.insert_one(test_document).inserted_id
    print(inserted_id)

# Select "production" database and "person_collection"
production = client.production
person_collection = production.person_collection

# Function to create multiple documents and insert them into "person_collection"
def create_document():
    first_names = ["Ayo", "Tim", "Joshua", "Jasse", "Bishop"]
    last_names = ["Adewale", "Akin", "Samuel", "Olasunkanmi", "Kolade"]
    ages = [12,23,45,67,78]

    docs = []
    # Loop through names and ages, create documents
    for first_names, last_names, ages in zip(first_names, last_names, ages):
            doc = {"first_name": first_names, "last_names": last_names, "age": ages}
            docs.append(doc)
            #person_collection.insert_one(doc)
    #Insert multiple document at once
    person_collection.insert_many(docs)
    print("Documents inserted successfully")

#Pretty printer for clean output
printer = pprint.PrettyPrinter()

# function to find and print all people in "person_collection"
def find_all_people():
     people = person_collection.find() # Retrieve all all document
     print(list(people))
     
     for person in people:
          printer.pprint(person) # Pretty print each document 

# Function to find one document where firt_name = "Ayo"
def find_Ayo():
     ayo = person_collection.find_one({"first_name" : "Ayo"})
     printer.pprint(ayo)

# function to count all documents in the collection
def count_all_people():
     # Empty filter {} matches all documents
     count = person_collection.count_documents(filter = {})
    
     print("Number of people", count)

#Function to get a person by their MongoDB ObjectId
def get_person_by_id(person_id):
     #import ObjectId class to convert string id to ObjectId
     from bson.objectid import ObjectId

     _id = ObjectId(person_id)
     person = person_collection.find_one({"_id": _id})
     printer.pprint(person)


get_person_by_id("68ac2fa4751eb10e30598e3a")

def get_age_range(min_age, max_age):
     query = {"$and" : [
               {"age": {"$gte": min_age}},
               {"age": {"$lte": max_age}}
               
          ]}
     

     people = person_collection.find(query).sort("age")
     for person in people:
          printer.pprint(person)

get_age_range(20 , 90)

#function to project only specific fields (first_name and last_name)
def project_columns():
     columns = {"_id": 0, "first_name": 1, "last_name": 1}
     people = person_collection.find({}, columns)
     for person in people:
          printer.pprint(person)


def update_person_by_id(person_id):
     from bson.objectid import ObjectId
     _id = ObjectId(person_id)

     all_update = {
     #     "$set": {"new_field": True},
       #   "$inc": {"age": 1},
        #  "$rename": {"first_name": "first", "last_names": "last"}
        }
     
     person_collection.update_one({"_id": _id}, {"$unset": {"new_field": True}})

     #person_collection.update_one({"_id": _id}, all_update)


def replace_person_by_id(person_id):
     from bson.objectid import ObjectId
     _id = ObjectId(person_id)

     new_doc = {
          "first_name": "Updated Name",
          "last_names": "Updated Last Name",
          "age": 100
     }

     person_collection.replace_one({"_id": _id}, new_doc)

def delete_person_by_id(person_id):
        from bson.objectid import ObjectId
        _id = ObjectId(person_id)
    
        person_collection.delete_one({"_id": _id})
        #person_collection.delete_many({})# Delete all documents in the collection   

address = {
     "street": "12 Onipepeye, Oluwo, Egebada Road",
    "city": "Ibadan",
    "state": "Oyo",
    "postal_code": "200263",
    "country": "Nigeria"
}


def add_address_to_person(person_id, address):
        from bson.objectid import ObjectId
        _id = ObjectId(person_id)
    
        person_collection.update_one({"_id": _id}, {"$addToSet": {"addresses": address}})
        

def add_address_relationship(person_id, address):
        from bson.objectid import ObjectId
        _id = ObjectId(person_id)

        address["person_id"] = person_id

        address_collection = production.address
        address_collection.insert_one(address)

add_address_relationship("68ac2fa4751eb10e30598e36",address)
