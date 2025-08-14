"""
Company Database Manager
Manages database operations for multi-company ERP system
"""

from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CompanyDatabaseManager:
    """Manages database operations for companies"""
    
    def __init__(self):
        self.current_company_id = None
    
    def set_company(self, company_id):
        """Set the current company context"""
        self.current_company_id = company_id
        logger.info(f"Company context set to: {company_id}")
    
    def get_company_context(self):
        """Get current company context"""
        return self.current_company_id
    
    def execute_query(self, query, params=None):
        """Execute a database query in company context"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise
    
    def get_company_data(self, company_id, table_name):
        """Get data for a specific company"""
        query = f"SELECT * FROM {table_name} WHERE company_id = %s"
        return self.execute_query(query, [company_id])

# Global instance
company_db_manager = CompanyDatabaseManager()