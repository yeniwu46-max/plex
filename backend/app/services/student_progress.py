"""学生星轨 / 探索档案聚合（由试炼、委托、积分推导）"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.constants.star_path_unlock import (
    DOMAIN_COMPLETE_PROGRESS,
    DOMAIN_UNLOCK_PROGRESS,
    UNLOCK_ALL,
)
from app.constants.test_accounts import is_test_sandbox_user
from app.data.knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    nodes_for_domain,
)
from app.models import Trial, TrialParticipation, TrialQuestionProgress, User, UserDailyQuest, db
from app.models import PersonalizedLearningResource, StudentProfile

# 8 大类目录，直接由知识点注册表派生。每个大类的 knowledge_keys 是其下所有节点的
# 旧 key 并集——历史 trial/resource 上存的仍是旧 key，靠它归域才不会丢进度。
DOMAIN_CATALOG = [
    {
        'key': domain.key,
        'title': domain.title,
        'knowledge_keys': [key for node in nodes_for_domain(domain.key) for key in node.knowledge_keys],
    }
    for domain in KNOWLEDGE_DOMAINS
]

# 大类标题 + 节点标题 + 旧 key 别名，合成一张"key → 中文名"的查询表。
KNOWLEDGE_LABELS = {domain.key: domain.title for domain in KNOWLEDGE_DOMAINS}
for _entry in KNOWLEDGE_NODE_REGISTRY:
    KNOWLEDGE_LABELS[_entry.kg_id] = _entry.label
    for _key in _entry.knowledge_keys:
        KNOWLEDGE_LABELS.setdefault(_key, _entry.label)

DEFAULT_DOMAIN_KEY = KNOWLEDGE_DOMAINS[0].key
# 试炼没写 knowledge_key 时的兜底：落到"变量与类型"，而不是原来的 'algo'
# —— 把无标注的作答算进"算法思维"会凭空抬高最难的那一维。
DEFAULT_KNOWLEDGE_KEY = 'lang-var'


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
            key = (trial.knowledge_key or DEFAULT_KNOWLEDGE_KEY).lower()
            score = part.score or trial.difficulty or 60
            for domain in DOMAIN_CATALOG:
                if key in domain['knowledge_keys']:
                    domain_scores[domain['key']].append(score)
                    break
            else:
                domain_scores[DEFAULT_DOMAIN_KEY].append(score)
            skill_scores[key].append(score)

        level_boost = min(30, (user.level or 1) * 4)
        domains = []
        for index, domain in enumerate(DOMAIN_CATALOG):
            scores = domain_scores.get(domain['key'], [])
            progress = min(100, round(sum(scores) / len(scores)) if scores else max(15, level_boost // (index + 1)))
            locked = (
                not UNLOCK_ALL
                and index > 0
                and domains[index - 1]['progress'] < DOMAIN_UNLOCK_PROGRESS
            )
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
            'active_domain_key': next((d['key'] for d in domains if d.get('active')), DEFAULT_DOMAIN_KEY),
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
            key = (part.trial.knowledge_key or DEFAULT_KNOWLEDGE_KEY).lower()
            for domain in DOMAIN_CATALOG:
                if key in domain['knowledge_keys']:
                    domain_scores[domain['key']].append(part.score or 60)
                    break
            else:
                domain_scores[DEFAULT_DOMAIN_KEY].append(part.score or 60)

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

    # 能力雷达一维对应一个大类，随注册表自动扩缩，不再单独维护一份 key 清单。
    RADAR_DIMENSIONS = [
        (domain['title'], domain['knowledge_keys']) for domain in DOMAIN_CATALOG
    ]

    @staticmethod
    def get_ability_stats(user_id: int):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        completed = StudentProgressService._completed_trials(user_id)
        skill_scores: dict[str, list[int]] = defaultdict(list)
        for part in completed:
            key = (part.trial.knowledge_key or DEFAULT_KNOWLEDGE_KEY).lower()
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

    @staticmethod
    def _practice_heatmap_level(count: int) -> int:
        if count <= 0:
            return 0
        if count < 5:
            return 1
        if count < 15:
            return 2
        if count < 20:
            return 3
        return 4

    @staticmethod
    def get_stat_details(user_id: int) -> dict:
        """首页统计卡弹窗：等级历史、练习热力图、班级排名详情。"""
        from app.models import PointsLog
        from app.services.incentive import IncentiveService, LEVEL_TITLES
        from app.services.user import UserService
        from app.services.class_service import ClassService

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        profile = UserService.get_current_user_info(user_id)
        level_profile = IncentiveService.level_profile(user)

        logs = (
            PointsLog.query.filter_by(user_id=user_id)
            .order_by(PointsLog.created_at.asc())
            .all()
        )
        cumulative = 0
        seen_levels = {1}
        level_history = [{
            'level': 1,
            'title': LEVEL_TITLES.get(1, 'Lv1'),
            'total_points': 0,
            'reached_at': user.created_at.isoformat() if user.created_at else None,
        }]
        for row in logs:
            cumulative += row.points or 0
            new_level = IncentiveService.level_from_points(cumulative)
            if new_level not in seen_levels:
                seen_levels.add(new_level)
                level_history.append({
                    'level': new_level,
                    'title': LEVEL_TITLES.get(new_level, f'Lv{new_level}'),
                    'total_points': cumulative,
                    'reached_at': row.created_at.isoformat() if row.created_at else None,
                })
        current_level = user.level or 1
        if current_level not in seen_levels:
            level_history.append({
                'level': current_level,
                'title': LEVEL_TITLES.get(current_level, f'Lv{current_level}'),
                'total_points': user.total_points or 0,
                'reached_at': None,
            })

        today = date.today()
        month_start = today.replace(day=1)
        # 近 6 个自然月（含当月）：用单次 GROUP BY 替代逐日 COUNT，避免 N+1
        from sqlalchemy import func

        months: list[str] = []
        y, m = today.year, today.month
        for _ in range(6):
            months.append(f'{y:04d}-{m:02d}')
            m -= 1
            if m <= 0:
                m = 12
                y -= 1
        months.reverse()

        range_start = date(int(months[0][:4]), int(months[0][5:7]), 1)
        range_end = today
        day_count_rows = (
            db.session.query(
                func.date(TrialQuestionProgress.answered_at).label('day'),
                func.count().label('cnt'),
            )
            .filter(
                TrialQuestionProgress.user_id == user_id,
                TrialQuestionProgress.status == 'completed',
                TrialQuestionProgress.answered_at >= datetime.combine(range_start, datetime.min.time()),
                TrialQuestionProgress.answered_at <= datetime.combine(range_end, datetime.max.time()),
            )
            .group_by(func.date(TrialQuestionProgress.answered_at))
            .all()
        )
        count_by_day: dict[str, int] = {}
        for row in day_count_rows:
            day_key = row.day.isoformat() if hasattr(row.day, 'isoformat') else str(row.day)
            count_by_day[day_key] = int(row.cnt or 0)

        heatmap_cells = []
        cursor = range_start
        while cursor <= range_end:
            key = cursor.isoformat()
            count = count_by_day.get(key, 0)
            heatmap_cells.append({
                'date': key,
                'count': count,
                'level': StudentProgressService._practice_heatmap_level(count),
                'in_current_month': cursor >= month_start,
                'month': cursor.strftime('%Y-%m'),
            })
            cursor += timedelta(days=1)

        total_solved = TrialQuestionProgress.query.filter_by(
            user_id=user_id,
            status='completed',
        ).count()

        rank_detail = {
            'rank': profile.get('class_rank'),
            'level': profile.get('level') or 1,
            'title': profile.get('title') or level_profile.get('title'),
            'total_solved': total_solved,
            'total_points': profile.get('total_points') or 0,
            'consecutive_days': profile.get('consecutive_days') or 0,
            'class_name': (profile.get('class') or {}).get('name'),
            'classmates': [],
            'win_leaderboard': [],
        }
        cls = profile.get('class')
        if cls and cls.get('id'):
            ranking = ClassService.get_class_ranking(cls['id'])
            # 首页「班级排名」：按综合班排前 5（含姓名/等级/XP）
            rank_detail['classmates'] = (ranking.get('rankings') or [])[:5]
            # 「我的班排」详情：按对局胜局数前 5
            rank_detail['win_leaderboard'] = ClassService.get_win_leaderboard(cls['id'], limit=5)

        # 热力图单元格补充星期（0=周一 … 6=周日），前端日历渲染用
        weekday_labels = ['一', '二', '三', '四', '五', '六', '日']
        for cell in heatmap_cells:
            try:
                day = date.fromisoformat(cell['date'])
            except ValueError:
                continue
            cell['weekday'] = day.weekday()
            cell['weekday_label'] = weekday_labels[day.weekday()]
            cell['day'] = day.day

        return {
            'level_profile': level_profile,
            'level_history': level_history,
            'practice_heatmap': {
                'month': month_start.strftime('%Y-%m'),
                'months': months,
                'cells': heatmap_cells,
                'weekday_headers': weekday_labels,
                'legend': [
                    {'level': 0, 'label': '无练习', 'min': 0, 'max': 0},
                    {'level': 1, 'label': '1–4 题', 'min': 1, 'max': 4},
                    {'level': 2, 'label': '5–14 题', 'min': 5, 'max': 14},
                    {'level': 3, 'label': '15–19 题', 'min': 15, 'max': 19},
                    {'level': 4, 'label': '20 题及以上', 'min': 20, 'max': None},
                ],
            },
            'class_rank_detail': rank_detail,
        }
