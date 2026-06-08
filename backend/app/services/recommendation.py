"""统一个性化推荐（规则层，聚合错题与学习报告）"""
from app.services.evaluation import EvaluationService
from app.services.mistake import MistakeService
from app.models import PersonalizedLearningResource, StudentProfile


class RecommendationService:
    @staticmethod
    def get_student_recommendations(user_id: int, period: str = '7d') -> dict:
        report = EvaluationService.get_student_learning_report(user_id, period)
        weak = MistakeService.list_weak_knowledge(user_id, limit=5)
        recommendations = report.get('recommendations') or []
        profile = StudentProfile.query.filter_by(user_id=user_id).first()
        weak_keys = [item['knowledge_key'] for item in weak]
        resource_query = PersonalizedLearningResource.query.filter_by(
            user_id=user_id,
            review_status='approved',
        )
        if weak_keys:
            resource_query = resource_query.filter(
                PersonalizedLearningResource.knowledge_key.in_(weak_keys)
            )
        resources = resource_query.order_by(
            PersonalizedLearningResource.created_at.desc()
        ).limit(10).all()
        dimensions = profile.dimensions if profile else {}
        pace = (dimensions.get('learning_pace') or {}).get('value') if dimensions else None
        preference = (dimensions.get('explanation_preference') or {}).get('value') if dimensions else None
        return {
            'period': period,
            'summary': report.get('summary'),
            'weak_knowledge': weak,
            'recommendations': recommendations,
            'mistake_highlights': (report.get('mistake_highlights') or [])[:5],
            'risk_tags': report.get('risk_tags') or [],
            'personalized_resources': [item.to_dict() for item in resources],
            'profile_version': profile.version if profile else 0,
            'recommendation_context': {
                'weak_knowledge': weak_keys,
                'preferred_resource_types': (
                    ['coding_lab', 'lesson_document']
                    if preference and ('代码' in preference or '案例' in preference)
                    else ['lesson_document', 'mind_map']
                ),
                'daily_minutes': pace,
            },
            'profile_update_suggestion': (
                {
                    'dimension': 'mistake_pattern',
                    'value': '近期薄弱点：' + '、'.join(item['knowledge_label'] for item in weak[:3]),
                    'source': 'behavior',
                    'requires_confirmation': True,
                }
                if weak else None
            ),
        }
