import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver, Session

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self) -> None:
        self._driver: Optional[Driver] = None

    def connect(self, uri: str, username: str, password: str) -> None:
        if not uri:
            raise ValueError("Neo4j URI is not set in settings")
        # create driver and verify
        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        self._driver.verify_connectivity()
        logger.info("Neo4j connected", extra={"uri": uri})

    def close(self) -> None:
        if self._driver:
            try:
                self._driver.close()
            finally:
                logger.info("Neo4j driver closed")

    @contextmanager
    def session(self) -> Session:
        if not self._driver:
            raise ValueError("Neo4j driver is not connected")
        s = self._driver.session()
        try:
            yield s
        finally:
            try:
                s.close()
            except Exception:
                pass

    def run_query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run a Cypher query and return list of dicts. Never raises to caller."""
        try:
            with self.session() as s:
                result = s.run(cypher, parameters or {})
                return [record.data() for record in result]
        except Exception as exc:  # never propagate
            logger.exception("Neo4j query failed: %s", exc)
            return []

    def is_connected(self) -> bool:
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False


# module-level singleton
neo4j_client = Neo4jClient()
