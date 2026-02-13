import asyncio
import os
import uuid

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://agentb:AgentB#Lily2026!@localhost:5433/agent_b'

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def test():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Import model
    from app.models import Session as SessionModel
    
    async with async_session() as session:
        # Create a new session
        new_session = SessionModel(
            id=str(uuid.uuid4()),
            title='Test Session',
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        print(f'Created session: {new_session.id} - {new_session.title}')

if __name__ == '__main__':
    asyncio.run(test())
