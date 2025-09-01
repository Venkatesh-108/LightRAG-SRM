import os
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf'}

def get_memory_info():
    """Get current memory usage information."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'percent_used': memory.percent,
            'is_sufficient': memory.available / (1024**3) >= 2.0
        }
    except ImportError:
        return {'error': 'psutil not available'}

def check_system_resources():
    """Check if system has sufficient resources for document processing."""
    try:
        import psutil
        
        # Check memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        # Check disk space
        disk = psutil.disk_usage('.')
        available_disk_gb = disk.free / (1024**3)
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            'memory_available_gb': available_gb,
            'memory_sufficient': available_gb >= 2.0,
            'disk_available_gb': available_disk_gb,
            'disk_sufficient': available_disk_gb >= 1.0,
            'cpu_percent': cpu_percent,
            'cpu_ok': cpu_percent < 90,
            'all_ok': available_gb >= 2.0 and available_disk_gb >= 1.0 and cpu_percent < 90
        }
    except ImportError:
        return {'error': 'psutil not available'}
