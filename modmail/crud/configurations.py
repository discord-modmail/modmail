from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from modmail.models import Configurations


class CRUDConfigurations:
    """View providing CRUD operations on Configurations."""

    def get_by_config_key(self, db: Session, *, target_id: int, config_key: str) -> Optional[Configurations]:
        """Get `Configurations` object by config key for `target_id`."""
        return (
            db.query(Configurations)
            .filter(Configurations.target_id == target_id)
            .filter(Configurations.config_key == config_key)
            .first()
        )

    def get_multi_by_target(
        self, db: Session, *, target_id: int, skip: int = 0, limit: int = 100
    ) -> List[Configurations]:
        """Get all `Configurations` for `target_id`."""
        return (
            db.query(Configurations)
            .filter(Configurations.target_id == target_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, **kwargs) -> Configurations:
        """Create a new `Configurations` object."""
        db_obj = Configurations(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Configurations, obj_in: Dict[str, Any]) -> Configurations:
        """Update a `Configurations` object."""
        for field in obj_in:
            setattr(db_obj, field, obj_in[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, target_id: int, config_key: str) -> Configurations:
        """Remove a `Configurations` object from the database."""
        obj = self.get_by_config_key(db, target_id=target_id, config_key=config_key)
        db.delete(obj)
        db.commit()
        return obj
