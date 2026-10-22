"""小 E 自由对话与显式学习工具。对话统一经过 TutorService。"""
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from flask import current_app

_learning_turn = ContextVar('plex_messenger_learning_turn', default=None)


@contextmanager
def learning_turn(user_id, snapshot=None):
    """One request-local evidence version, including all provider fallback calls."""
    turn = None
    if current_app.config.get('LEARNER_STATE_READ_MODE', 'shadow') == 'evidence':
        from app.services.learner_state import LearnerStateService
        from app.services.learner_decision import LearnerDecisionService
        snapshot = snapshot if snapshot is not None else LearnerStateService.snapshot(user_id)
        turn = {'user_id': user_id, 'snapshot': snapshot,
                'decision': LearnerDecisionService.from_snapshot(snapshot), 'plans': {}}
    token = _learning_turn.set(turn)
    try:
        yield turn
    finally:
        _learning_turn.reset(token)


def active_turn(user_id):
    turn = _learning_turn.get()
    return turn if turn and turn['user_id'] == user_id else None


class MessengerChatService:
    """Reviewed chat entry points; document/graph tools remain explicit actions."""
    @staticmethod
    def chat(user_id: int, message: str, history=None, *, state_snapshot=None) -> dict:
        import uuid
        from app.services.messenger_tutoring import MessengerTutoring
        payload = MessengerTutoring.prepare(user_id, {'message': message, 'request_id': str(uuid.uuid4())})
        return MessengerTutoring.answer(user_id, payload, state_snapshot=state_snapshot)

    @staticmethod
    def chat_stream(user_id: int, message: str, history=None) -> Iterator[dict]:
        from app.services.messenger_tutoring import MessengerTutoring
        yield from MessengerTutoring.stream(user_id, MessengerTutoring.prepare(user_id, {'message': message}))

    @staticmethod
    def generate_knowledge_graph(user_id: int, topic) -> dict:
        from app.services.messenger_artifacts import MessengerArtifactService
        return MessengerArtifactService.generate(user_id, topic, 'knowledge_graph')

    @staticmethod
    def generate_learning_document(user_id: int, topic) -> dict:
        from app.services.messenger_artifacts import MessengerArtifactService
        return MessengerArtifactService.generate(user_id, topic, 'learning_document')
