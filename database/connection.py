import asyncpg
import os
from fastapi import HTTPException
from dotenv import load_dotenv

# Ensure environment variables are loaded even if this module is imported before app initialization
load_dotenv()

async def get_db_connection():
	try:
		# Read the DATABASE_URL at call time to avoid import-order issues
		DATABASE_URL = os.getenv("DATABASE_URL")
		if not DATABASE_URL:
			raise HTTPException(status_code=500, detail="DATABASE_URL is not set. Please create backend/.env with your Neon connection string.")

		# Neon requires SSL; asyncpg supports passing ssl=True to use a default SSL context
		conn = await asyncpg.connect(DATABASE_URL, ssl=True)
		return conn
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

async def init_db():
	conn = await get_db_connection()
	try:
		await conn.execute("""
			CREATE TABLE IF NOT EXISTS users (
				id SERIAL PRIMARY KEY,
				username VARCHAR(50) UNIQUE NOT NULL,
				email VARCHAR(100) UNIQUE NOT NULL,
				password_hash VARCHAR(255) NOT NULL,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
		""")
	finally:
		await conn.close()
