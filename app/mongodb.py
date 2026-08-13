import logging
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from app.config import settings
from app.logger import log_event


class MongoDBHandler:
    """
    Handles MongoDB connection management and document persistence with structured logging.
    """
    def __init__(self, uri: str = settings.MONGODB_URI, db_name: str = settings.MONGODB_DATABASE, collection_name: str = settings.MONGODB_COLLECTION):
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None

    def connect(self, logger: logging.Logger, run_id: str, simulated_error: Optional[str] = None) -> None:
        """
        Establishes connection to MongoDB instance.
        """
        log_event(
            logger=logger,
            level=logging.INFO,
            action="mongodb_connection_started",
            outcome="success",
            message="Connecting to MongoDB",
            run_id=run_id,
            crawler_status="running"
        )

        try:
            if simulated_error == "mongodb_connection_error":
                raise ConnectionFailure("Simulated MongoDB connection failure")
            elif simulated_error == "mongodb_timeout":
                raise ServerSelectionTimeoutError("Simulated MongoDB connection timeout after 3000ms")

            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            # Ping database to verify active connection
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]

            log_event(
                logger=logger,
                level=logging.INFO,
                action="mongodb_connection_succeeded",
                outcome="success",
                message="Successfully connected to MongoDB",
                run_id=run_id,
                crawler_status="running"
            )
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            is_timeout = isinstance(e, ServerSelectionTimeoutError) or simulated_error == "mongodb_timeout"
            err_category = "mongodb_timeout" if is_timeout else "mongodb_connection_error"
            is_simulated = simulated_error in ["mongodb_connection_error", "mongodb_timeout"]

            log_event(
                logger=logger,
                level=logging.ERROR,
                action="mongodb_connection_failed",
                outcome="failure",
                message=f"MongoDB connection failed: {str(e)}",
                run_id=run_id,
                crawler_status="failed",
                error_category=err_category,
                error_message=str(e),
                error_simulated=is_simulated
            )
            raise e
        except Exception as e:
            log_event(
                logger=logger,
                level=logging.ERROR,
                action="mongodb_connection_failed",
                outcome="failure",
                message=f"Unexpected MongoDB connection failure: {str(e)}",
                run_id=run_id,
                crawler_status="failed",
                error_category="mongodb_connection_error",
                error_message=str(e),
                error_simulated=False
            )
            raise e

    def insert_records(self, logger: logging.Logger, run_id: str, documents: List[Dict[str, Any]], simulated_error: Optional[str] = None) -> int:
        """
        Inserts processed crawler records into MongoDB collection.
        """
        try:
            if simulated_error == "database_write_error":
                raise OperationFailure("Simulated database write failure")

            if self.collection is None:
                raise ConnectionFailure("MongoDB client is not connected")

            result = self.collection.insert_many(documents)
            inserted_count = len(result.inserted_ids)

            log_event(
                logger=logger,
                level=logging.INFO,
                action="records_stored",
                outcome="success",
                message=f"Successfully stored {inserted_count} records in MongoDB",
                run_id=run_id,
                crawler_status="running",
                records_count=inserted_count
            )
            return inserted_count
        except Exception as e:
            is_simulated = simulated_error == "database_write_error"
            log_event(
                logger=logger,
                level=logging.ERROR,
                action="database_write_failed",
                outcome="failure",
                message=f"Failed to store records in MongoDB: {str(e)}",
                run_id=run_id,
                crawler_status="failed",
                error_category="database_write_error",
                error_message=str(e),
                error_simulated=is_simulated
            )
            raise e

    def close(self) -> None:
        """
        Closes MongoDB client connection.
        """
        if self.client:
            self.client.close()
