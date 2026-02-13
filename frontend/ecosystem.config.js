module.exports = {
  apps: [
    {
      name: "agentb-fe",
      script: "node_modules/next/dist/bin/next",
      args: "dev -p 3011",
      cwd: __dirname,
      env: {
        NODE_ENV: "development"
      }
    }
  ]
};
