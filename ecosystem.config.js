module.exports = {
  apps: [
    {
      name: 'agentb-fe',
      cwd: './frontend',
      script: 'node_modules/next/dist/bin/next',
      args: 'dev',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },
    {
      name: 'agentb-be',
      cwd: './backend',
      script: './venv/Scripts/python.exe',
      args: '-X faulthandler -m uvicorn app.main:app --port 8001 --host 0.0.0.0',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: '1',
        OMP_NUM_THREADS: '1',
        MKL_NUM_THREADS: '1',
        PYTHONFAULTHANDLER: '1'
      }
    }
  ]
};
