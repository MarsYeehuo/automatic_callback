from __future__ import annotations

"""
回访排期策略 — 决定什么时间对什么患者进行回访。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class CallbackType(str, Enum):
    """回访类型"""

    POST_SURGERY = "post_surgery"  # 术后回访
    POST_DISCHARGE = "post_discharge"  # 出院后回访
    CHRONIC_FOLLOWUP = "chronic_followup"  # 慢性病随访
    CHECKUP_REMINDER = "checkup_reminder"  # 复诊提醒
    ABNORMAL_TRACKING = "abnormal_tracking"  # 异常指标追踪


# ─── 排期策略配置 ──────────────────────────────────────────

class ScheduleStrategy:
    """排期策略基类"""

    def __init__(
        self,
        callback_type: CallbackType,
        priority: int,
        delay_days: list[int],
        max_retries: int = 3,
        retry_interval_hours: int = 24,
    ):
        self.callback_type = callback_type
        self.priority = priority  # 基础优先级
        self.delay_days = delay_days  # 事件后第几天回访（支持多次）
        self.max_retries = max_retries
        self.retry_interval_hours = retry_interval_hours

    def calculate_schedule_times(self, event_date: datetime) -> list[datetime]:
        """根据事件日期计算排期时间列表"""
        return [event_date + timedelta(days=d) for d in self.delay_days]


# ─── 预设策略 ──────────────────────────────────────────────

# 术后回访：术后第1天、第3天、第7天
POST_SURGERY_STRATEGY = ScheduleStrategy(
    callback_type=CallbackType.POST_SURGERY,
    priority=80,
    delay_days=[1, 3, 7],
)

# 出院后回访：出院第7天、第14天、第30天
POST_DISCHARGE_STRATEGY = ScheduleStrategy(
    callback_type=CallbackType.POST_DISCHARGE,
    priority=60,
    delay_days=[7, 14, 30],
)

# 慢性病随访：每30天随访
CHRONIC_FOLLOWUP_STRATEGY = ScheduleStrategy(
    callback_type=CallbackType.CHRONIC_FOLLOWUP,
    priority=30,
    delay_days=[30],
)

# 复诊提醒：提前3天提醒
CHECKUP_REMINDER_STRATEGY = ScheduleStrategy(
    callback_type=CallbackType.CHECKUP_REMINDER,
    priority=20,
    delay_days=[-3],  # 复诊前3天
)

# 异常追踪：立即（0天）
ABNORMAL_TRACKING_STRATEGY = ScheduleStrategy(
    callback_type=CallbackType.ABNORMAL_TRACKING,
    priority=100,
    delay_days=[0],
)


STRATEGY_MAP: dict[CallbackType, ScheduleStrategy] = {
    CallbackType.POST_SURGERY: POST_SURGERY_STRATEGY,
    CallbackType.POST_DISCHARGE: POST_DISCHARGE_STRATEGY,
    CallbackType.CHRONIC_FOLLOWUP: CHRONIC_FOLLOWUP_STRATEGY,
    CallbackType.CHECKUP_REMINDER: CHECKUP_REMINDER_STRATEGY,
    CallbackType.ABNORMAL_TRACKING: ABNORMAL_TRACKING_STRATEGY,
}


def get_strategy(callback_type: CallbackType) -> Optional[ScheduleStrategy]:
    return STRATEGY_MAP.get(callback_type)
