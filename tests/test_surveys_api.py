"""
Integration tests for surveys API endpoints
Tests the surveys functionality with cache integration
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from main import app
from db_control.mymodels_MySQL import Base
from cache.manager import cache_manager
import api.surveys

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_surveys.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the session factory for testing
api.surveys._test_session_factory = TestingSessionLocal

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_test_db():
    """Set up test database with sample data"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create test session
    db = TestingSessionLocal()
    
    try:
        # Import models for data creation
        from db_control.mymodels_MySQL import USERS, SURVEYS, SURVEY_RESPONSES
        
        # Create test users
        test_user1 = USERS(
            user_id=1,
            username="testuser1",
            email="test1@example.com",
            display_name="Test User 1",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_user2 = USERS(
            user_id=2,
            username="testuser2",
            email="test2@example.com",
            display_name="Test User 2",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(test_user1)
        db.add(test_user2)
        
        # Create test surveys
        survey1 = SURVEYS(
            survey_id=1,
            title="地域の交通について",
            question_text="地域の交通状況についてどう思いますか？",
            points=10,
            deadline=None,
            target_audience="all",
            created_at=datetime.now()
        )
        survey2 = SURVEYS(
            survey_id=2,
            title="公園の利用について",
            question_text="地域の公園をどのくらい利用しますか？",
            points=5,
            target_audience="all",
            created_at=datetime.now()
        )
        
        db.add(survey1)
        db.add(survey2)
        
        # Create test survey responses
        response1 = SURVEY_RESPONSES(
            user_id=1,
            survey_id=1,
            choice="agree",
            comment="交通が便利になってほしいです",
            submitted_at=datetime.now()
        )
        response2 = SURVEY_RESPONSES(
            user_id=2,
            survey_id=1,
            choice="disagree",
            comment="現状で満足しています",
            submitted_at=datetime.now()
        )
        response3 = SURVEY_RESPONSES(
            user_id=1,
            survey_id=2,
            choice="often",
            comment="毎日利用しています",
            submitted_at=datetime.now()
        )
        
        db.add(response1)
        db.add(response2)
        db.add(response3)
        
        db.commit()
        
        # Initialize cache with test data
        cache_manager.initialize(db)
        
        yield db
        
    finally:
        db.close()
        # Clean up
        Base.metadata.drop_all(bind=engine)


class TestSurveysAPI:
    """Test class for surveys API endpoints"""
    
    def test_get_surveys_success(self, setup_test_db):
        """Test successful retrieval of surveys list"""
        response = client.get("/api/v1/surveys")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check survey structure
        survey = data[0]
        assert "survey_id" in survey
        assert "title" in survey
        assert "question_text" in survey
        assert "points" in survey
        assert "deadline" in survey
        assert "target_audience" in survey
        assert "created_at" in survey
        assert "response_count" in survey
        
        # Check that surveys are sorted by creation date (newest first)
        assert data[0]["created_at"] >= data[1]["created_at"]
    
    def test_get_surveys_with_pagination(self, setup_test_db):
        """Test surveys list with pagination parameters"""
        response = client.get("/api/v1/surveys?skip=0&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 1
    
    def test_get_surveys_empty_pagination(self, setup_test_db):
        """Test surveys list with pagination beyond available data"""
        response = client.get("/api/v1/surveys?skip=10&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_survey_by_id_success(self, setup_test_db):
        """Test successful retrieval of a specific survey"""
        response = client.get("/api/v1/surveys/1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["survey_id"] == 1
        assert data["title"] == "地域の交通について"
        assert data["question_text"] == "地域の交通状況についてどう思いますか？"
        assert data["points"] == 10
        assert data["target_audience"] == "all"
        assert data["response_count"] == 2  # Two responses for survey 1
    
    def test_get_survey_by_id_not_found(self, setup_test_db):
        """Test retrieval of non-existent survey"""
        response = client.get("/api/v1/surveys/999")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error_code" in data
        assert "message" in data
        assert "Survey with ID 999 not found" in data["message"]
    
    def test_get_survey_responses_success(self, setup_test_db):
        """Test successful retrieval of survey response statistics"""
        response = client.get("/api/v1/surveys/1/responses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["survey_id"] == 1
        assert data["survey_title"] == "地域の交通について"
        assert data["total_responses"] == 2
        assert data["responses_with_comments"] == 2
        
        # Check choice statistics
        choice_stats = data["choice_statistics"]
        assert "agree" in choice_stats
        assert "disagree" in choice_stats
        assert choice_stats["agree"]["count"] == 1
        assert choice_stats["disagree"]["count"] == 1
        assert choice_stats["agree"]["percentage"] == 50.0
        assert choice_stats["disagree"]["percentage"] == 50.0
        
        # Check response rate info
        response_rate = data["response_rate_info"]
        assert response_rate["total_responses"] == 2
        assert response_rate["target_audience"] == "all"
    
    def test_get_survey_responses_no_responses(self, setup_test_db):
        """Test retrieval of response statistics for survey with no responses"""
        response = client.get("/api/v1/surveys/2/responses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["survey_id"] == 2
        assert data["total_responses"] == 1  # One response for survey 2
        assert data["choice_statistics"]["often"]["count"] == 1
        assert data["responses_with_comments"] == 1
    
    def test_get_survey_responses_not_found(self, setup_test_db):
        """Test retrieval of responses for non-existent survey"""
        response = client.get("/api/v1/surveys/999/responses")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error_code" in data
        assert "message" in data
        assert "Survey with ID 999 not found" in data["message"]
    
    def test_surveys_api_error_handling(self, setup_test_db):
        """Test API error handling for invalid requests"""
        # Test invalid pagination parameters
        response = client.get("/api/v1/surveys?skip=-1")
        assert response.status_code == 422
        
        response = client.get("/api/v1/surveys?limit=0")
        assert response.status_code == 422
        
        response = client.get("/api/v1/surveys?limit=1000")
        assert response.status_code == 422
        
        # Test invalid survey ID
        response = client.get("/api/v1/surveys/invalid")
        assert response.status_code == 422


class TestSurveysAPIIntegration:
    """Integration tests for surveys API with other components"""
    
    def test_surveys_cache_integration(self, setup_test_db):
        """Test that surveys API properly integrates with cache manager"""
        # Test that cache is initialized
        assert cache_manager.is_initialized()
        
        # Test that surveys are loaded in cache
        cached_surveys = cache_manager.get_surveys()
        assert len(cached_surveys) == 2
        
        # Test API returns same data as cache
        response = client.get("/api/v1/surveys")
        api_surveys = response.json()
        
        assert len(api_surveys) == len(cached_surveys)
        
        # Compare first survey
        api_survey = api_surveys[0]
        cached_survey = next(s for s in cached_surveys if s.survey_id == api_survey["survey_id"])
        
        assert api_survey["survey_id"] == cached_survey.survey_id
        assert api_survey["title"] == cached_survey.title
        assert api_survey["response_count"] == cached_survey.response_count
    
    def test_surveys_response_consistency(self, setup_test_db):
        """Test consistency between survey response counts and actual responses"""
        # Get survey from API
        response = client.get("/api/v1/surveys/1")
        survey_data = response.json()
        
        # Get response statistics
        response = client.get("/api/v1/surveys/1/responses")
        response_data = response.json()
        
        # Verify consistency
        assert survey_data["response_count"] == response_data["total_responses"]
    
    def test_surveys_data_validation(self, setup_test_db):
        """Test that survey data meets validation requirements"""
        response = client.get("/api/v1/surveys")
        surveys = response.json()
        
        for survey in surveys:
            # Test required fields
            assert survey["survey_id"] > 0
            assert len(survey["title"]) > 0
            assert survey["points"] >= 0
            assert survey["response_count"] >= 0
            assert survey["target_audience"] in ["all", "tokyogas_member"]
            
            # Test datetime format
            assert "T" in survey["created_at"]  # ISO format
            if survey["deadline"]:
                assert "T" in survey["deadline"]  # ISO format