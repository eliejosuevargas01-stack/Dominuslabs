import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import os
# Add the app directory to sys.path so pytest can find 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, get_db

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create tables in the test database
    Base.metadata.create_all(bind=engine)
    
    # Seed users for test session
    from app.core.config import settings
    from app.models.user import User
    from app.core.security import get_password_hash
    
    seed_session = TestingSessionLocal()
    try:
        admin_email = settings.ADMIN_USERNAME
        if "@" not in admin_email:
            admin_email = f"{settings.ADMIN_USERNAME}@dominuslabs.online"
            
        admin_user = User(
            email=admin_email,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role="admin",
            can_create_projects=True,
            can_edit_projects=True,
            can_manage_crm=True,
            can_use_scrapper=True
        )
        seed_session.add(admin_user)
        
        viewer_email = settings.VIEWER_USERNAME
        if "@" not in viewer_email:
            viewer_email = "patrik182rodrigues@gmail.com"
            
        viewer_user = User(
            email=viewer_email,
            hashed_password=get_password_hash(settings.VIEWER_PASSWORD),
            role="custom",
            can_create_projects=True,
            can_edit_projects=False,
            can_manage_crm=True,
            can_use_scrapper=True
        )
        seed_session.add(viewer_user)
        seed_session.commit()
    except Exception as e:
        seed_session.rollback()
        raise e
    finally:
        seed_session.close()

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    # Override get_db dependency to use the test session
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
