"""统一个性化推荐（规则层，聚合错题与学习报告）"""
from app.services.evaluation import EvaluationService
from app.services.mistake import MistakeService
from app.models import PersonalizedLearningResource, StudentProfile, StudentProfileSuggestion


class RecommendationService:
    @staticmethod
    def preferred_resource_types(profile: StudentProfile | None) -> list[str]:
        dimensions = profile.dimensions if profile else {}
        preference = (
            (dimensions.get('explanation_preference') or {}).get('value')
            if dimensions else None
        )
        mistake_pattern = (
            (dimensions.get('mistake_pattern') or {}).get('value')
            if dimensions else None
        )
        ordered = []
        if mistake_pattern and '近期薄弱点' in mistake_pattern:
            ordered.extend(['exercise_set', 'coding_lab'])
        if preference and ('代码' in preference or '案例' in preference):
            ordered.extend(['coding_lab', 'lesson_document'])
        else:
            ordered.extend(['lesson_document', 'mind_map'])
        ordered.extend(['exercise_set', 'mind_map', 'extended_reading'])
        return list(dict.fromkeys(ordered))

    @staticmethod
    def sort_personalized_resources(resources, profile: StudentProfile | None):
        priorities = {
            resource_type: index
            for index, resource_type in enumerate(
                RecommendationService.preferred_resource_types(profile)
            )
        }
        return sorted(
            resources,
            key=lambda item: (
                priorities.get(item.resource_type, len(priorities)),
                -(item.id or 0),
            ),
        )

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
        resources = RecommendationService.sort_personalized_resources(
            resource_query.order_by(
                PersonalizedLearningResource.created_at.desc()
            ).limit(50).all(),
            profile,
        )[:10]
        dimensions = profile.dimensions if profile else {}
        pace = (dimensions.get('learning_pace') or {}).get('value') if dimensions else None
        mistake_pattern = (dimensions.get('mistake_pattern') or {}).get('value') if dimensions else None
        preferred_types = RecommendationService.preferred_resource_types(profile)
        pending_suggestion = StudentProfileSuggestion.query.filter_by(
            user_id=user_id,
            status='pending',
        ).order_by(StudentProfileSuggestion.created_at.desc()).first()
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
                'preferred_resource_types': preferred_types,
                'daily_minutes': pace,
                'mistake_pattern': mistake_pattern,
            },
            'profile_update_suggestion': pending_suggestion.to_dict() if pending_suggestion else None,
        }
