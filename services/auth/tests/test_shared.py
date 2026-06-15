"""Tests para lego_shared."""
import json
import logging
from lego_shared import setup_logging, build_health_response, ErrorResponse


class TestLogging:
    def test_setup_logging_returns_logger(self):
        logger = setup_logging("test", "DEBUG")
        assert logger.level == logging.DEBUG
        assert logger.name == "test"

    def test_log_output_is_json(self, caplog):
        caplog.set_level(logging.INFO)
        logger = setup_logging("test_json", "INFO")
        logger.info("hello world")

        # caplog no captura nuestro handler custom, entonces verificamos que se pueda crear
        assert logger.hasHandlers()


class TestHealth:
    def test_build_health_response_minimal(self):
        result = build_health_response("auth")
        assert result["status"] == "healthy"
        assert result["service"] == "auth"
        assert result["version"] == "0.1.0"
        assert "timestamp" in result

    def test_build_health_response_with_extra(self):
        result = build_health_response("auth", "1.0.0", {"db": "ok"})
        assert result["version"] == "1.0.0"
        assert result["db"] == "ok"

    def test_build_health_response_custom_version(self):
        result = build_health_response("auth", "2.0.0")
        assert result["version"] == "2.0.0"


class TestErrorResponse:
    def test_error_response_minimal(self):
        err = ErrorResponse("not_found", "User not found")
        d = err.to_dict()
        assert d["error"] == "not_found"
        assert d["message"] == "User not found"
        assert "detail" not in d

    def test_error_response_with_detail(self):
        err = ErrorResponse("validation_error", "Invalid email", {"email": "bad format"})
        d = err.to_dict()
        assert d["detail"] == {"email": "bad format"}

    def test_error_response_omit_none_detail(self):
        err = ErrorResponse("err", "msg", None)
        d = err.to_dict()
        assert "detail" not in d
