from database.database import engine

try:
    connection = engine.connect()
    print("✅ Connected to the database successfully!")
    connection.close()
except Exception as e:
    print("❌ Connection failed:", e)