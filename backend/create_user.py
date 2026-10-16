
import asyncio

from dotenv import load_dotenv

load_dotenv() 

from database import users_collection, ensure_indexes
from security import hash_password


async def main():
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    confirm = input("Confirm password: ").strip()

    if password != confirm:
        print("Passwords don't match. Nothing created.")
        return

    if len(password) < 8:
        print("Password must be at least 8 characters. Nothing created.")
        return

    await ensure_indexes()

    existing = await users_collection.find_one({"email": email})
    if existing:
        print(f"An account with {email} already exists. Nothing created.")
        return

    await users_collection.insert_one({
        "email": email,
        "hashed_password": hash_password(password),
    })
    print(f"Account created for {email}. You can now log in from the frontend.")


if __name__ == "__main__":
    asyncio.run(main())