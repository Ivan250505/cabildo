"""Script de uso único: resetea el password del admin ivvh2505@gmail.com a admin12345."""
import asyncio
from sqlalchemy import update

from app.database import AsyncSessionLocal
from app.auth.models import User
from app.auth.service import hash_password


async def main():
    new_password = "admin12345"
    email = "ivvh2505@gmail.com"
    new_hash = hash_password(new_password)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(User).where(User.email == email).values(password_hash=new_hash)
        )
        await db.commit()
        print(f"Filas actualizadas: {result.rowcount}")
        print(f"Email: {email}")
        print(f"Password nuevo: {new_password}")


if __name__ == "__main__":
    asyncio.run(main())
