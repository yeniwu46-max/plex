"""试炼题目评论服务。"""
from app.models import TrialComment, TrialCommentLike, User, db
from app.utils.time import utc_now


class TrialCommentService:
    MAX_CONTENT_LEN = 2000

    @staticmethod
    def list_for_question(question_ref: str, viewer_id: int | None = None) -> list[dict]:
        question_ref = (question_ref or '').strip()
        if not question_ref:
            raise ValueError('缺少题目标识')

        roots = (
            TrialComment.query.filter_by(question_ref=question_ref, parent_id=None)
            .order_by(TrialComment.created_at.desc())
            .all()
        )
        return [TrialCommentService._serialize_thread(row, viewer_id) for row in roots]

    @staticmethod
    def create(user_id: int, question_ref: str, content: str, parent_id: int | None = None) -> dict:
        question_ref = (question_ref or '').strip()
        content = (content or '').strip()
        if not question_ref:
            raise ValueError('缺少题目标识')
        if not content:
            raise ValueError('评论内容不能为空')
        if len(content) > TrialCommentService.MAX_CONTENT_LEN:
            raise ValueError(f'评论内容不能超过 {TrialCommentService.MAX_CONTENT_LEN} 字')

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        if parent_id is not None:
            parent = db.session.get(TrialComment, parent_id)
            if not parent or parent.question_ref != question_ref:
                raise ValueError('回复目标不存在')

        row = TrialComment(
            user_id=user_id,
            question_ref=question_ref,
            parent_id=parent_id,
            content=content,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.session.add(row)
        db.session.commit()
        return TrialCommentService._serialize_row(row, user_id)

    @staticmethod
    def toggle_like(user_id: int, comment_id: int) -> dict:
        row = db.session.get(TrialComment, comment_id)
        if not row:
            raise ValueError('评论不存在')

        existing = TrialCommentLike.query.filter_by(comment_id=comment_id, user_id=user_id).first()
        if existing:
            db.session.delete(existing)
            liked = False
        else:
            db.session.add(TrialCommentLike(comment_id=comment_id, user_id=user_id, created_at=utc_now()))
            liked = True
        db.session.commit()
        like_count = TrialCommentLike.query.filter_by(comment_id=comment_id).count()
        return {'comment_id': comment_id, 'liked': liked, 'like_count': like_count}

    @staticmethod
    def _serialize_thread(root: TrialComment, viewer_id: int | None) -> dict:
        replies = (
            TrialComment.query.filter_by(parent_id=root.id)
            .order_by(TrialComment.created_at.asc())
            .all()
        )
        payload = TrialCommentService._serialize_row(root, viewer_id)
        payload['replies'] = [TrialCommentService._serialize_row(reply, viewer_id) for reply in replies]
        return payload

    @staticmethod
    def _serialize_row(row: TrialComment, viewer_id: int | None) -> dict:
        like_count = TrialCommentLike.query.filter_by(comment_id=row.id).count()
        liked_by_me = False
        if viewer_id is not None:
            liked_by_me = TrialCommentLike.query.filter_by(comment_id=row.id, user_id=viewer_id).first() is not None
        return row.to_dict(like_count=like_count, liked_by_me=liked_by_me)
