"""Unit tests for FUNDING agent CLI entry point.

Tests for apps.agents.funding.main module, ensuring proper CLI argument parsing,
agent execution, error handling, and database persistence.

Coverage target: >80% per CLAUDE.md standards.
"""

import logging
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

# Add project root to path (same as main.py does)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.agents.funding.main import setup_logging, persist_to_db, main


class TestSetupLogging:
    """Test suite for logging configuration."""

    def test_setup_logging_default_level(self):
        """Test that default logging level is INFO."""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(verbose=False)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs['level'] == logging.INFO

    def test_setup_logging_verbose_level(self):
        """Test that verbose flag sets DEBUG level."""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(verbose=True)

            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs['level'] == logging.DEBUG

    def test_setup_logging_format(self):
        """Test that logging format includes timestamp, name, and level."""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging()

            call_kwargs = mock_basic_config.call_args[1]
            log_format = call_kwargs['format']

            assert '%(asctime)s' in log_format
            assert '%(name)s' in log_format
            assert '%(levelname)s' in log_format
            assert '%(message)s' in log_format


class TestPersistToDB:
    """Test suite for database persistence."""

    @patch('dotenv.load_dotenv')
    @patch('sqlalchemy.create_engine')
    @patch('sqlalchemy.orm.sessionmaker')
    @patch('apps.agents.funding.db_writer.persist_all_events')
    def test_persist_to_db_creates_agent_run(
        self, mock_persist_events, mock_sessionmaker, mock_create_engine, mock_load_dotenv
    ):
        """Test that persist_to_db creates AgentRun record."""
        # Setup mocks
        mock_session = Mock()
        mock_sessionmaker.return_value = Mock(return_value=mock_session)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        mock_agent = Mock()
        mock_agent.agent_name = "funding"
        mock_agent.run_id = "test-run-123"
        mock_agent.week_number = 7
        mock_agent.provenance.get_sources.return_value = ["source1", "source2"]
        mock_agent._scored_events = []

        mock_result = Mock()
        mock_result.title = "Test Report"
        mock_result.body_md = "Test content"
        mock_result.summary = "Test summary"
        mock_result.content_type = "DATA_REPORT"
        mock_result.sources = []
        mock_result.confidence.composite = 0.8
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        metadata = {
            'items_collected': 10,
            'items_processed': 8,
            'started_at': datetime.now(),
        }

        # Execute
        persist_to_db(mock_agent, mock_result, metadata)

        # Verify AgentRun was added
        assert mock_session.add.call_count == 2  # AgentRun + ContentPiece
        assert mock_session.commit.called
        assert not mock_session.rollback.called

    @patch('dotenv.load_dotenv')
    @patch('sqlalchemy.create_engine')
    @patch('sqlalchemy.orm.sessionmaker')
    @patch('apps.agents.funding.db_writer.persist_all_events')
    def test_persist_to_db_persists_funding_rounds(
        self, mock_persist_events, mock_sessionmaker, mock_create_engine, mock_load_dotenv
    ):
        """Test that persist_to_db calls persist_all_events with scored events."""
        # Setup mocks
        mock_session = Mock()
        mock_sessionmaker.return_value = Mock(return_value=mock_session)
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        mock_event1 = Mock()
        mock_event2 = Mock()
        mock_scored1 = Mock()
        mock_scored1.event = mock_event1
        mock_scored1.confidence.composite = 0.8
        mock_scored2 = Mock()
        mock_scored2.event = mock_event2
        mock_scored2.confidence.composite = 0.7

        mock_agent = Mock()
        mock_agent.agent_name = "funding"
        mock_agent.run_id = "test-run-123"
        mock_agent.week_number = 7
        mock_agent.provenance.get_sources.return_value = ["source1"]
        mock_agent._scored_events = [mock_scored1, mock_scored2]

        mock_result = Mock()
        mock_result.title = "Test Report"
        mock_result.body_md = "Test content"
        mock_result.summary = "Test summary"
        mock_result.content_type = "DATA_REPORT"
        mock_result.sources = []
        mock_result.confidence.composite = 0.75
        mock_result.confidence.dq_display = 3.8
        mock_result.confidence.ac_display = 3.2

        metadata = {'items_collected': 10, 'items_processed': 8}

        mock_persist_events.return_value = {'inserted': 2, 'updated': 0, 'skipped': 0}

        # Execute
        persist_to_db(mock_agent, mock_result, metadata)

        # Verify persist_all_events was called
        mock_persist_events.assert_called_once()
        events_arg = mock_persist_events.call_args[0][1]
        assert len(events_arg) == 2
        assert events_arg[0][0] == mock_event1
        assert events_arg[0][1] == 0.8
        assert events_arg[1][0] == mock_event2
        assert events_arg[1][1] == 0.7

    @patch('dotenv.load_dotenv')
    @patch('sqlalchemy.create_engine')
    @patch('sqlalchemy.orm.sessionmaker')
    def test_persist_to_db_handles_errors(
        self, mock_sessionmaker, mock_create_engine, mock_load_dotenv
    ):
        """Test that persist_to_db rolls back on error."""
        # Setup mocks
        mock_session = Mock()
        mock_session.add.side_effect = Exception("Database error")
        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        mock_agent = Mock()
        mock_agent.agent_name = "funding"
        mock_agent.provenance.get_sources.return_value = []
        mock_agent._scored_events = []

        mock_result = Mock()
        mock_result.confidence.composite = 0.8
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        metadata = {}

        # Execute - should raise error
        with pytest.raises(Exception) as exc_info:
            persist_to_db(mock_agent, mock_result, metadata)

        assert "Database error" in str(exc_info.value)
        assert mock_session.rollback.called
        assert mock_session.close.called


class TestMainCLI:
    """Test suite for main() CLI function."""

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('sys.argv', ['main.py', '--dry-run'])
    def test_dry_run_mode_no_file_created(self, mock_setup_logging, mock_funding_agent_class):
        """Test that dry-run mode doesn't create output files."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Test funding content"
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 15,
            'items_processed': 12
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 5}

        mock_funding_agent_class.return_value = mock_agent

        # Capture stdout
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            main()

            output = mock_stdout.getvalue()

            # Should print preview with equals signs
            assert "=" in output
            assert "Test funding content" in output

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('sys.argv', ['main.py', '--week', '8'])
    def test_normal_mode_creates_output_file(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_funding_agent_class
    ):
        """Test that normal mode creates output file with correct content."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        md_content = "# FUNDING Report\n\nTest content"
        mock_result.to_markdown.return_value = md_content
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 15,
            'items_processed': 12
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 5}

        mock_funding_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify output directory created
        mock_makedirs.assert_called_once_with("apps/agents/funding/output", exist_ok=True)

        # Verify file written with correct content
        mock_file_open.assert_called_once_with(
            "apps/agents/funding/output/funding-week-8.md",
            "w",
            encoding="utf-8"
        )
        handle = mock_file_open()
        handle.write.assert_called_once_with(md_content)

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('sys.argv', ['main.py', '--output', '/tmp/custom-funding-report.md'])
    def test_custom_output_path(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_funding_agent_class
    ):
        """Test that --output flag uses custom path."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 10,
            'items_processed': 8
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 3}

        mock_funding_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Should NOT create default directory when custom output specified
        mock_makedirs.assert_not_called()

        # Should write to custom path
        mock_file_open.assert_called_once_with(
            "/tmp/custom-funding-report.md",
            "w",
            encoding="utf-8"
        )

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('apps.agents.funding.main.persist_to_db')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('sys.argv', ['main.py', '--persist'])
    def test_persist_flag_calls_persist_to_db(
        self, mock_makedirs, mock_file_open, mock_persist_to_db,
        mock_setup_logging, mock_funding_agent_class
    ):
        """Test that --persist flag calls persist_to_db function."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_funding_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify persist_to_db was called
        mock_persist_to_db.assert_called_once()
        call_args = mock_persist_to_db.call_args[0]
        assert call_args[0] == mock_agent
        assert call_args[1] == mock_result

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('sys.argv', ['main.py', '--verbose'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_verbose_flag_enables_debug_logging(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_funding_agent_class
    ):
        """Test that --verbose flag enables DEBUG logging."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_funding_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify verbose=True was passed to setup_logging
        mock_setup_logging.assert_called_once_with(True)

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('sys.argv', ['main.py', '--week', '42'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_custom_week_number(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_funding_agent_class
    ):
        """Test that --week flag sets custom week number."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_funding_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify FundingAgent was initialized with week 42
        mock_funding_agent_class.assert_called_once_with(week_number=42)

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_displays_metadata_in_output(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_funding_agent_class
    ):
        """Test that metadata is displayed in final output."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.validate.return_value = []
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "B"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 20,
            'items_processed': 18
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 7}

        mock_funding_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            main()

            output = mock_stdout.getvalue()

            # Verify metadata is displayed
            assert "20" in output  # items_collected
            assert "18" in output  # items_processed
            assert "7" in output  # unique_sources
            assert "B" in output  # confidence grade

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    def test_output_validation_warnings(self, mock_setup_logging, mock_funding_agent_class):
        """Test that validation warnings are logged."""
        # Setup mock agent with validation errors
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.validate.return_value = ["Missing title", "Invalid confidence"]
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = 4.0
        mock_result.confidence.ac_display = 3.5

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_funding_agent_class.return_value = mock_agent

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with patch('sys.stdout', new=StringIO()):
                with patch('builtins.open', mock_open()):
                    with patch('os.makedirs'):
                        main()

            # Verify warning was logged
            assert mock_logger.warning.called

    @patch('apps.agents.funding.main.FundingAgent')
    @patch('apps.agents.funding.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    def test_agent_execution_error_propagates(self, mock_setup_logging, mock_funding_agent_class):
        """Test that agent execution errors propagate to caller."""
        # Setup mock agent that raises error
        mock_agent = Mock()
        mock_agent.run.side_effect = RuntimeError("Failed to collect funding events")

        mock_funding_agent_class.return_value = mock_agent

        # Should propagate the error
        with pytest.raises(RuntimeError) as exc_info:
            main()

        assert "Failed to collect funding events" in str(exc_info.value)
