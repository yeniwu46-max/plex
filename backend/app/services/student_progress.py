"""学生星轨 / 探索档案聚合（由试炼、委托、积分推导）"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.constants.star_path_unlock import (
    DOMAIN_COMPLETE_PROGRESS,
    DOMAIN_UNLOCK_PROGRESS,
)
from app.constants.test_accounts import is_test_sandbox_user
from app.models import Trial, TrialParticipation, TrialQuestionProgress, User, UserDailyQuest, db
from app.models import PersonalizedLearningResource, StudentProfile

DOMAIN_CATALOG = [
    {'key': 'data-vars', 'title': '数据与变量', 'knowledge_keys': ['intro', 'comment', 'python', 'lang', 'syntax', 'basic', 'var', 'io', 'input']},
    {'key': 'operators', 'title': '运算符的使用', 'knowledge_keys': ['ops']},
    {'key': 'flow-control', 'title': '流程控制', 'knowledge_keys': ['cond', 'condition', 'loop', 'range', 'break', 'continue', 'nested']},
    {'key': 'strings', 'title': '字符串', 'knowledge_keys': ['str', 'string']},
    {'key': 'lists-dicts', 'title': '列表与字典', 'knowledge_keys': ['list', 'tuple', 'set', 'dict']},
    {'key': 'functions', 'title': '函数', 'knowledge_keys': ['func', 'function']},
    {'key': 'recursion-iter', 'title': '递归与迭代', 'knowledge_keys': ['file', 'except', 'exception', 'algo', 'algo-sum', 'algo-search', 'algo-sort', 'algo-dedup', 'algo-bubble', 'algo-selection', 'algo-binary']},
]

KNOWLEDGE_LABELS = {
    'data-vars': '数据与变量',
    'operators': '运算符的使用',
    'flow-control': '流程控制',
    'strings': '字符串',
    'lists-dicts': '列表与字典',
    'functions': '函数',
    'recursion-iter': '递归与迭代',
    'intro': 'Python 入门',
    'comment': '注释',
    'var': '变量与类型',
    'io': '输入输出',
    'input': '输入',
    'ops': '运算与表达式',
    'cond': '条件分支',
    'loop': '循环结构',
    'range': 'range 与控制',
    'list': '列表',
    'dict': '字典',
    'str': '字符串',
    'func': '函数',
    'file': '文件操作',
    'except': '异常处理',
    'algo': '算法入门',
    'algo-sum': '求和统计',
    'algo-search': '线性查找',
    'python': 'Python',
    'lang': 'Python 基础',
}


class StudentProgressService:
    @staticmethod
    def get_overview(user_id):
        """Return the data shared by the student landing pages in one request."""
        from app.services.achievement import AchievementService
        from app.services.class_service import ClassService
        from app.services.daily_quest import DailyQuestService
        from app.services.user import UserService
        from app.services.presence import PresenceService

        profile = UserService.get_current_user_info(user_id)
        ranking = (
            ClassService.get_class_ranking(profile['class']['id'])
            if profile.get('class')
            else None
        )
        daily = DailyQuestService.get_today(user_id)

        extras = StudentProgressService.get_student_dashboard_extras(user_id)
        return {
            'profile': profile,
            'achievements': AchievementService.get_user_achievements(user_id),
            'pointsLog': AchievementService.get_points_log(user_id, page=1, limit=6),
            'ranking': ranking,
            'daily': daily,
            'running_trials': extras['running_trials'],
            'class_online_count': PresenceService.class_presence(user_id)['online_count'],
        }

    @staticmethod
    def _completed_trials(user_id):
        return (
            TrialParticipation.query.join(Trial)
            .filter(
                TrialParticipation.user_id == user_id,
                TrialParticipation.status == 'completed',
            )
            .all()
        )

    @staticmethod
    def get_learning_path(user_id):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        completed = StudentProgressService._completed_trials(user_id)
        domain_scores = defaultdict(list)
        skill_scores = defaultdict(list)

        for part in completed:
            trial = part.trial
            key = (trial.knowledge_key or 'algo').lower()
            score = part.score or trial.difficulty or 60
            for domain in DOMAIN_CATALOG:
                if key in domain['knowledge_keys']:
                    domain_scores[domain['key']].append(score)
                    break
            else:
                domain_scores['data-vars'].append(score)
            skill_scores[key].append(score)

        level_boost = min(30, (user.level or 1) * 4)
        domains = []
        for index, domain in enumerate(DOMAIN_CATALOG):
            scores = domain_scores.get(domain['key'], [])
            progress = min(100, round(sum(scores) / len(scores)) if scores else max(15, level_boost // (index + 1)))
            locked = index > 0 and domains[index - 1]['progress'] < DOMAIN_UNLOCK_PROGRESS
            state = '进行中' if progress < DOMAIN_COMPLETE_PROGRESS else '已点亮'
            domains.append(
                {
                    'key': domain['key'],
                    'title': domain['title'],
                    'progress': progress,
                    'state': state,
                    'locked': locked,
                    'active': progress < DOMAIN_COMPLETE_PROGRESS and not locked,
                }
            )

        if is_test_sandbox_user(user):
            for item in domains:
                item['progress'] = 100
                item['locked'] = False
                item['state'] = '已点亮'
                item['active'] = False
            if domains:
                domains[0]['active'] = True

        if domains and not any(d['active'] for d in domains):
            for item in domains:
                if not item['locked']:
                    item['active'] = True
                    break

        resources = PersonalizedLearningResource.query.filter_by(
            user_id=user_id,
            review_status='approved',
        ).order_by(PersonalizedLearningResource.created_at.desc()).all()
        resources_by_domain = defaultdict(list)
        for resource in resources:
            for domain in DOMAIN_CATALOG:
                if resource.knowledge_key in domain['knowledge_keys']:
                    resources_by_domain[domain['key']].append(resource)
                    break
        profile = StudentProfile.query.filter_by(user_id=user_id).first()
        from app.services.recommendation import RecommendationService

        for domain in domains:
            matched = RecommendationService.sort_personalized_resources(
                resources_by_domain.get(domain['key'], []),
                profile,
            )[:3]
            domain['recommended_resource_ids'] = [item.id for item in matched]
            mistake_pattern = (
                ((profile.dimensions or {}).get('mistake_pattern') or {}).get('value')
                if profile else None
            )
            domain['recommendation_reason'] = (
                f"结合画像版本 {profile.version if profile else 0} 与当前学习进度，"
                f"优先学习 {matched[0].knowledge_label}"
                f"{'，并针对' + mistake_pattern if mistake_pattern and '近期薄弱点' in mistake_pattern else ''}。"
                if matched else '完成当前节点练习后，系统会生成对应的个性化资源。'
            )

        from app.services.learning_path import LearningPathService
        from app.services.mistake import MistakeService

        path_plan = LearningPathService.plan(user_id)

        return {
            'domains': domains,
            'active_domain_key': next((d['key'] for d in domains if d.get('active')), 'data-vars'),
            'profile_version': profile.version if profile else 0,
            'ordered_nodes': path_plan.get('ordered_nodes', []),
            'active_node_id': path_plan.get('active_node_id'),
            'next_best_action': path_plan.get('next_best_action'),
            'remediation_paths': path_plan.get('remediation_paths', []),
            'graph_backend': path_plan.get('graph_backend'),
            'question_ac_status': StudentProgressService._question_ac_status(user_id, user),
        }

    @staticmethod
    def _question_ac_status(user_id: int, user: User | None) -> list[str]:
        from app.constants.test_accounts import SLOTS_PER_KNOWLEDGE_POINT, STAR_PATH_KNOWLEDGE_POINT_IDS
        from app.services.mistake import MistakeService

        if is_test_sandbox_user(user):
            return [
                f'gen-{kp_id}-s{slot}'
                for kp_id in STAR_PATH_KNOWLEDGE_POINT_IDS
                for slot in range(SLOTS_PER_KNOWLEDGE_POINT)
            ]
        return MistakeService.list_accepted_question_refs(user_id)

    @staticmethod
    def get_archive_insights(user_id):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        completed = StudentProgressService._completed_trials(user_id)
        domain_scores = defaultdict(list)
        for part in completed:
            key = (part.trial.knowledge_key or 'algo').lower()
            for domain in DOMAIN_CATALOG:
                if key in domain['knowledge_keys']:
                    domain_scores[domain['key']].append(part.score or 60)
                    break
            else:
                domain_scores['data-vars'].append(part.score or 60)

        skills = []
        for domain in DOMAIN_CATALOG:
            scores = domain_scores.get(domain['key'], [])
            percent = min(100, round(sum(scores) / len(scores))) if scores else 0
            skills.append(
                {
                    'key': domain['key'],
                    'label': domain['title'],
                    'percent': percent,
                }
            )

        if not any(item['percent'] > 0 for item in skills):
            level_boost = min(30, (user.level or 1) * 4)
            for index, item in enumerate(skills):
                item['percent'] = max(0, min(100, level_boost // (index + 2)))

        today_quests = (
            UserDailyQuest.query.filter_by(user_id=user_id)
            .order_by(UserDailyQuest.id.desc())
            .limit(20)
            .all()
        )
        completed_q = sum(1 for q in today_quests if q.completed_at)
        trial_count = len(completed)

        if trial_count >= 3:
            label = '试炼驱动型'
            desc = '你通过多次试炼闯关积累实战经验，适合以挑战带复习。'
        elif completed_q >= 2:
            label = '节奏稳定型'
            desc = '你能持续完成每日委托，学习节奏均衡，建议保持晨间启动习惯。'
        else:
            label = '探索起步型'
            desc = '你正在建立个人探索节奏，可从今日委托与班级试炼开始积累星轨进度。'

        from app.services.emergency_mission import EmergencyMissionService

        return {
            'tendency': {'label': label, 'description': desc},
            'skills': skills[:7],
            'stats': {
                'completed_trials': trial_count,
                'completed_daily_quests': completed_q,
                'total_points': user.total_points or 0,
            },
            'emergency_missions': EmergencyMissionService.list_archive_records(user_id),
        }

    @staticmethod
    def get_student_dashboard_extras(user_id):
        from app.services.presence import PresenceService

        running = 0
        user = db.session.get(User, user_id)
        if user and user.class_id:
            running = Trial.query.filter_by(class_id=user.class_id, status='running').count()
        return {
            'running_trials': running,
            'class_online_count': PresenceService.class_presence(user_id)['online_count'],
        }

    RADAR_DIMENSIONS = [
        ('语法基础', ['intro', 'comment', 'var', 'io', 'python', 'lang', 'syntax', 'basic']),
        ('控制结构', ['ops', 'cond', 'condition', 'loop', 'range']),
        ('数据组织', ['list', 'tuple', 'dict', 'str', 'string', 'func', 'function']),
        ('调试能力', ['except', 'exception', 'file']),
        ('算法思维', ['algo', 'algo-sum', 'algo-search', 'algo-sort', 'algo-dedup', 'nested']),
    ]

    @staticmethod
    def get_ability_stats(user_id: int):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        completed = StudentProgressService._completed_trials(user_id)
        skill_scores: dict[str, list[int]] = defaultdict(list)
        for part in completed:
            key = (part.trial.knowledge_key or 'algo').lower()
            skill_scores[key].append(part.score or 60)

        def avg_for_keys(keys: list[str]) -> int:
            scores: list[int] = []
            for key in keys:
                scores.extend(skill_scores.get(key, []))
            return min(100, round(sum(scores) / len(scores))) if scores else 0

        radar_values = [avg_for_keys(keys) for _, keys in StudentProgressService.RADAR_DIMENSIONS]
        if not any(radar_values):
            boost = min(30, (user.level or 1) * 5)
            radar_values = [min(100, boost + index * 4) for index in range(len(radar_values))]

        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        x_data: list[str] = []
        correct_rates: list[int] = []
        practice_counts: list[int] = []
        today = date.today()

        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            x_data.append(weekday_labels[day.weekday()])
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            rows = TrialQuestionProgress.query.filter(
                TrialQuestionProgress.user_id == user_id,
                TrialQuestionProgress.status == 'completed',
                TrialQuestionProgress.answered_at >= day_start,
                TrialQuestionProgress.answered_at <= day_end,
            ).all()
            practice_counts.append(len(rows))
            if rows:
                correct = len([row for row in rows if row.is_correct])
                correct_rates.append(round((correct / len(rows)) * 100))
            else:
                correct_rates.append(0)

        return {
            'radar': {
                'dimensions': [label for label, _ in StudentProgressService.RADAR_DIMENSIONS],
                'values': radar_values,
            },
            'trend': {
                'x_data': x_data,
                'correct_rate': correct_rates,
                'practice_count': practice_counts,
            },
        }
