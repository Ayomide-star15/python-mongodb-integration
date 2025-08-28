from fastapi import FastAPI, Path
from typing import Optional
from pydantic import BaseModel
app  = FastAPI()

# Path parameter
Students = []
#Creating 
class Student(BaseModel):
    Name: str
    Age: int
    Year: str

#Update
class updateStudent(BaseModel):
    Name: Optional[str] = None
    Age: Optional[int] = None
    Year: Optional[str] = None

def find_student(name: str):
    for student in Students:
        if student.Name.lower() == name.lower():
            return student
# @app.get("/")
# def index():
#     return{"name": "First Data"}

@app.get("/get-Student/{name}")
# The path is use to give extra information or validation rules
def get_Student(name: str= Path(..., description = "The name of the student you want to view")):
     for student in Students:
        if student.Name.lower() == name.lower():
            return student
        

# Get all student
@app.get("/get-all-Students")
def get_all_students():
    return{"Students": Students}

#Post method 
@app.post("/create-Student")
def create_student(student : Student):
    # if student.Name in Students:
    #     return{"Error": "Student exists"}

    #Students = student.dict()
    Students.append(student)
    return student

#Put method
@app.put("/update-student/{name}")
def update_student(name: str, student: updateStudent):
    s = next((stu for stu in Students if stu.Name == name), None)

    if not s:
        return {"Error": "Student does not exist"}

    if student.Name is not None:
        s.Name = student.Name
    if student.Age is not None:
        s.Age = student.Age
    if student.Year is not None:
        s.Year = student.Year

    return {
        "Message": "Student updated successfully",
        "Updated Student": s
    }
#delete method
@app.delete("/delete-student/{name}")
def delete_student(name: str):
    for i, s in enumerate(Students):
        if s.Name == name:   # Assuming s is an object
            deleted_student = Students.pop(i)
            return {
                "Message": "Student deleted successfully",
                "Deleted Student": deleted_student
            }
    return {"Error": "Student does not exist"}