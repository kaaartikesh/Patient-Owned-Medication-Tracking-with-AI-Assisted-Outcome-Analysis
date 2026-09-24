# app/auth/security.py
from passlib.context import CryptContext # helps to scramble the passwords and stores them
from jose import jwt # to give the tickets
from datetime import datetime, timedelta #to put timelimit over the tickets
from app.config import settings #to store the secret key and algorithm

# scrambling of passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")#object

#defining function hash_password()
def hash_password(password):
    return pwd_context.hash(password) #pwd.context in itself is a object cant be called

def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)

# passing ticket using jwt
def create_access_token(data):
    to_encode = data.copy() 
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
#it copies the data, stamps an expiry on it, and signs it into a JWT string using your secret and algorithm. 

# 
def decode_access_token(token):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    

