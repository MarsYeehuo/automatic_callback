#!/usr/bin/env python
"""
快速启动脚本：创建数据库表，添加示例数据，启动 API 服务。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

logger = logging.getLogger(__name__)


async def init_db():
    """初始化数据库并填充示例数据"""
    from app.core.database import async_session_factory, engine
    from app.models.patient import Base, Patient, MedicalRecord, TreatmentEvent

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建成功")

    # 填充示例数据
    async with async_session_factory() as session:
        # 检查是否已有数据
        result = await session.execute(text("SELECT COUNT(*) FROM patients"))
        count = result.scalar()
        if count and count > 0:
            logger.info(f"已有 {count} 条患者数据，跳过示例数据填充")
            return

        # 示例患者 1：胃切除术后
        p1 = Patient(
            name="张明",
            phone="13800138001",
            gender="男",
            age=55,
            primary_diagnosis="胃癌早期",
            allergies="青霉素过敏",
            address="北京市海淀区中关村大街1号",
        )
        session.add(p1)
        await session.flush()

        session.add(
            MedicalRecord(
                patient_id=p1.id,
                diagnosis="早期胃癌（T1N0M0）",
                doctor="李伟",
                department="普外科",
                record_date=datetime.now(timezone.utc) - timedelta(days=10),
                details="患者因上腹部不适就诊，胃镜发现胃窦部肿瘤，病理确诊为腺癌，行根治性胃大部切除术。",
            )
        )

        session.add(
            TreatmentEvent(
                patient_id=p1.id,
                event_type="surgery",
                event_name="腹腔镜胃癌根治术（胃大部切除）",
                doctor="李伟",
                event_date=datetime.now(timezone.utc) - timedelta(days=7),
                follow_up_days=7,
                notes="手术顺利，术中出血约200ml，术后安返病房。",
            )
        )

        # 示例患者 2：冠心病出院
        p2 = Patient(
            name="李芳",
            phone="13800138002",
            gender="女",
            age=68,
            primary_diagnosis="冠心病",
            allergies="无",
            address="上海市浦东新区张江路200号",
        )
        session.add(p2)
        await session.flush()

        session.add(
            MedicalRecord(
                patient_id=p2.id,
                diagnosis="冠状动脉粥样硬化性心脏病（不稳定性心绞痛）",
                doctor="王强",
                department="心内科",
                record_date=datetime.now(timezone.utc) - timedelta(days=15),
                details="患者因反复胸闷胸痛就诊，冠脉造影示左前降支中段狭窄80%，行支架植入术。",
            )
        )

        session.add(
            TreatmentEvent(
                patient_id=p2.id,
                event_type="surgery",
                event_name="冠状动脉支架植入术（PCI）",
                doctor="王强",
                event_date=datetime.now(timezone.utc) - timedelta(days=14),
                follow_up_days=30,
                notes="于LAD中段植入支架1枚，术后血流恢复良好。",
            )
        )

        # 示例患者 3：糖尿病患者
        p3 = Patient(
            name="王建国",
            phone="13800138003",
            gender="男",
            age=62,
            primary_diagnosis="2型糖尿病",
            allergies="磺胺类药物过敏",
            address="广州市天河区体育西路100号",
        )
        session.add(p3)
        await session.flush()

        session.add(
            MedicalRecord(
                patient_id=p3.id,
                diagnosis="2型糖尿病伴血糖控制不佳",
                doctor="赵丽",
                department="内分泌科",
                record_date=datetime.now(timezone.utc) - timedelta(days=5),
                details="患者糖尿病史8年，近期空腹血糖10-12mmol/L，调整降糖方案后出院。",
            )
        )

        session.add(
            TreatmentEvent(
                patient_id=p3.id,
                event_type="medication",
                event_name="降糖方案调整（二甲双胍+达格列净）",
                doctor="赵丽",
                event_date=datetime.now(timezone.utc) - timedelta(days=5),
                follow_up_days=14,
                notes="调整用药方案，嘱定期监测血糖。",
            )
        )

        await session.commit()
        logger.info("示例数据填充完成")


async def run_migration():
    """简易数据库迁移（创建表）"""
    from app.models.patient import Base
    from app.core.database import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库迁移完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 初始化数据库
    asyncio.run(init_db())

    # 启动 API
    from app.main import main
    main()
