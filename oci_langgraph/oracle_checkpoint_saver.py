"""
oracle_checkpoint_saver.py

Author: L. Saetta

This module provides the OracleCheckpointSaver class, which implements
LangGraph's BaseCheckpointSaver interface to persist workflow state
in an Oracle Database using the oracledb driver.

It is an implementation of:
    https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint

License: Mit

Updates:
- (19/04/2025) added connection pooling to improve performance.
- (19/04/2025) added creation of the table if it doesn't exist.
"""

import os
import json
import uuid
from typing import Any, Dict, Iterator, Optional, AsyncIterator, Sequence, Tuple
from decimal import Decimal
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.base import (
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    RunnableConfig,
    ChannelVersions,
)
import oracledb
from .utils import get_console_logger

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

logger = get_console_logger()

# the name of the Oracle DB table
TABLE_NAME = "OCI_LANGGRAPH_CHECKPOINTS"


class OracleCheckpointSaver(BaseCheckpointSaver):
    """
    A checkpoint saver that persists LangGraph workflow state to an
    Oracle Database.

    This class manages the insertion, updating, retrieval, and listing
    of checkpoints identified by thread_id and checkpoint_id.

    Attributes:
        connection (oracledb.Connection): Active connection to the Oracle Database.
        cursor (oracledb.Cursor): Cursor object for executing SQL statements.
    """

    def __init__(
        self, connect_args, min_connections=1, max_connections=5, table_name=TABLE_NAME
    ):
        """
        Initializes the OracleCheckpointSaver with a connection pool

        Args:
            connect_args: Dictionary containing connection parameters
                for the Oracle Database (e.g., user, password, dsn,
                wallet_dir).
            min_connections: Minimum number of connections in the pool
            max_connections: Maximum number of connections in the pool
            table_name: Name of the table to store checkpoints
        """
        super().__init__()
        self.pool = None
        try:
            self.pool = oracledb.create_pool(
                min=min_connections, max=max_connections, **connect_args
            )
            # ensure the tables exist
            self._ensure_tables_exist()
        except oracledb.DatabaseError as e:
            logger.error("Error initializing connection pool: %s", e)
            raise RuntimeError(f"Failed to initialize Oracle connection pool: {e}") from e

        # the name of the table for the checkpoints
        self.table_name = table_name.upper()

    def __del__(self):
        """Clean up resources when the object is destroyed"""
        if self.pool:
            try:
                self.pool.close()
            except Exception as e:
                logger.error("Error closing connection pool: %s", e)

    def _ensure_tables_exist(self):
        """Ensures the required tables exist in the database"""
        with self.pool.acquire() as conn:
            with conn.cursor() as cursor:
                # Check if checkpoints table exists
                cursor.execute(
                    "SELECT COUNT(*) FROM user_tables WHERE table_name = :name",
                    {"name": self.table_name},
                )
                if cursor.fetchone()[0] == 0:
                    # Create the checkpoints table if it doesn't exist
                    cursor.execute(
                        f"""
                        CREATE TABLE {self.table_name} (
                            thread_id VARCHAR2(64) NOT NULL,
                            checkpoint_id VARCHAR2(64) NOT NULL,
                            state JSON,
                            metadata JSON,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (thread_id, checkpoint_id)
                        )
                    """
                    )

                conn.commit()

    def _sanitize_decimals(self, obj):
        """
        Recursively converts Decimal values in dicts/lists to int or float.

        We need it because the sql query fro number in Oracle returns decimals
        """
        if isinstance(obj, dict):
            return {k: self._sanitize_decimals(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize_decimals(v) for v in obj]
        if isinstance(obj, Decimal):
            return int(obj) if obj == int(obj) else float(obj)

        return obj

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """
        Inserts a new checkpoint or updates an existing one in the database.
        Uses created_at to track the order of checkpoints.
        """
        if DEBUG:
            logger.info("OracleCheckpointSaver: called put...")

        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        if not checkpoint_id:
            if DEBUG:
                logger.warning(
                    "Missing checkpoint_id in put(); generating fallback UUID."
                )
            checkpoint_id = str(uuid.uuid4())
            config.setdefault("configurable", {})["checkpoint_id"] = checkpoint_id

        state_json = json.dumps(checkpoint)
        metadata_json = json.dumps(metadata)

        update_sql = f"""
            UPDATE {self.table_name}
            SET state = :state, metadata = :metadata
            WHERE thread_id = :thread_id AND checkpoint_id = :checkpoint_id
        """

        with self.pool.acquire() as conn:
            with conn.cursor() as cursor:
                cursor.setinputsizes(
                    state=oracledb.DB_TYPE_JSON, metadata=oracledb.DB_TYPE_JSON
                )
                cursor.execute(
                    update_sql,
                    {
                        "state": state_json,
                        "metadata": metadata_json,
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint_id,
                    },
                )

                if cursor.rowcount == 0:
                    insert_sql = f"""
                        INSERT INTO {self.table_name} (thread_id, checkpoint_id, state, metadata, created_at)
                        VALUES (:thread_id, :checkpoint_id, :state, :metadata, CURRENT_TIMESTAMP)
                    """
                    cursor.execute(
                        insert_sql,
                        {
                            "thread_id": thread_id,
                            "checkpoint_id": checkpoint_id,
                            "state": state_json,
                            "metadata": metadata_json,
                        },
                    )

            conn.commit()

        if DEBUG:
            logger.info(
                "Saving checkpoint ID %s: %s",
                checkpoint_id,
                json.dumps(checkpoint, indent=2),
            )

        return config

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        Stores intermediate writes linked to a checkpoint.

        Args:
            config (RunnableConfig): Configuration specifying thread_id and checkpoint_id.
            writes (Sequence[Tuple[str, Any]]): List of writes to store.
            task_id (str): Identifier for the task creating the writes.
            task_path (str, optional): Path of the task creating the writes.
        """
        # TODO Implement logic to store intermediate writes if necessary
        if DEBUG:
            logger.info("OracleCheckpointSaver, called put_writes...")

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """
        Retrieves the most recent or specified checkpoint for a given thread.

        If `checkpoint_id` is provided, retrieves that specific checkpoint.
        Otherwise, selects the most recent checkpoint based on created_at.

        All Decimal values are converted to native int or float.
        """
        if DEBUG:
            logger.info("OracleCheckpointSaver: called get_tuple...")

        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        with self.pool.acquire() as conn:
            with conn.cursor() as cursor:
                if checkpoint_id:
                    select_sql = f"""
                        SELECT state, metadata
                        FROM {self.table_name}
                        WHERE thread_id = :thread_id AND checkpoint_id = :checkpoint_id
                    """
                    cursor.execute(
                        select_sql,
                        {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
                    )
                else:
                    # get the last checkpoint for this thread_id
                    select_sql = f"""
                        SELECT state, metadata
                        FROM {self.table_name}
                        WHERE thread_id = :thread_id
                        ORDER BY created_at DESC FETCH FIRST 1 ROWS ONLY
                    """
                    cursor.execute(select_sql, {"thread_id": thread_id})

                row = cursor.fetchone()
                if row:
                    logger.info("Checkpoint row found!")
                    state_raw, metadata_raw = row
                    state = (
                        json.loads(state_raw)
                        if isinstance(state_raw, str)
                        else state_raw
                    )
                    metadata = (
                        json.loads(metadata_raw)
                        if isinstance(metadata_raw, str)
                        else metadata_raw
                    )

                    state = self._sanitize_decimals(state)
                    metadata = self._sanitize_decimals(metadata)

                    if DEBUG:
                        logger.info(
                            "Returning checkpoint ID: %s with channel_versions: %s",
                            state.get("id"),
                            state.get("channel_versions"),
                        )

                    return CheckpointTuple(
                        checkpoint=state, metadata=metadata, config=config
                    )

        if DEBUG:
            logger.info("No checkpoint row found — will restart from scratch!")

        return None

    def list(
        self,
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """
        Lists checkpoints for a given thread_id, ordered by created_at descending.
        All Decimal values in state/metadata are converted to int/float.

        Args:
            config: Configuration that may contain thread_id.
            filter: Not used.
            before: Optional checkpoint_id to filter out newer ones.
            limit: Optional number of records to return.
        """
        thread_id = config["configurable"]["thread_id"] if config else None
        params = {"thread_id": thread_id}

        base_sql = f"""
            SELECT state, metadata
            FROM {self.table_name}
            WHERE thread_id = :thread_id
        """

        if before:
            before_id = before["configurable"].get("checkpoint_id")
            if before_id:
                base_sql += " AND checkpoint_id < :before_id"
                params["before_id"] = before_id

        # checkpoints are returned in reverse order of creation
        base_sql += " ORDER BY created_at DESC"

        if limit:
            base_sql += f" FETCH FIRST {limit} ROWS ONLY"

        with self.pool.acquire() as conn:
            with conn.cursor() as cursor:
                cursor.execute(base_sql, params)
                for row in cursor.fetchall():
                    state_raw, metadata_raw = row
                    state = (
                        json.loads(state_raw)
                        if isinstance(state_raw, str)
                        else state_raw
                    )
                    metadata = (
                        json.loads(metadata_raw)
                        if isinstance(metadata_raw, str)
                        else metadata_raw
                    )

                    yield CheckpointTuple(
                        checkpoint=self._sanitize_decimals(state),
                        metadata=self._sanitize_decimals(metadata),
                        config=config or {},
                    )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """
        Asynchronously inserts a new checkpoint or updates an existing one in the database.

        Args:
            config (RunnableConfig): Configuration specifying thread_id and checkpoint_id.
            checkpoint (Checkpoint): The checkpoint data to store.
            metadata (CheckpointMetadata): Additional metadata for the checkpoint.
            new_versions (ChannelVersions): New channel versions as of this write.

        Returns:
            RunnableConfig: Updated configuration after storing the checkpoint.
        """
        # Implement asynchronous version if needed
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        Asynchronously stores intermediate writes linked to a checkpoint.

        Args:
            config (RunnableConfig): Configuration specifying thread_id and checkpoint_id.
            writes (Sequence[Tuple[str, Any]]): List of writes to store.
            task_id (str): Identifier for the task creating the writes.
            task_path (str, optional): Path of the task creating the writes.
        """
        # Implement asynchronous version if needed
        self.put_writes(config, writes, task_id, task_path)

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """
        Asynchronously retrieves a checkpoint tuple from the database.

        Args:
            config (RunnableConfig): Configuration specifying thread_id and checkpoint_id.

        Returns:
            Optional[CheckpointTuple]: The retrieved checkpoint tuple, or None if not found.
        """
        # Implement asynchronous version if needed
        return self.get_tuple(config)

    async def alist(
        self,
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """
        Asynchronously lists checkpoints that match the given criteria.

        Args:
            config (Optional[RunnableConfig], optional): Base configuration
            for filtering checkpoints.
            filter (Optional[Dict[str, Any]], optional): Additional filtering criteria.
            before (Optional[RunnableConfig], optional): List checkpoints
            created before this configuration.
            limit (Optional[int], optional): Maximum number of checkpoints to return.

        Yields:
            AsyncIterator[CheckpointTuple]: Asynchronous iterator of matching checkpoint tuples.
        """
        # Implement asynchronous version if needed
        for checkpoint in self.list(config, filter=filter, before=before, limit=limit):
            yield checkpoint
