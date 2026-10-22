"""Account-scoped arrival state and appearance; separate from assessed mastery."""
from . import db


class StudentOnboarding(db.Model):
    __tablename__ = 'student_onboarding'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    status = db.Column(db.String(16), nullable=False, default='exempt')
    survey_version = db.Column(db.Integer, nullable=False, default=1)
    answers = db.Column(db.JSON, nullable=False, default=dict)
    draft = db.Column(db.JSON, nullable=False, default=dict)
    step = db.Column(db.Integer, nullable=False, default=1)
    adventurer_number = db.Column(db.Integer, unique=True)
    completed_at = db.Column(db.DateTime)
    welcomed_at = db.Column(db.DateTime)


class AdventurerCounter(db.Model):
    __tablename__ = 'adventurer_counter'
    id = db.Column(db.Integer, primary_key=True)
    last_number = db.Column(db.Integer, nullable=False, default=200)


class UserAppearance(db.Model):
    __tablename__ = 'user_appearance'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    visual_style = db.Column(db.String(10), nullable=False)
    color_mode = db.Column(db.String(10), nullable=False)

    def to_dict(self):
        return {'visual_style': self.visual_style, 'color_mode': self.color_mode}
