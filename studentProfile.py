from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List, Optional
from bson import ObjectId
from passlib.context import CryptContext
from jose import JWTError, jwt
import time

app = FastAPI()

# ---------------- DB Setup ----------------
client = MongoClient("mongodb+srv://AyoTech:aGj8hu250IP2Vj82@dataforge.blxqv5n.mongodb.net/?retryWrites=true&w=majority&appName=DataForge")
db = client["School_app"]
students_collection = db["students"]
teachers_collection = db["teachers"]

# ---------------- JWT Config ----------------
SECRET_KEY = "super-secret-key-please-change-to-a-very-long-string"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ---------------- Models ----------------
class StudentRegister(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: str
    password: str

class Teacher(BaseModel):
    name: str
    email: str
    subject: str

class BulkAssign(BaseModel):
    student_usernames: List[str]
    teacher_email: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# ---------------- Utils ----------------
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = time.time() + expires_delta * 60
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_student(token: str = Depends(oauth2_scheme)):
    """Dependency to fetch current student from token"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    student = students_collection.find_one({"username": username})
    if not student:
        raise credentials_exception
    return student

# ---------------- Student Routes ----------------
@app.post("/register")
def register_student(student: StudentRegister):
    if students_collection.find_one({"username": student.username}):
        raise HTTPException(status_code=400, detail="Username already exists")

    student_data = student.dict()
    student_data["hashed_password"] = hash_password(student.password)
    del student_data["password"]

    students_collection.insert_one(student_data)
    return {"message": "Student registered successfully"}

@app.post("/login", response_model=Token)
def login_student(form_data: OAuth2PasswordRequestForm = Depends()):
    student = students_collection.find_one({"username": form_data.username})

    if not student:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # If old "password" exists, convert it to hashed
    if "password" in student and "hashed_password" not in student:
        hashed_pw = hash_password(student["password"])
        students_collection.update_one(
            {"_id": student["_id"]},
            {"$set": {"hashed_password": hashed_pw}, "$unset": {"password": ""}}
        )
        student["hashed_password"] = hashed_pw

    if "hashed_password" not in student:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if not verify_password(form_data.password, student["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": student["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/my_profile")
def read_profile(current_student: dict = Depends(get_current_student)):
    return {
        "full_name": current_student.get("full_name"),
        "email": current_student["email"],
        "username": current_student["username"],
        "message": "This is your protected profile information."
    }

@app.get("/students")
def get_students():
    students = list(students_collection.find({}, {"_id": 0, "hashed_password": 0}))
    return students

# ---------------- Teacher Routes ----------------
@app.post("/add_teacher")
def add_teacher(teacher: Teacher):
    if teachers_collection.find_one({"email": teacher.email}):
        raise HTTPException(status_code=400, detail="Teacher with this email already exists")
    teachers_collection.insert_one(teacher.dict())
    return {"message": "Teacher added successfully"}

@app.post("/assign_teacher_bulk")
def assign_teacher_bulk(data: BulkAssign):
    teacher = teachers_collection.find_one({"email": data.teacher_email})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    result = students_collection.update_many(
        {"username": {"$in": data.student_usernames}},
        {"$set": {"teacher_id": str(teacher["_id"])}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No students found with provided usernames")

    return {"message": f"Teacher {teacher['name']} assigned to {result.modified_count} students"}

# ---------------- Combined Routes ----------------
@app.get("/students_with_teachers")
def students_with_teachers():
    students = list(students_collection.find({}))
    result = []
    for s in students:
        student_info = {
            "full_name": s.get("full_name"),
            "email": s.get("email"),
            "username": s.get("username")
        }
        if s.get("teacher_id"):
            teacher = teachers_collection.find_one({"_id": ObjectId(s["teacher_id"])})
            if teacher:
                student_info["teacher"] = {
                    "name": teacher["name"],
                    "email": teacher["email"],
                    "subject": teacher["subject"]
                }
        result.append(student_info)
    return result

@app.get("/students_by_teacher/{teacher_id}")
def get_students_by_teacher(teacher_id: str):
    try:
        teacher_obj_id = ObjectId(teacher_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid teacher ID format")

    teacher = teachers_collection.find_one({"_id": teacher_obj_id})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    students = list(students_collection.find(
        {"teacher_id": teacher_id},
        {"_id": 0, "hashed_password": 0}
    ))

    return {
        "teacher": {
            "id": str(teacher["_id"]),
            "name": teacher["name"],
            "email": teacher["email"],
            "subject": teacher["subject"]
        },
        "assigned_students": students
    }
