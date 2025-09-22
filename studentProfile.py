from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from passlib.context import CryptContext
from jose import JWTError, jwt
import random
import string
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()

app = FastAPI()

# ---------------- DB Setup ----------------
MongoDB_URI = os.getenv("MongoDB_URI")
client = MongoClient(MongoDB_URI)  
db = client["School_app"]
students_collection = db["students"]
teachers_collection = db["teachers"]

# ---------------- JWT Config ----------------
SECRET_KEY = os.environ.get("JWT_SECRET", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ---------------- Models ----------------
class StudentCreate(BaseModel):
    full_name: str
    email: EmailStr
    gender: str
    student_class: str
    age: int
    address: str

class TeacherCreate(BaseModel):
    full_name: str
    email: EmailStr
    gender: str
    subject: str
    years_of_experience: int
    address: str

class Token(BaseModel):
    access_token: str
    token_type: str

# ---------------- Utility Functions ----------------
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def generate_password(length: int = 10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = time.time() + expires_delta * 60
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub") or ""
        role: str = payload.get("role") or ""
        if username is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    collection = students_collection if role == "student" else teachers_collection
    user = collection.find_one({"username": username})
    if not user:
        raise credentials_exception
    return user

# ---------------- Email Function ----------------
def send_credentials_email(to_email: str, full_name: str, username: str, password: str, role: str):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465
    
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_app_password = os.environ.get("SENDER_PASSWORD")
    
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Your {role.capitalize()} Account Credentials"
    message["From"] = str(sender_email)
    message["To"] = to_email


    text = f"""
Hello {full_name},

Your {role} account has been created.

Username: {username}
Password: {password}

Please keep this information safe.
"""
    message.attach(MIMEText(text, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(str(sender_email), str(sender_app_password))
            server.sendmail(str(sender_email), to_email, message.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email credentials")

# ---------------- Admin Add Student ----------------
@app.post("/admin/add_student")
def add_student(student: StudentCreate):
    if students_collection.find_one({"username": student.email}):
        raise HTTPException(status_code=400, detail="Student with this email already exists")

    raw_password = generate_password()
    hashed_password = hash_password(raw_password)

    student_data = {
        "full_name": student.full_name,
        "username": student.email,
        "email": student.email,
        "gender": student.gender,
        "student_class": student.student_class,
        "age": student.age,
        "address": student.address,
        "hashed_password": hashed_password,
        "role": "student"
    }

    students_collection.insert_one(student_data)

    # Send credentials emai
    send_credentials_email(student.email, student.full_name, student.email, raw_password, "student")

    return {
        "message": f"Student {student.full_name} added successfully.",
        "username": student.email,
        "password": raw_password
    }

# ---------------- Admin Add Teacher ----------------
@app.post("/admin/add_teacher")
def add_teacher(teacher: TeacherCreate):
    if teachers_collection.find_one({"username": teacher.email}):
        raise HTTPException(status_code=400, detail="Teacher with this email already exists")

    raw_password = generate_password()
    hashed_password = hash_password(raw_password)

    teacher_data = {
        "full_name": teacher.full_name,
        "username": teacher.email,
        "email": teacher.email,
        "gender": teacher.gender,
        "subject": teacher.subject,
        "years_of_experience": teacher.years_of_experience,
        "address": teacher.address,
        "hashed_password": hashed_password,
        "role": "teacher"
    }

    teachers_collection.insert_one(teacher_data)

    # Send credentials email
    send_credentials_email(teacher.email, teacher.full_name, teacher.email, raw_password, "teacher")

    return {
        "message": f"Teacher {teacher.full_name} added successfully.",
        "username": teacher.email,
        "password": raw_password
    }

# ---------------- Login (Student or Teacher) ----------------
@app.post("/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    # Check in students
    user = students_collection.find_one({"username": form_data.username})
    role = "student"
    if not user:
        # If not student, check teachers
        user = teachers_collection.find_one({"username": form_data.username})
        role = "teacher"
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user["username"], "role": role})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------------- Protected Profile ----------------
@app.get("/my_profile")
def read_profile(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role", "student")
    base_profile = {
        "full_name": current_user.get("full_name"),
        "email": current_user["email"],
        "username": current_user["username"],
        "gender": current_user.get("gender"),
        "address": current_user.get("address"),
        "role": role,
        "message": f"This is your protected {role} profile information."
    }
    if role == "student":
        base_profile.update({
            "class": current_user.get("student_class"),
            "age": current_user.get("age"),
        })
    else:  # teacher
        base_profile.update({
            "subject": current_user.get("subject"),
            "years_of_experience": current_user.get("years_of_experience"),
        })
    return base_profile


# ---------------- New: Get Endpoint ----------------
@app.get("/admin/get_students")
def get_students():
    students = list(students_collection.find({}, {"_id": 0, "password": 0}))
    return {"students": students}

@app.get("/admin/get_teachers")
def get_teachers():
    teachers = list(teachers_collection.find({}, {"_id": 0, "password": 0}))
    return {"teachers": teachers}