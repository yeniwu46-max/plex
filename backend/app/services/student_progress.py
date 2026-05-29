"""学生星轨 / 探索档案聚合（由试炼、委托、积分推导）"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.models import Trial, TrialParticipation, TrialQuestionProgress, User, UserDailyQuest, db

DOMAIN_CATALOG = [
    {'key': 'lang', 'title': '语言基础', 'knowledge_keys': ['lang', 'python', 'syntax', 'basic']},
    {'key': 'algo', 'title': '算法基础', 'knowledge_keys': ['algo', 'greedy', 'sort', 'complexity']},
    {'key': 'dp', 'title': '动态规划', 'knowledge_keys': ['dp']},
    {'key': 'geom', 'title': '计算几何', 'knowledge_keys': ['geom', 'geometry']},
    {'key': 'graph', 'title': '图论', 'knowledge_keys': ['graph', 'tree']},
    {'key': 'ds', 'title': '数据结构', 'knowledge_keys': ['data', 'ds', 'stack', 'heap']},
]

KNOWLEDGE_LABELS = {
    'lang': '语言基础',
    'python': 'Python',
    'dp': '动态规划',
    'graph': '图论',
    'geom': '计算几何',
    'geometry': '计算几何',
    'algo': '算法综合',
    'greedy': '贪心',
    'tree': '树结构',
    'data': '数据结构',
    'ds': '数据结构',
    'stack': '栈',
    'heap': '堆',
}


class StudentProgressService:
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
        user = User.query.get(user_id)
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
                domain_scores['lang'].append(score)
            skill_scores[key].append(score)

        level_boost = min(30, (user.level or 1) * 4)
        domains = []
        prev_unlocked = True
        for index, domain in enumerate(DOMAIN_CATALOG):
            scores = domain_scores.get(domain['key'], [])
            progress = min(100, round(sum(scores) / len(scores)) if scores else level_boost // (index + 1))
            locked = not prev_unlocked and progress < 15
            if progress >= 20:
                prev_unlocked = True
            state = '待解锁' if locked else ('进行中' if progress < 85 else '已点亮')
            domains.append(
                {
                    'key': domain['key'],
                    'title': domain['title'],
                    'progress': progress,
                    'state': state,
                    'locked': locked,
                    'active': not locked and progress < 85,
                }
            )

        if domains and not any(d['active'] for d in domains):
            for item in domains:
                if not item['locked']:
                    item['active'] = True
                    break

        return {'domains': domains, 'active_domain_key': next((d['key'] for d in domains if d.get('active')), 'lang')}

    @staticmethod
    def get_archive_insights(user_id):
        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')

        completed = StudentProgressService._completed_trials(user_id)
        skill_map = defaultdict(list)
        for part in completed:
            key = (part.trial.knowledge_key or 'algo').lower()
            skill_map[key].append(part.score or 60)

        skills = []
        for key, scores in skill_map.items():
            skills.append(
                {
                    'key': key,
                    'label': KNOWLEDGE_LABELS.get(key, key.upper()),
                    'percent': min(100, round(sum(scores) / len(scores))),
                }
            )
        skills.sort(key=lambda item: item['percent'], reverse=True)

        while len(skills) < 4:
            skills.append({'key': f'pending-{len(skills)}', 'label': '待探索', 'percent': 0})

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
            'skills': skills[:6],
            'stats': {
                'completed_trials': trial_count,
                'completed_daily_quests': completed_q,
                'total_points': user.total_points or 0,
            },
            'emergency_missions': EmergencyMissionService.list_archive_records(user_id),
        }

    @staticmethod
    def get_student_dashboard_extras(user_id):
        running = 0
        user = User.query.get(user_id)
        if user and user.class_id:
            running = Trial.query.filter_by(class_id=user.class_id, status='running').count()
        return {'running_trials': running}

    RADAR_DIMENSIONS = [
        ('抽象建模', ['geom', 'geometry', 'graph', 'tree']),
        ('算法设计', ['algo', 'greedy', 'sort', 'complexity']),
        ('分解问题', ['dp']),
        ('调试能力', ['lang', 'python', 'syntax', 'basic']),
        ('逻辑推理', ['data', 'ds', 'stack', 'heap']),
    ]

    @staticmethod
    def get_ability_stats(user_id: int):
        user = User.query.get(user_id)
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
