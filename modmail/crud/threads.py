from typing import Any, List

from sqlalchemy.orm import Session

from modmail.models import Tickets


class CRUDTickets:
    """View providing CRUD operations on Tickets."""

    def get_by_id(self, db: Session, id: Any) -> Tickets:
        """Get `Tickets` object by object ID."""
        return db.query(Tickets).filter(Tickets.id == id).first()

    def get_multi_by_creator(
        self, db: Session, *, creater_id: int, server_id: int, skip: int = 0, limit: int = 100
    ) -> List[Tickets]:
        """Get all `Tickets` of a user from server with `server_id`."""
        return (
            db.query(Tickets)
            .filter(Tickets.creater_id == creater_id)
            .filter(Tickets.server_id == server_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_by_server(
        self, db: Session, *, server_id: int, skip: int = 0, limit: int = 100
    ) -> List[Tickets]:
        """Get all `Tickets` for a specific server."""
        return db.query(Tickets).filter(Tickets.server_id == server_id).offset(skip).limit(limit).all()

    def get_by_thread_id(self, db: Session, *, server_id: int, thread_id: int) -> Tickets:
        """Get `Tickets` object by thread ID."""
        return (
            db.query(Tickets)
            .filter(Tickets.server_id == server_id)
            .filter(Tickets.thread_id == thread_id)
            .first()
        )

    def create(self, db: Session, **kwargs) -> Tickets:
        """Create a new `Tickets` object."""
        db_obj = Tickets(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
