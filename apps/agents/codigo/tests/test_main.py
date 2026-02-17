"""Unit tests for CODIGO agent CLI entry point.

Tests for apps.agents.codigo.main module, ensuring proper CLI argument parsing,
agent execution, error handling, and output generation.

Coverage target: >80% per CLAUDE.md standards.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open, call

import pytest

# Add project root to path (same as main.py does)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.agents.codigo.main import setup_logging, main


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

    def test_setup_logging_date_format(self):
        """Test that date format is ISO-like."""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging()

            call_kwargs = mock_basic_config.call_args[1]
            date_format = call_kwargs['datefmt']

            assert date_format == "%Y-%m-%d %H:%M:%S"


class TestMainCLI:
    """Test suite for main() CLI function."""

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['main.py', '--dry-run'])
    def test_dry_run_mode_no_file_created(self, mock_file_open, mock_setup_logging, mock_codigo_agent_class):
        """Test that dry-run mode doesn't create output files."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Test content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 25,
            'items_processed': 20
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 8}

        mock_codigo_agent_class.return_value = mock_agent

        # Capture stdout
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            main()

            output = mock_stdout.getvalue()

            # Should print preview with equals signs
            assert "=" in output
            assert "Test content" in output

        # Verify no file write attempted (dry-run returns early)
        mock_file_open.assert_not_called()

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('sys.argv', ['main.py', '--week', '10'])
    def test_normal_mode_creates_output_file(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that normal mode creates output file with correct content."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        md_content = "# CODIGO Report\n\nTest content"
        mock_result.to_markdown.return_value = md_content
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 30,
            'items_processed': 28
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 10}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify output directory created
        mock_makedirs.assert_called_once_with("apps/agents/codigo/output", exist_ok=True)

        # Verify file written with correct content
        mock_file_open.assert_called_once_with(
            "apps/agents/codigo/output/codigo-week-10.md",
            "w",
            encoding="utf-8"
        )
        handle = mock_file_open()
        handle.write.assert_called_once_with(md_content)

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('sys.argv', ['main.py', '--output', '/tmp/custom-dev-report.md'])
    def test_custom_output_path(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that --output flag uses custom path."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 15,
            'items_processed': 12
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 6}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # When custom output is specified, makedirs should NOT be called
        mock_makedirs.assert_not_called()

        # Should write to custom path
        mock_file_open.assert_called_once_with(
            "/tmp/custom-dev-report.md",
            "w",
            encoding="utf-8"
        )

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py', '--persist'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_persist_flag_shows_warning(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that --persist flag shows 'not implemented' warning."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 8,
            'items_processed': 7
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 3}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            main()

            output = mock_stdout.getvalue()

            # Should show persistence skipped message
            assert "persistence skipped" in output or "not implemented" in output

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py', '--verbose'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_verbose_flag_enables_debug_logging(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that --verbose flag enables DEBUG logging."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify verbose=True was passed to setup_logging
        mock_setup_logging.assert_called_once_with(True)

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    def test_default_week_is_current_week(self, mock_setup_logging, mock_codigo_agent_class):
        """Test that default week is current ISO week number."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    main()

        # Verify CodigoAgent was initialized with current week
        current_week = datetime.now().isocalendar()[1]
        mock_codigo_agent_class.assert_called_once_with(week_number=current_week)

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py', '--week', '35'])
    def test_custom_week_number(self, mock_setup_logging, mock_codigo_agent_class):
        """Test that --week flag sets custom week number."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    main()

        # Verify CodigoAgent was initialized with week 35
        mock_codigo_agent_class.assert_called_once_with(week_number=35)

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_displays_metadata_in_output(
        self, mock_makedirs, mock_file_open, mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that metadata is displayed in final output."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "B"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 45,
            'items_processed': 42
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 12}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            main()

            output = mock_stdout.getvalue()

            # Verify metadata is displayed
            assert "45" in output  # items_collected
            assert "42" in output  # items_processed
            assert "12" in output  # unique_sources
            assert "B" in output  # confidence grade

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    def test_agent_execution_error_propagates(self, mock_setup_logging, mock_codigo_agent_class):
        """Test that agent execution errors propagate to caller."""
        # Setup mock agent that raises error
        mock_agent = Mock()
        mock_agent.run.side_effect = RuntimeError("GitHub API rate limit exceeded")

        mock_codigo_agent_class.return_value = mock_agent

        # Should propagate the error
        with pytest.raises(RuntimeError) as exc_info:
            main()

        assert "GitHub API rate limit exceeded" in str(exc_info.value)

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('sys.argv', ['main.py'])
    @patch('os.makedirs')
    @patch('builtins.open')
    def test_file_write_error_propagates(
        self, mock_file_open, mock_makedirs, mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that file write errors propagate to caller."""
        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 5,
            'items_processed': 5
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 2}

        mock_codigo_agent_class.return_value = mock_agent

        # Simulate file write error
        mock_file_open.side_effect = IOError("Disk full")

        with pytest.raises(IOError) as exc_info:
            main()

        assert "Disk full" in str(exc_info.value)

    @patch('apps.agents.codigo.main.CodigoAgent')
    @patch('apps.agents.codigo.main.setup_logging')
    @patch('logging.getLogger')
    @patch('sys.argv', ['main.py'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_logging_messages(
        self, mock_makedirs, mock_file_open, mock_get_logger,
        mock_setup_logging, mock_codigo_agent_class
    ):
        """Test that proper logging messages are generated."""
        # Setup mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Setup mock agent
        mock_agent = Mock()
        mock_result = Mock()
        mock_result.to_markdown.return_value = "Content"
        mock_result.confidence.to_dict.return_value = {"dq": 0.8, "ac": 0.7}
        mock_result.confidence.grade = "A"
        mock_result.confidence.dq_display = "4"
        mock_result.confidence.ac_display = "3.5"

        mock_agent.run.return_value = mock_result
        mock_agent.get_run_metadata.return_value = {
            'items_collected': 18,
            'items_processed': 16
        }
        mock_agent.provenance.summary.return_value = {'unique_sources': 7}

        mock_codigo_agent_class.return_value = mock_agent

        with patch('sys.stdout', new=StringIO()):
            main()

        # Verify logging calls were made
        assert mock_logger.info.call_count >= 3  # At least: start, metadata, provenance

        # Check that starting message was logged
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Starting CODIGO" in str(call) for call in info_calls)
