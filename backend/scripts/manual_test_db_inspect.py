import asyncio
import os

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://agentb:AgentB#Lily2026!@localhost:5433/agent_b'

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def test():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check tables
        result = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [r[0] for r in result.fetchall()]
        print('Tables:', tables)
        
        if 'sessions' in tables:
            result = await session.execute(text('SELECT COUNT(*) FROM sessions'))
            count = result.scalar()
            print('Session count:', count)
        else:
            print('sessions table NOT FOUND!')

if __name__ == '__main__':
    asyncio.run(test())
