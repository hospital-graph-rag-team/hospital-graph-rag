import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Locate .env in root
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

print(f"Loaded URI: {URI}")
print(f"Loaded USER: {USER}")
print(f"Loaded PASSWORD set? {'Yes' if PASSWORD else 'No'}")

def get_driver():
    if not URI or not PASSWORD:
        raise ValueError("Missing NEO4J_URI or NEO4J_PASSWORD in .env file.")
    return GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def verify_connection():
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print(" Successfully connected to Neo4j database.")
    finally:
        driver.close()

if __name__ == "__main__":
    verify_connection()