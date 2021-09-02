from typing import Any

from sqlalchemy.orm import Session

from modmail.models import Messages


class CRUDMessages:
    """View providing CRUD operations on Messages."""

    def get_by_id(self, db: Session, id: Any) -> Messages:
        """Get `Messages` object by object ID."""
        return db.query(Messages).filter(Messages.id == id).first()

    def get_by_mirrored_id(self, db: Session, *, mirrored_id: Any) -> Messages:
        """Get `Messages` object by mirrored_id, ID of message in the server."""
        return db.query(Messages).filter(Messages.mirrored_id == mirrored_id).first()

    def create(self, db: Session, **kwargs) -> Messages:
        """Create a new `Messages` object."""
        db_obj = Messages(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
