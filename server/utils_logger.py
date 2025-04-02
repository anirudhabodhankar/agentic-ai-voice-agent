import logging
import threading
#from azure.core.tracing.ext.opentelemetry_span import OpenTelemetrySpan
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

app_logger_name = "vpa_application_logger"
configure_azure_monitor(
    # Set logger_name to the name of the logger you want to capture logging telemetry with
    # This is imperative so you do not collect logging telemetry from the SDK itself.
    logger_name=app_logger_name,
)


# Dictionary to track configured loggers and a lock for thread safety
_logger_handlers = {}
_logger_lock = threading.Lock()

def get_logger_tracer(name: str = app_logger_name) -> tuple[logging.Logger, trace.Tracer]:
    """  
    Returns a singleton logger with the specified name in a thread-safe way.
    
    Args:  
        name (str): The name of the logger. Defaults to "vpaserver".
    Returns:  
        logging.Logger: Configured logger instance.  
    """
    # Get the logger by name (logging module maintains a registry of loggers)
    tracer = trace.get_tracer(app_logger_name)
    logger = logging.getLogger(app_logger_name)
    # Set the log level
    logger.setLevel(logging.INFO)
    # Check if the logger is already configured
    
    # Thread-safe section for configuring the logger
    with _logger_lock:
        # Check if this logger has already been configured
        if name not in _logger_handlers:
            # Configure a new handler
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s ------- %(filename)s - %(funcName)s - %(lineno)d ')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Store the handler reference to avoid duplicate handlers
            _logger_handlers[name] = handler                                              
    
    return logger, tracer

