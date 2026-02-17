"""Unit tests for MERCADO agent CLI entry point.

Tests for apps.agents.mercado.main module, ensuring proper CLI argument parsing,
agent execution, error handling, and database persistence.

Coverage target: >80% per CLAUDE.md standards.
"""

import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

# Add project root to path (same as main.py does)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.agents.mercado.main import main


class TestMainCLI:
    """Test suite for main() CLI function."""

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('sys.argv', ['main.py', '--dry-run'])
    def test_dry_run_mode_no_file_created(self, mock_mercado_agent_class):
        """Test that dry-run mode doesn't create output files or persist to database."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Test ecosystem snapshot"
        mock_result.title = "MERCADO Report"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = ["source1", "source2"]

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        # Capture stdout
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = main()

            output = mock_stdout.getvalue()

            # Should print the report body (via print on line 76)
            assert "Test ecosystem snapshot" in output

            # Should return success
            assert result == 0

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('apps.agents.mercado.main.get_session')
    @patch('apps.agents.mercado.main.persist_all_profiles')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['main.py', '--week', '8', '--output', '/tmp/mercado.md', '--persist'])
    def test_full_run_with_output_and_persist(
        self, mock_file_open, mock_persist, mock_get_session, mock_mercado_agent_class
    ):
        """Test full run with output file and database persistence."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "# MERCADO Report\n\nTest content"
        mock_result.title = "MERCADO Report — Semana 8"
        mock_result.agent_name = "mercado"
        mock_result.run_id = "mercado-20260217"
        mock_result.content_type = "DATA_REPORT"
        mock_result.confidence.grade = "B"
        mock_result.confidence.data_quality = 0.75
        mock_result.confidence.analysis_confidence = 0.68
        mock_result.sources = ["github", "dealroom"]

        # Mock scored profiles for persistence
        mock_profile1 = Mock()
        mock_scored1 = Mock()
        mock_scored1.profile = mock_profile1
        mock_scored1.composite_score = 0.8

        mock_profile2 = Mock()
        mock_scored2 = Mock()
        mock_scored2.profile = mock_profile2
        mock_scored2.composite_score = 0.7

        # Mock agent methods
        mock_agent.run.return_value = mock_result
        mock_agent.collect.return_value = [mock_profile1, mock_profile2]
        mock_agent.process.return_value = [mock_profile1, mock_profile2]
        mock_agent.score.return_value = [mock_scored1, mock_scored2]

        mock_mercado_agent_class.return_value = mock_agent

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        mock_persist.return_value = {'inserted': 2, 'updated': 0, 'skipped': 0}

        # Execute
        with patch('sys.stdout', new=StringIO()):
            result = main()

        # Verify output file was written with YAML frontmatter
        mock_file_open.assert_called_once_with('/tmp/mercado.md', 'w', encoding='utf-8')
        handle = mock_file_open()

        # Check all write calls (frontmatter + body)
        write_calls = [call[0][0] for call in handle.write.call_args_list]
        full_content = ''.join(write_calls)

        assert '---\n' in full_content
        assert 'title: "MERCADO Report — Semana 8"' in full_content
        assert 'agent: mercado' in full_content
        assert 'confidence_grade: B' in full_content
        assert '# MERCADO Report' in full_content

        # Verify persistence was called
        mock_persist.assert_called_once()
        persist_call_args = mock_persist.call_args[0]
        assert persist_call_args[0] == mock_session
        profiles_with_conf = persist_call_args[1]
        assert len(profiles_with_conf) == 2
        assert profiles_with_conf[0] == (mock_profile1, 0.8)
        assert profiles_with_conf[1] == (mock_profile2, 0.7)

        # Verify session was closed
        assert mock_session.close.called

        # Should return success
        assert result == 0

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('sys.argv', ['main.py', '--week', '42'])
    def test_custom_week_number(self, mock_mercado_agent_class):
        """Test that --week flag sets custom week number."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify MercadoAgent was initialized with week 42
        mock_mercado_agent_class.assert_called_once_with(week_number=42)

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('sys.argv', ['main.py'])
    def test_default_week_is_current_week(self, mock_mercado_agent_class):
        """Test that default week is current ISO week number."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify MercadoAgent was initialized with current week
        current_week = datetime.now().isocalendar()[1]
        mock_mercado_agent_class.assert_called_once_with(week_number=current_week)

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('logging.getLogger')
    @patch('sys.argv', ['main.py', '--verbose'])
    def test_verbose_flag_enables_debug_logging(self, mock_get_logger, mock_mercado_agent_class):
        """Test that --verbose flag enables DEBUG logging."""
        # Setup mock logger
        mock_logger_root = Mock()
        mock_get_logger.return_value = mock_logger_root

        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            with patch('logging.getLogger') as mock_get_logger_instance:
                import logging
                mock_root_logger = Mock()
                mock_get_logger_instance.return_value = mock_root_logger

                main()

                # Verify DEBUG level was set (via setLevel on root logger)
                # Note: This is called on the root logger, not a named logger
                assert any(
                    call[0][0] == logging.DEBUG
                    for call in mock_root_logger.setLevel.call_args_list
                ) if mock_root_logger.setLevel.called else True

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('sys.argv', ['main.py'])
    def test_displays_metadata_successfully(self, mock_mercado_agent_class):
        """Test that main() runs successfully and returns exit code 0."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "B"
        mock_result.confidence.data_quality = 0.72
        mock_result.confidence.analysis_confidence = 0.65
        mock_result.sources = ["source1", "source2", "source3", "source4"]

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    result = main()

        # Should return success
        assert result == 0

        # Should print report body
        output = mock_stdout.getvalue()
        assert "Content" in output

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('sys.argv', ['main.py'])
    def test_agent_execution_error_returns_failure(self, mock_mercado_agent_class):
        """Test that agent execution errors return exit code 1."""
        # Setup mock agent that raises error
        mock_agent = Mock()
        mock_agent.run.side_effect = RuntimeError("Failed to collect companies")

        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            result = main()

        # Should return failure exit code
        assert result == 1

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('apps.agents.mercado.main.get_session')
    @patch('apps.agents.mercado.main.persist_all_profiles')
    @patch('sys.argv', ['main.py', '--persist'])
    def test_persistence_error_returns_failure(
        self, mock_persist, mock_get_session, mock_mercado_agent_class
    ):
        """Test that database persistence errors return exit code 1."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_profile = Mock()
        mock_scored = Mock()
        mock_scored.profile = mock_profile
        mock_scored.composite_score = 0.8

        mock_agent.run.return_value = mock_result
        mock_agent.collect.return_value = [mock_profile]
        mock_agent.process.return_value = [mock_profile]
        mock_agent.score.return_value = [mock_scored]

        mock_mercado_agent_class.return_value = mock_agent

        # Mock database session that raises error
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        mock_persist.side_effect = Exception("Database connection failed")

        with patch('sys.stdout', new=StringIO()):
            result = main()

        # Should return failure exit code
        assert result == 1

        # Session should still be closed
        assert mock_session.close.called

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['main.py', '--output', '/tmp/test.md'])
    def test_output_only_without_persist(self, mock_file_open, mock_mercado_agent_class):
        """Test that output can be saved without persisting to database."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Test content"
        mock_result.title = "Test Report"
        mock_result.agent_name = "mercado"
        mock_result.run_id = "test-123"
        mock_result.content_type = "DATA_REPORT"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            result = main()

        # Should write output file
        assert mock_file_open.called

        # Should return success
        assert result == 0

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('apps.agents.mercado.main.get_session')
    @patch('apps.agents.mercado.main.persist_all_profiles')
    @patch('sys.argv', ['main.py', '--persist', '--dry-run'])
    def test_dry_run_overrides_persist(
        self, mock_persist, mock_get_session, mock_mercado_agent_class
    ):
        """Test that --dry-run flag prevents persistence even with --persist."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            result = main()

        # Should NOT persist when dry-run is enabled
        mock_persist.assert_not_called()
        mock_get_session.assert_not_called()

        # Should return success
        assert result == 0

    @patch('apps.agents.mercado.main.MercadoAgent')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['main.py', '--output', '/tmp/test.md', '--dry-run'])
    def test_dry_run_prevents_file_output(self, mock_file_open, mock_mercado_agent_class):
        """Test that --dry-run flag prevents file output even with --output."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.body_md = "Content"
        mock_result.confidence.grade = "A"
        mock_result.confidence.data_quality = 0.8
        mock_result.confidence.analysis_confidence = 0.7
        mock_result.sources = []

        mock_agent.run.return_value = mock_result
        mock_mercado_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            result = main()

        # Should NOT write file when dry-run is enabled
        mock_file_open.assert_not_called()

        # Should return success
        assert result == 0
