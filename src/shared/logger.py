import logging
import os
import sys

def setup_logger(name="oracle-nba"):
    """Configura un logger estandarizado."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Formato
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

logger = setup_logger()
