# -*- coding: utf-8 -*-
"""星轨 / 试炼解锁阈值（与 frontend/src/constants/starPathUnlock.ts 保持一致）"""

# 全站解锁开关。置 True 后：所有星域、知识点节点、试炼题目一律可直接进入，
# 前置掌握度不再作为准入条件。下面那些阈值仍参与"进度/点亮"的展示计算，
# 只是不再用来拦人——教学上希望学生能自由跳转到任意知识点练习。
UNLOCK_ALL = True

MASTERY_THRESHOLD = 0.4  # 原 0.8
DOMAIN_UNLOCK_PROGRESS = 40  # 原 85（星域解锁）
DOMAIN_COMPLETE_PROGRESS = 60  # 原 85（星域点亮）
NODE_UNLOCK_MIN_AC = 1  # 原：需前置节点 mastery >= 80%
