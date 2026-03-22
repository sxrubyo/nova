module.exports = {
  apps: [
    {
      name: 'nova-frontend',
      cwd: '/home/ubuntu/nova-os/frontend',
      script: 'npm',
      args: 'run dev',
      env: {
        PORT: 3000,
      },
      error_file: './pm2-error.log',
      out_file: './pm2-out.log',
      log_file: './pm2-combined.log',
      time: true,
    },
  ],
};
