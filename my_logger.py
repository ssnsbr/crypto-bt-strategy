import sys
import os

# Global configuration (can be changed at runtime)
_log_to_console = True
_log_to_file = False
_log_file_path = None
_log_file_handle = None


def set_logging(console=True, file=False, file_path=None):
    """Set where myprint should write to."""
    global _log_to_console, _log_to_file, _log_file_path, _log_file_handle
    _log_to_console = console
    _log_to_file = file
    if file and file_path:
        # Close previous file handle if open
        if _log_file_handle:
            _log_file_handle.close()
        _log_file_path = file_path
        # Open in append mode, create directories if needed
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        _log_file_handle = open(file_path, 'a', encoding='utf-8')
    elif not file and _log_file_handle:
        _log_file_handle.close()
        _log_file_handle = None


def myprint(*args, **kwargs):
    """Drop-in replacement for print() that respects global logging settings."""
    # Convert everything to string like print does
    parts = [str(arg) for arg in args]
    msg = ' '.join(parts)
    # Handle 'end' and 'sep' like original print? Optional: implement if needed
    end = kwargs.get('end', '\n')

    if _log_to_console:
        # Write to console
        sys.stdout.write(msg + end)
        sys.stdout.flush()

    if _log_to_file and _log_file_handle:
        # Write to file (without ANSI codes if any, but plain text is fine)
        _log_file_handle.write(msg + end)
        _log_file_handle.flush()


def close_log():
    """Call at the end of your script to close the log file."""
    global _log_file_handle
    if _log_file_handle:
        _log_file_handle.close()
        _log_file_handle = None
